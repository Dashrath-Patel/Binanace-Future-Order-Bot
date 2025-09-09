#!/usr/bin/env python3
"""
TWAP Strategy - Time-Weighted Average Price for Binance Futures
Splits large orders into smaller chunks executed over time

Usage: python src/advanced/twap.py SYMBOL SIDE TOTAL_QUANTITY DURATION_MINUTES [--chunks N] [--testnet]

Example: python src/advanced/twap.py BTCUSDT BUY 1.0 60 --chunks 10
"""

import sys
import os
import argparse
import time
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import BinanceConfig, TRADING_LIMITS
from utils import (
    setup_logger, validate_symbol, validate_side, validate_quantity,
    format_quantity, log_order_attempt, log_order_success, log_order_error,
    ValidationError
)

class TWAPOrderBot:
    """TWAP (Time-Weighted Average Price) trading bot for Binance Futures"""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.client = Client(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        self.logger = setup_logger('TWAPOrderBot')
        self.is_running = False
        self.orders_placed = []
        
    def validate_inputs(self, symbol: str, side: str, total_quantity: float, 
                       duration_minutes: int, chunks: int) -> None:
        """Validate all input parameters"""
        errors = []
        
        if not validate_symbol(symbol):
            errors.append(f"Invalid symbol format: {symbol}")
            
        if not validate_side(side):
            errors.append(f"Invalid side: {side}. Must be BUY or SELL")
            
        if not validate_quantity(total_quantity, 
                               TRADING_LIMITS['min_quantity'], 
                               TRADING_LIMITS['max_quantity']):
            errors.append(f"Invalid total quantity: {total_quantity}. Must be between "
                         f"{TRADING_LIMITS['min_quantity']} and {TRADING_LIMITS['max_quantity']}")
        
        if duration_minutes <= 0:
            errors.append(f"Duration must be positive, got: {duration_minutes}")
            
        if chunks <= 0:
            errors.append(f"Number of chunks must be positive, got: {chunks}")
            
        if chunks > duration_minutes:
            errors.append(f"Too many chunks ({chunks}) for duration ({duration_minutes} minutes)")
        
        # Check if chunk size is valid
        chunk_size = total_quantity / chunks
        if chunk_size < TRADING_LIMITS['min_quantity']:
            errors.append(f"Chunk size ({chunk_size}) would be below minimum ({TRADING_LIMITS['min_quantity']})")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    def calculate_chunk_schedule(self, total_quantity: float, duration_minutes: int, 
                                chunks: int) -> List[Dict]:
        """Calculate when and how much to trade for each chunk"""
        chunk_size = total_quantity / chunks
        interval_minutes = duration_minutes / chunks
        
        schedule = []
        start_time = datetime.now()
        
        for i in range(chunks):
            execute_time = start_time + timedelta(minutes=i * interval_minutes)
            schedule.append({
                'chunk_id': i + 1,
                'quantity': chunk_size,
                'execute_time': execute_time,
                'interval_seconds': interval_minutes * 60
            })
            
        return schedule
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            raise
    
    def place_chunk_order(self, symbol: str, side: str, quantity: float, chunk_id: int) -> dict:
        """Place a single chunk order (market order for immediate execution)"""
        try:
            formatted_quantity = format_quantity(quantity, TRADING_LIMITS['quantity_precision'])
            
            self.logger.info(f"Placing chunk {chunk_id}: {side} {quantity} {symbol}")
            
            order = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type=Client.FUTURE_ORDER_TYPE_MARKET,
                quantity=formatted_quantity
            )
            
            log_order_success(self.logger, order)
            return order
            
        except Exception as e:
            log_order_error(self.logger, e, f"Chunk {chunk_id} for {symbol}")
            raise
    
    def execute_twap_strategy(self, symbol: str, side: str, total_quantity: float, 
                            duration_minutes: int, chunks: int = 10) -> Dict:
        """Execute TWAP strategy by splitting order into time-distributed chunks"""
        
        # Validate inputs
        self.validate_inputs(symbol, side, total_quantity, duration_minutes, chunks)
        
        # Calculate execution schedule
        schedule = self.calculate_chunk_schedule(total_quantity, duration_minutes, chunks)
        
        self.logger.info(f"Starting TWAP execution: {total_quantity} {symbol} over {duration_minutes} minutes in {chunks} chunks")
        
        self.is_running = True
        execution_results = {
            'strategy': 'TWAP',
            'symbol': symbol,
            'side': side,
            'total_quantity': total_quantity,
            'duration_minutes': duration_minutes,
            'chunks': chunks,
            'orders': [],
            'start_time': datetime.now(),
            'end_time': None,
            'total_executed': 0.0,
            'avg_price': 0.0,
            'errors': []
        }
        
        try:
            for chunk in schedule:
                if not self.is_running:
                    self.logger.info("TWAP execution stopped by user")
                    break
                
                # Wait until it's time for this chunk
                now = datetime.now()
                if now < chunk['execute_time']:
                    wait_seconds = (chunk['execute_time'] - now).total_seconds()
                    self.logger.info(f"Waiting {wait_seconds:.1f} seconds for chunk {chunk['chunk_id']}")
                    time.sleep(wait_seconds)
                
                if not self.is_running:
                    break
                
                try:
                    # Get current price for logging
                    current_price = self.get_current_price(symbol)
                    
                    # Place chunk order
                    order = self.place_chunk_order(
                        symbol, side, chunk['quantity'], chunk['chunk_id']
                    )
                    
                    # Record order details
                    order_info = {
                        'chunk_id': chunk['chunk_id'],
                        'order_id': order['orderId'],
                        'quantity': float(order['origQty']),
                        'executed_qty': float(order.get('executedQty', 0)),
                        'price': current_price,
                        'timestamp': datetime.now()
                    }
                    
                    execution_results['orders'].append(order_info)
                    execution_results['total_executed'] += order_info['executed_qty']
                    self.orders_placed.append(order)
                    
                    self.logger.info(f"Chunk {chunk['chunk_id']} completed: {order_info['executed_qty']} @ {current_price}")
                    
                except Exception as e:
                    error_info = {
                        'chunk_id': chunk['chunk_id'],
                        'error': str(e),
                        'timestamp': datetime.now()
                    }
                    execution_results['errors'].append(error_info)
                    self.logger.error(f"Failed to execute chunk {chunk['chunk_id']}: {e}")
                    # Continue with next chunk despite error
            
            # Calculate average price
            if execution_results['orders']:
                total_value = sum(
                    order['executed_qty'] * order['price'] 
                    for order in execution_results['orders']
                )
                execution_results['avg_price'] = total_value / execution_results['total_executed'] if execution_results['total_executed'] > 0 else 0
            
            execution_results['end_time'] = datetime.now()
            
            self.logger.info(f"TWAP execution completed: {execution_results['total_executed']}/{total_quantity} executed")
            
            return execution_results
            
        except KeyboardInterrupt:
            self.logger.info("TWAP execution interrupted by user")
            self.is_running = False
            execution_results['end_time'] = datetime.now()
            return execution_results
        
        finally:
            self.is_running = False
    
    def stop_execution(self):
        """Stop TWAP execution"""
        self.is_running = False
        self.logger.info("TWAP execution stop requested")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Execute TWAP (Time-Weighted Average Price) strategy on Binance USDT-M Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute 1 BTC buy over 60 minutes in 10 chunks
  python src/advanced/twap.py BTCUSDT BUY 1.0 60 --chunks 10
  
  # Execute 5 ETH sell over 30 minutes in 6 chunks
  python src/advanced/twap.py ETHUSDT SELL 5.0 30 --chunks 6
        """
    )
    
    parser.add_argument('symbol', help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', help='Order side (BUY or SELL)')
    parser.add_argument('total_quantity', type=float, help='Total quantity to trade')
    parser.add_argument('duration_minutes', type=int, help='Duration in minutes to spread the trades')
    parser.add_argument('--chunks', type=int, default=10, 
                       help='Number of chunks to split the order into (default: 10)')
    parser.add_argument('--testnet', action='store_true', 
                       help='Use testnet (default: from config)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = BinanceConfig.from_env()
        if args.testnet:
            config.testnet = True
            
        # Create bot instance
        bot = TWAPOrderBot(config)
        
        # Setup interrupt handler
        def signal_handler():
            print("\n⚠️  Stopping TWAP execution...")
            bot.stop_execution()
        
        # Execute TWAP strategy
        print(f"🚀 Starting TWAP execution...")
        print(f"Symbol: {args.symbol}")
        print(f"Side: {args.side}")
        print(f"Total Quantity: {args.total_quantity}")
        print(f"Duration: {args.duration_minutes} minutes")
        print(f"Chunks: {args.chunks}")
        print(f"Press Ctrl+C to stop execution\n")
        
        try:
            result = bot.execute_twap_strategy(
                args.symbol, args.side, args.total_quantity, 
                args.duration_minutes, args.chunks
            )
            
            print(f"\n✅ TWAP execution completed!")
            print(f"Total Executed: {result['total_executed']}/{result['total_quantity']}")
            print(f"Orders Placed: {len(result['orders'])}")
            print(f"Average Price: {result['avg_price']:.8f}")
            print(f"Errors: {len(result['errors'])}")
            
            if result['errors']:
                print(f"\n⚠️  Errors encountered:")
                for error in result['errors']:
                    print(f"  Chunk {error['chunk_id']}: {error['error']}")
        
        except KeyboardInterrupt:
            signal_handler()
            print("\n✅ TWAP execution stopped by user")
        
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

