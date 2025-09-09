#!/usr/bin/env python3
"""
Limit Orders - CLI script for placing limit orders on Binance USDT-M Futures
Usage: python src/limit_orders.py SYMBOL SIDE QUANTITY PRICE [--testnet]

Example: python src/limit_orders.py BTCUSDT BUY 0.01 65000.0
"""

import sys
import argparse
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException

from config import BinanceConfig, TRADING_LIMITS
from utils import (
    setup_logger, validate_symbol, validate_side, validate_quantity, validate_price,
    format_quantity, format_price, log_order_attempt, log_order_success, log_order_error,
    ValidationError
)

class LimitOrderBot:
    """Limit order trading bot for Binance Futures"""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.client = Client(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        self.logger = setup_logger('LimitOrderBot')
        
    def validate_inputs(self, symbol: str, side: str, quantity: float, price: float) -> None:
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
        
        if not validate_price(price, TRADING_LIMITS['min_price']):
            errors.append(f"Invalid price: {price}. Must be >= {TRADING_LIMITS['min_price']}")
        
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
    
    def validate_limit_price(self, symbol: str, side: str, price: float) -> None:
        """Validate limit price against current market price"""
        try:
            current_price = self.get_current_price(symbol)
            self.logger.info(f"Current market price for {symbol}: {current_price}")
            
            # For BUY orders, limit price should typically be below market
            # For SELL orders, limit price should typically be above market
            # This is just a warning, not a blocking validation
            if side.upper() == 'BUY' and price > current_price:
                self.logger.warning(f"BUY limit price {price} is above market price {current_price}")
            elif side.upper() == 'SELL' and price < current_price:
                self.logger.warning(f"SELL limit price {price} is below market price {current_price}")
                
        except Exception as e:
            self.logger.warning(f"Could not validate limit price: {e}")
    
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
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> dict:
        """Place a limit order on Binance Futures"""
        
        # Validate inputs
        self.validate_inputs(symbol, side, quantity, price)
        
        # Validate limit price (warning only)
        self.validate_limit_price(symbol, side, price)
        
        # Get symbol info for precision
        symbol_info = self.get_symbol_info(symbol)
        
        # Format values with proper precision
        formatted_quantity = format_quantity(quantity, TRADING_LIMITS['quantity_precision'])
        formatted_price = format_price(price, TRADING_LIMITS['price_precision'])
        
        # Log attempt
        log_order_attempt(self.logger, "LIMIT", symbol, side, quantity, price)
        
        try:
            # Place limit order
            order = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type=Client.FUTURE_ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,  # Good Till Cancelled
                quantity=formatted_quantity,
                price=formatted_price
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
        description="Place limit orders on Binance USDT-M Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/limit_orders.py BTCUSDT BUY 0.01 65000.0
  python src/limit_orders.py ETHUSDT SELL 0.1 4000.0 --testnet
        """
    )
    
    parser.add_argument('symbol', help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', help='Order side (BUY or SELL)')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('price', type=float, help='Limit price')
    parser.add_argument('--testnet', action='store_true', 
                       help='Use testnet (default: from config)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = BinanceConfig.from_env()
        if args.testnet:
            config.testnet = True
            
        # Create bot instance
        bot = LimitOrderBot(config)
        
        # Place order
        result = bot.place_limit_order(args.symbol, args.side, args.quantity, args.price)
        
        print(f"✅ Limit order placed successfully!")
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Quantity: {result.get('origQty')}")
        print(f"Price: {result.get('price')}")
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

