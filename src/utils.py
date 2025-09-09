"""
Utility functions for Binance Futures Trading Bot
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import re

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Set up structured logging with timestamps"""
    if log_file is None:
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.log')
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    if not symbol:
        return False
    
    # Check if symbol follows pattern (e.g., BTCUSDT)
    # Convert to uppercase for validation
    pattern = r'^[A-Z]{3,10}USDT$'
    return bool(re.match(pattern, symbol.upper()))

def validate_side(side: str) -> bool:
    """Validate order side (BUY/SELL)"""
    return side.upper() in ['BUY', 'SELL']

def validate_quantity(quantity: float, min_qty: float = 0.001, max_qty: float = 1000.0) -> bool:
    """Validate order quantity"""
    if not isinstance(quantity, (int, float)):
        return False
    return min_qty <= quantity <= max_qty

def validate_price(price: float, min_price: float = 0.01) -> bool:
    """Validate price value"""
    if not isinstance(price, (int, float)):
        return False
    return price >= min_price

def format_quantity(quantity: float, precision: int = 3) -> str:
    """Format quantity with proper precision"""
    return f"{quantity:.{precision}f}"

def format_price(price: float, precision: int = 8) -> str:
    """Format price with proper precision"""
    return f"{price:.{precision}f}"

def log_order_attempt(logger: logging.Logger, order_type: str, symbol: str, 
                     side: str, quantity: float, price: Optional[float] = None) -> None:
    """Log order placement attempt"""
    price_str = f" at {price}" if price else ""
    logger.info(f"Attempting {order_type} order: {side} {quantity} {symbol}{price_str}")

def log_order_success(logger: logging.Logger, order_response: Dict[str, Any]) -> None:
    """Log successful order placement"""
    order_id = order_response.get('orderId', 'Unknown')
    symbol = order_response.get('symbol', 'Unknown')
    side = order_response.get('side', 'Unknown')
    quantity = order_response.get('origQty', 'Unknown')
    logger.info(f"Order placed successfully: ID={order_id}, {side} {quantity} {symbol}")

def log_order_error(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """Log order placement error"""
    logger.error(f"Order failed {context}: {str(error)}")

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass
