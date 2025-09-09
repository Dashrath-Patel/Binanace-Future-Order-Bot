#!/usr/bin/env python3
"""
Grid Strategy - Automated grid trading strategy for Binance Futures
Places buy and sell orders in a grid pattern within a price range

Usage: python src/advanced/grid_strategy.py SYMBOL QUANTITY GRID_LOWER GRID_UPPER --levels N [--testnet]

Example: python src/advanced/grid_strategy.py BTCUSDT 0.01 64000.0 66000.0 --levels 10
"""

import sys
import os
import argparse
import time
from datetime import datetime
from decimal import Decimal
from typing import List, Dict
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import BinanceConfig, TRADING_LIMITS
from utils import (
    setup_logger, validate_symbol, validate_quantity, validate_price,
    format_quantity, format_price, log_order_attempt, log_order_success, log_order_error,
    ValidationError
)

class GridStrategyBot:
    """Grid trading strategy bot for Binance Futures"""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.client = Client(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        self.logger = setup_logger('GridStrategyBot')
        self.active_orders = []
        
    def validate_inputs(self, symbol: str, quantity: float, 
                       grid_lower: float, grid_upper: float, levels: int) -> None:
        """Validate all input parameters"""
        errors = []
        
        if not validate_symbol(symbol):
            errors.append(f"Invalid symbol format: {symbol}")
            
        if not validate_quantity(quantity, 
                               TRADING_LIMITS['min_quantity'], 
                               TRADING_LIMITS['max_quantity']):
            errors.append(f"Invalid quantity: {quantity}. Must be between "
                         f"{TRADING_LIMITS['min_quantity']} and {TRADING_LIMITS['max_quantity']}")
        
        if not validate_price(grid_lower, TRADING_LIMITS['min_price']):
            errors.append(f"Invalid lower grid price: {grid_lower}. Must be >= {TRADING_LIMITS['min_price']}")
            
        if not validate_price(grid_upper, TRADING_LIMITS['min_price']):
            errors.append(f"Invalid upper grid price: {grid_upper}. Must be >= {TRADING_LIMITS['min_price']}")
        
        if grid_lower >= grid_upper:
            errors.append(f"Lower grid price ({grid_lower}) must be less than upper grid price ({grid_upper})")
            
        if levels < 2:
            errors.append(f"Number of levels must be at least 2, got: {levels}")
            
        if levels > 50:
            errors.append(f"Number of levels too high ({levels}), maximum is 50")
        
        # Check price difference between levels
        if levels > 1:
            level_spacing = (grid_upper - grid_lower) / (levels - 1)
            min_tick_size = 0.01  # Minimum tick size (should be fetched from symbol info)
            if level_spacing < min_tick_size:
                errors.append(f"Grid levels too close together: {level_spacing} < {min_tick_size}")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    def get_current_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            raise
    
    def calculate_grid_levels(self, grid_lower: float, grid_upper: float, levels: int) -> List[float]:
        """Calculate grid price levels"""
        if levels == 1:
            return [(grid_lower + grid_upper) / 2]
        
        price_range = grid_upper - grid_lower
        level_spacing = price_range / (levels - 1)
        
        grid_levels = []
        for i in range(levels):
            price = grid_lower + (i * level_spacing)
            grid_levels.append(price)
            
        return grid_levels
    
    def get_symbol_info(self, symbol: str) -> dict:
        """Get symbol trading information"""
        try:
            exchange_info = self.client.futures_exchange_info()
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            raise ValidationError(f"Symbol {symbol} not found on exchange")
        except Exception as e:
            self.logger.error(f"Failed to get symbol info for {symbol}: {e}")
            raise
    
    def place_grid_orders(self, symbol: str, quantity: float, grid_levels: List[float], 
                         current_price: float) -> Dict:
        """Place buy and sell orders at grid levels"""
        
        orders_placed = []
        errors = []
        
        # Format quantity
        formatted_quantity = format_quantity(quantity, TRADING_LIMITS['quantity_precision'])
        
        for i, price in enumerate(grid_levels):
            try:
                formatted_price = format_price(price, TRADING_LIMITS['price_precision'])
                
                # Determine order side based on current price
                if price < current_price:
                    # Place BUY orders below current price
                    side = 'BUY'
                elif price > current_price:
                    # Place SELL orders above current price  
                    side = 'SELL'
                else:
                    # Skip if price equals current price
                    self.logger.info(f"Skipping level {i+1} at {price} (current price)")
                    continue
                
                self.logger.info(f"Placing grid order {i+1}/{len(grid_levels)}: {side} {quantity} {symbol} @ {price}")
                
                # Place limit order
                order = self.client.futures_create_order(
                    symbol=symbol.upper(),
                    side=side,
                    type=Client.FUTURE_ORDER_TYPE_LIMIT,
                    timeInForce=Client.TIME_IN_FORCE_GTC,
                    quantity=formatted_quantity,
                    price=formatted_price
                )
                
                order_info = {
                    'level': i + 1,
                    'order_id': order['orderId'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': float(order['origQty']),
                    'price': float(order['price']),
                    'status': order['status']
                }
                
                orders_placed.append(order_info)
                log_order_success(self.logger, order)
                
                # Small delay between orders to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                error_info = {
                    'level': i + 1,
                    'price': price,
                    'error': str(e)
                }
                errors.append(error_info)
                log_order_error(self.logger, e, f"Grid level {i+1} at {price}")
        
        return {
            'strategy': 'GRID',
            'symbol': symbol,
            'quantity_per_level': quantity,
            'grid_levels': grid_levels,
            'current_price': current_price,
            'orders_placed': orders_placed,
            'errors': errors,
            'timestamp': datetime.now()
        }
    
    def execute_grid_strategy(self, symbol: str, quantity: float, 
                            grid_lower: float, grid_upper: float, levels: int = 10) -> Dict:
        """Execute grid trading strategy"""
        
        # Validate inputs
        self.validate_inputs(symbol, quantity, grid_lower, grid_upper, levels)
        
        # Get current price
        current_price = self.get_current_price(symbol)
        self.logger.info(f"Current price for {symbol}: {current_price}")
        
        # Validate price is within grid range
        if not (grid_lower <= current_price <= grid_upper):
            self.logger.warning(f"Current price {current_price} is outside grid range [{grid_lower}, {grid_upper}]")
        
        # Calculate grid levels
        grid_levels = self.calculate_grid_levels(grid_lower, grid_upper, levels)
        self.logger.info(f"Grid levels: {[round(level, 2) for level in grid_levels]}")
        
        # Get symbol info
        symbol_info = self.get_symbol_info(symbol)
        
        # Place grid orders
        self.logger.info(f"Starting grid strategy: {levels} levels between {grid_lower} and {grid_upper}")
        
        result = self.place_grid_orders(symbol, quantity, grid_levels, current_price)
        
        self.active_orders = result['orders_placed']
        
        self.logger.info(f"Grid strategy executed: {len(result['orders_placed'])} orders placed, {len(result['errors'])} errors")
        
        return result
    
    def cancel_all_orders(self, symbol: str) -> Dict:
        """Cancel all active orders for the symbol"""
        cancelled_orders = []
        errors = []
        
        try:
            # Get all open orders
            open_orders = self.client.futures_get_open_orders(symbol=symbol.upper())
            
            for order in open_orders:
                try:
                    result = self.client.futures_cancel_order(
                        symbol=symbol.upper(),
                        orderId=order['orderId']
                    )
                    cancelled_orders.append(result)
                    self.logger.info(f"Cancelled order {order['orderId']}")
                    
                except Exception as e:
                    errors.append({
                        'order_id': order['orderId'],
                        'error': str(e)
                    })
                    self.logger.error(f"Failed to cancel order {order['orderId']}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to get open orders: {e}")
            errors.append({'error': str(e)})
        
        return {
            'cancelled_orders': cancelled_orders,
            'errors': errors
        }

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Execute grid trading strategy on Binance USDT-M Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create 10-level grid between 64000 and 66000
  python src/advanced/grid_strategy.py BTCUSDT 0.01 64000.0 66000.0 --levels 10
  
  # Create 5-level grid for ETH
  python src/advanced/grid_strategy.py ETHUSDT 0.1 3800.0 4200.0 --levels 5
  
  # Cancel all orders for a symbol
  python src/advanced/grid_strategy.py BTCUSDT 0 0 0 --cancel-all
        """
    )
    
    parser.add_argument('symbol', help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('quantity', type=float, help='Quantity per grid level')
    parser.add_argument('grid_lower', type=float, help='Lower bound of grid')
    parser.add_argument('grid_upper', type=float, help='Upper bound of grid')
    parser.add_argument('--levels', type=int, default=10, 
                       help='Number of grid levels (default: 10)')
    parser.add_argument('--cancel-all', action='store_true',
                       help='Cancel all open orders for the symbol')
    parser.add_argument('--testnet', action='store_true', 
                       help='Use testnet (default: from config)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = BinanceConfig.from_env()
        if args.testnet:
            config.testnet = True
            
        # Create bot instance
        bot = GridStrategyBot(config)
        
        if args.cancel_all:
            # Cancel all orders
            result = bot.cancel_all_orders(args.symbol)
            print(f"✅ Cancelled {len(result['cancelled_orders'])} orders")
            if result['errors']:
                print(f"⚠️  {len(result['errors'])} errors occurred")
        else:
            # Execute grid strategy
            result = bot.execute_grid_strategy(
                args.symbol, args.quantity, 
                args.grid_lower, args.grid_upper, args.levels
            )
            
            print(f"✅ Grid strategy executed!")
            print(f"Symbol: {result['symbol']}")
            print(f"Grid Range: {result['grid_levels'][0]:.2f} - {result['grid_levels'][-1]:.2f}")
            print(f"Current Price: {result['current_price']:.2f}")
            print(f"Orders Placed: {len(result['orders_placed'])}")
            print(f"Errors: {len(result['errors'])}")
            
            if result['orders_placed']:
                print(f"\n📊 Orders Summary:")
                buy_orders = [o for o in result['orders_placed'] if o['side'] == 'BUY']
                sell_orders = [o for o in result['orders_placed'] if o['side'] == 'SELL']
                print(f"  BUY orders: {len(buy_orders)}")
                print(f"  SELL orders: {len(sell_orders)}")
            
            if result['errors']:
                print(f"\n⚠️  Errors:")
                for error in result['errors']:
                    print(f"  Level {error['level']}: {error['error']}")
        
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
