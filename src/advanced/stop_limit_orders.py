#!/usr/bin/env python3
"""
Stop-Limit Orders - Advanced stop-limit order logic for Binance Futures
Triggers a limit order when a stop price is reached

Usage: python src/advanced/stop_limit_orders.py SYMBOL SIDE QUANTITY STOP_PRICE LIMIT_PRICE [--testnet]

Example: python src/advanced/stop_limit_orders.py BTCUSDT SELL 0.01 64000.0 63900.0
"""

import sys
import os
import argparse
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import BinanceConfig, TRADING_LIMITS
from utils import (
    setup_logger, validate_symbol, validate_side, validate_quantity, validate_price,
    format_quantity, format_price, log_order_attempt, log_order_success, log_order_error,
    ValidationError
)

class StopLimitOrderBot:
    """Stop-Limit order trading bot for Binance Futures"""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.client = Client(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        self.logger = setup_logger('StopLimitOrderBot')
        
    def validate_inputs(self, symbol: str, side: str, quantity: float, 
                       stop_price: float, limit_price: float) -> None:
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
        
        if not validate_price(stop_price, TRADING_LIMITS['min_price']):
            errors.append(f"Invalid stop price: {stop_price}. Must be >= {TRADING_LIMITS['min_price']}")
            
        if not validate_price(limit_price, TRADING_LIMITS['min_price']):
            errors.append(f"Invalid limit price: {limit_price}. Must be >= {TRADING_LIMITS['min_price']}")
        
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
    
    def validate_stop_limit_prices(self, symbol: str, side: str, stop_price: float, limit_price: float) -> None:
        """Validate stop-limit price relationships"""
        try:
            current_price = self.get_current_price(symbol)
            self.logger.info(f"Current market price for {symbol}: {current_price}")
            
            if side.upper() == 'SELL':
                # SELL stop-limit: typically used for stop-loss
                # Current price should be above stop price
                if current_price <= stop_price:
                    self.logger.warning(f"SELL stop-limit: Current price {current_price} is at/below stop price {stop_price}")
                # Limit price can be below stop price for better execution
                if limit_price > stop_price:
                    self.logger.warning(f"SELL stop-limit: Limit price {limit_price} is above stop price {stop_price}")
            else:  # BUY
                # BUY stop-limit: typically used for breakout trading
                # Current price should be below stop price
                if current_price >= stop_price:
                    self.logger.warning(f"BUY stop-limit: Current price {current_price} is at/above stop price {stop_price}")
                # Limit price can be above stop price for better execution
                if limit_price < stop_price:
                    self.logger.warning(f"BUY stop-limit: Limit price {limit_price} is below stop price {stop_price}")
                    
        except Exception as e:
            self.logger.warning(f"Could not validate stop-limit prices: {e}")
    
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
    
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float, 
                              stop_price: float, limit_price: float) -> dict:
        """Place a stop-limit order on Binance Futures"""
        
        # Validate inputs
        self.validate_inputs(symbol, side, quantity, stop_price, limit_price)
        
        # Validate price relationships (warnings only)
        self.validate_stop_limit_prices(symbol, side, stop_price, limit_price)
        
        # Get symbol info for precision
        symbol_info = self.get_symbol_info(symbol)
        
        # Format values with proper precision
        formatted_quantity = format_quantity(quantity, TRADING_LIMITS['quantity_precision'])
        formatted_stop_price = format_price(stop_price, TRADING_LIMITS['price_precision'])
        formatted_limit_price = format_price(limit_price, TRADING_LIMITS['price_precision'])
        
        # Log attempt
        self.logger.info(f"Placing stop-limit order: {side} {quantity} {symbol} @ stop={stop_price}, limit={limit_price}")
        
        try:
            # Place stop-limit order
            order = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type=Client.FUTURE_ORDER_TYPE_STOP,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=formatted_quantity,
                price=formatted_limit_price,
                stopPrice=formatted_stop_price
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
        description="Place stop-limit orders on Binance USDT-M Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SELL stop-limit (stop-loss): If price drops to 64000, sell at limit 63900
  python src/advanced/stop_limit_orders.py BTCUSDT SELL 0.01 64000.0 63900.0
  
  # BUY stop-limit (breakout): If price rises to 66000, buy at limit 66100
  python src/advanced/stop_limit_orders.py BTCUSDT BUY 0.01 66000.0 66100.0
        """
    )
    
    parser.add_argument('symbol', help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', help='Order side (BUY or SELL)')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('stop_price', type=float, help='Stop price (trigger price)')
    parser.add_argument('limit_price', type=float, help='Limit price (execution price)')
    parser.add_argument('--testnet', action='store_true', 
                       help='Use testnet (default: from config)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = BinanceConfig.from_env()
        if args.testnet:
            config.testnet = True
            
        # Create bot instance
        bot = StopLimitOrderBot(config)
        
        # Place stop-limit order
        result = bot.place_stop_limit_order(
            args.symbol, args.side, args.quantity, 
            args.stop_price, args.limit_price
        )
        
        print(f"✅ Stop-limit order placed successfully!")
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Quantity: {result.get('origQty')}")
        print(f"Stop Price: {args.stop_price}")
        print(f"Limit Price: {result.get('price')}")
        print(f"Status: {result.get('status')}")
        print(f"Time in Force: {result.get('timeInForce')}")
        
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
