"""
Configuration file for Binance Futures Trading Bot
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class BinanceConfig:
    """Configuration for Binance API"""
    api_key: str
    api_secret: str
    testnet: bool = True  # Use testnet by default for safety
    base_url: str = "https://testnet.binancefuture.com"
    
    @classmethod
    def from_env(cls) -> 'BinanceConfig':
        """Create config from environment variables"""
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        
        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set")
            
        return cls(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet
        )

# Trading limits and validation rules
TRADING_LIMITS = {
    'min_quantity': 0.001,
    'max_quantity': 1000.0,
    'min_price': 0.01,
    'price_precision': 8,
    'quantity_precision': 3
}

# Supported symbols (can be extended)
SUPPORTED_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT',
    'BNBUSDT', 'LTCUSDT', 'XRPUSDT', 'SOLUSDT', 'AVAXUSDT'
]
