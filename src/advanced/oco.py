#!/usr/bin/env python3
"""
OCO Orders - One-Cancels-the-Other order logic for Binance Futures
Places both a take-profit and stop-loss order simultaneously

Usage: python src/advanced/oco.py SYMBOL SIDE QUANTITY STOP_PRICE LIMIT_PRICE [--testnet]

Example: python src/advanced/oco.py BTCUSDT SELL 0.01 64000.0 66000.0
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

class OCOOrderBot:
    """OCO (One-Cancels-the-Other) order trading bot for Binance Futures"""
    
    def __init__(self, config: BinanceConfig):
        self.config = config
        self.client = Client(
            api_key=config.api_key,
            api_secret=config.api_secret,
            testnet=config.testnet
        )
        self.logger = setup_logger('OCOOrderBot')
        
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
        
        # Validate price relationships
        if side.upper() == 'SELL':
            if stop_price >= limit_price:
                errors.append(f"For SELL OCO: stop_price ({stop_price}) must be < limit_price ({limit_price})")
        else:  # BUY
            if stop_price <= limit_price:
                errors.append(f"For BUY OCO: stop_price ({stop_price}) must be > limit_price ({limit_price})")
        
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
    
    def validate_oco_prices(self, symbol: str, side: str, stop_price: float, limit_price: float) -> None:
        """Validate OCO prices against current market price"""
        try:
            current_price = self.get_current_price(symbol)
            self.logger.info(f"Current market price for {symbol}: {current_price}")
            
            if side.upper() == 'SELL':
                # For SELL OCO: current < stop < limit
                if current_price >= stop_price:
                    self.logger.warning(f"SELL OCO: Current price {current_price} should be below stop price {stop_price}")
                if stop_price >= limit_price:
                    raise ValidationError(f"SELL OCO: Stop price {stop_price} must be below limit price {limit_price}")
            else:  # BUY
                # For BUY OCO: current > stop > limit  
                if current_price <= stop_price:
                    self.logger.warning(f"BUY OCO: Current price {current_price} should be above stop price {stop_price}")
                if stop_price <= limit_price:
                    raise ValidationError(f"BUY OCO: Stop price {stop_price} must be above limit price {limit_price}")
                    
        except Exception as e:
            self.logger.warning(f"Could not validate OCO prices: {e}")
    
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
    
    def place_oco_order(self, symbol: str, side: str, quantity: float, 
                       stop_price: float, limit_price: float) -> dict:
        """
        Place OCO order on Binance Futures
        Note: Binance Futures doesn't have native OCO, so we simulate with separate orders
        """
        
        # Validate inputs
        self.validate_inputs(symbol, side, quantity, stop_price, limit_price)
        
        # Validate OCO price relationships
        self.validate_oco_prices(symbol, side, stop_price, limit_price)
        
        # Get symbol info for precision
        symbol_info = self.get_symbol_info(symbol)
        
        # Format values with proper precision
        formatted_quantity = format_quantity(quantity, TRADING_LIMITS['quantity_precision'])
        formatted_stop_price = format_price(stop_price, TRADING_LIMITS['price_precision'])
        formatted_limit_price = format_price(limit_price, TRADING_LIMITS['price_precision'])
        
        orders_placed = []
        
        try:
            # Place stop-limit order (acts as stop-loss)
            self.logger.info(f"Placing stop-limit order: {side} {quantity} {symbol} @ stop={stop_price}")
            
            stop_order = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type=Client.FUTURE_ORDER_TYPE_STOP,
                quantity=formatted_quantity,
                stopPrice=formatted_stop_price,
                timeInForce=Client.TIME_IN_FORCE_GTC
            )
            
            orders_placed.append(stop_order)
            log_order_success(self.logger, stop_order)
            
            # Place limit order (acts as take-profit)
            self.logger.info(f"Placing limit order: {side} {quantity} {symbol} @ {limit_price}")
            
            limit_order = self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type=Client.FUTURE_ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=formatted_quantity,
                price=formatted_limit_price
            )
            
            orders_placed.append(limit_order)
            log_order_success(self.logger, limit_order)
            
            # Return combined result
            result = {
                'oco_type': 'SIMULATED',
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'stop_order': stop_order,
                'limit_order': limit_order,
                'orders_count': len(orders_placed)
            }
            
            self.logger.info(f"OCO order simulation completed: {len(orders_placed)} orders placed")
            return result
            
        except Exception as e:
            # If any order fails, try to cancel previously placed orders
            if orders_placed:
                self.logger.warning(f"OCO placement failed, attempting to cancel {len(orders_placed)} orders")
                for order in orders_placed:
                    try:
                        self.client.futures_cancel_order(
                            symbol=symbol.upper(),
                            orderId=order['orderId']
                        )
                        self.logger.info(f"Cancelled order {order['orderId']}")
                    except Exception as cancel_error:
                        self.logger.error(f"Failed to cancel order {order['orderId']}: {cancel_error}")
            
            log_order_error(self.logger, e, f"OCO order for {symbol}")
            raise

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Place OCO (One-Cancels-the-Other) orders on Binance USDT-M Futures",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SELL OCO: Take profit at 66000, Stop loss at 64000
  python src/advanced/oco.py BTCUSDT SELL 0.01 64000.0 66000.0
  
  # BUY OCO: Take profit at 64000, Stop loss at 66000  
  python src/advanced/oco.py BTCUSDT BUY 0.01 66000.0 64000.0
        """
    )
    
    parser.add_argument('symbol', help='Trading pair symbol (e.g., BTCUSDT)')
    parser.add_argument('side', help='Order side (BUY or SELL)')
    parser.add_argument('quantity', type=float, help='Order quantity')
    parser.add_argument('stop_price', type=float, help='Stop price (triggers stop order)')
    parser.add_argument('limit_price', type=float, help='Limit price (take profit level)')
    parser.add_argument('--testnet', action='store_true', 
                       help='Use testnet (default: from config)')
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = BinanceConfig.from_env()
        if args.testnet:
            config.testnet = True
            
        # Create bot instance
        bot = OCOOrderBot(config)
        
        # Place OCO order
        result = bot.place_oco_order(
            args.symbol, args.side, args.quantity, 
            args.stop_price, args.limit_price
        )
        
        print(f"✅ OCO order placed successfully!")
        print(f"Symbol: {result['symbol']}")
        print(f"Side: {result['side']}")
        print(f"Quantity: {result['quantity']}")
        print(f"Stop Order ID: {result['stop_order']['orderId']}")
        print(f"Limit Order ID: {result['limit_order']['orderId']}")
        print(f"⚠️  Note: This is a simulated OCO using separate orders")
        
    except ValidationError as e:
        print(f"❌ Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

