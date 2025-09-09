#!/usr/bin/env python3
"""
Market Orders - CLI script for placing market orders on Binance USDT-M Futures
Usage: python src/market_orders.py SYMBOL SIDE QUANTITY [--testnet]

Example: python src/market_orders.py BTCUSDT BUY 0.01
"""

import sys
import argparse
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

from config import BinanceConfig, TRADING_LIMITS
from utils import (
    setup_logger, validate_symbol, validate_side, validate_quantity,
    format_quantity, log_order_attempt, log_order_success, log_order_error,
    ValidationError
)

class MarketOrderBot:
    """Market order trading bot for Binance Futures"""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.client = Client(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        self.logger = setup_logger('MarketOrderBot')
        
    def validate_inputs(self, symbol: str, side: str, quantity: float) -> None:
        """Validate all input parameters"""
        errors = []
        
        if not validate_symbol(symbol):
            errors.append(f"Invalid symbol format: {symbol}")
            
        if not validate_side(side):
            errors.append(f"Invalid side: {side}. Must be BUY or SELL")
            
        if not validate_quantity(quantity, 
                               TRADING_LIMITS['min_quantity'], 
                               TRADING_LIMITS['max_quantity']):
            errors.append(f"Invalid quantity: {quantity}. Must be between "
                         f"{TRADING_LIMITS['min_quantity']} and {TRADING_LIMITS['max_quantity']}")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
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
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        """Place a market order on Binance Futures"""
        
        # Validate inputs
        self.validate_inputs(symbol, side, quantity)
        
        # Get symbol info for precision
        symbol_info = self.get_symbol_info(symbol)
        
        # Format quantity with proper precision
        formatted_quantity = format_quantity(quantity, TRADING_LIMITS['quantity_precision'])
        
        # Log attempt
        log_order_attempt(self.logger, "MARKET", symbol, side, quantity)
        
        try:
            # Place market order
            order = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type=Client.FUTURE_ORDER_TYPE_MARKET,
                quantity=formatted_quantity
            )
            
            # Log success
            log_order_success(self.logger, order)
            return order
            
        except BinanceAPIException as e:
            log_order_error(self.logger, e, f"API Error for {symbol}")
            raise
        except BinanceOrderException as e:
            log_order_error(self.logger, e, f"Order Error for {symbol}")
            raise
        except Exception as e:
            log_order_error(self.logger, e, f"Unexpected error for {symbol}")
            raise

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Place market orders on Binance USDT-M Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/market_orders.py BTCUSDT BUY 0.01
  python src/market_orders.py ETHUSDT SELL 0.1 --testnet
        """
    )
    
    parser.add_argument('symbol', help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', help='Order side (BUY or SELL)')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('--testnet', action='store_true', 
                       help='Use testnet (default: from config)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = BinanceConfig.from_env()
        if args.testnet:
            config.testnet = True
            
        # Create bot instance
        bot = MarketOrderBot(config)
        
        # Place order
        result = bot.place_market_order(args.symbol, args.side, args.quantity)
        
        print(f"✅ Market order placed successfully!")
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Quantity: {result.get('origQty')}")
        print(f"Status: {result.get('status')}")
        
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
