#!/usr/bin/env python3
"""
Test Script - Verify bot setup without placing real orders
Tests configuration, validation, and API connectivity
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config import BinanceConfig, TRADING_LIMITS, SUPPORTED_SYMBOLS
from utils import (
    setup_logger, validate_symbol, validate_side, validate_quantity, 
    validate_price, ValidationError
)

def test_validation():
    """Test input validation functions"""
    print("🧪 Testing input validation...")
    
    # Test symbol validation
    valid_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    invalid_symbols = ['BTC', 'BTCUSD', 'btcusdt', '']
    
    for symbol in valid_symbols:
        assert validate_symbol(symbol), f"Should validate: {symbol}"
    
    for symbol in invalid_symbols:
        if symbol == 'btcusdt':
            # btcusdt should now validate since we convert to uppercase
            assert validate_symbol(symbol), f"Should validate (case insensitive): {symbol}"
        else:
            assert not validate_symbol(symbol), f"Should not validate: {symbol}"
    
    # Test side validation
    assert validate_side('BUY')
    assert validate_side('SELL')
    assert validate_side('buy')  # case insensitive
    assert not validate_side('HOLD')
    assert not validate_side('')
    
    # Test quantity validation
    assert validate_quantity(0.01)
    assert validate_quantity(1.0)
    assert not validate_quantity(0.0001)  # too small
    assert not validate_quantity(10000)   # too large
    
    # Test price validation
    assert validate_price(100.0)
    assert validate_price(0.01)
    assert not validate_price(0.001)  # too small
    assert not validate_price(-1.0)   # negative
    
    print("✅ All validation tests passed!")

def test_configuration():
    """Test configuration loading"""
    print("🧪 Testing configuration...")
    
    # Test default config values
    assert TRADING_LIMITS['min_quantity'] == 0.001
    assert TRADING_LIMITS['max_quantity'] == 1000.0
    assert 'BTCUSDT' in SUPPORTED_SYMBOLS
    
    print("✅ Configuration tests passed!")

def test_logging():
    """Test logging setup"""
    print("🧪 Testing logging...")
    
    logger = setup_logger('TestBot')
    logger.info("Test log message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Check if log file exists
    log_file = 'bot.log'
    if os.path.exists(log_file):
        print(f"✅ Log file created: {log_file}")
    else:
        print(f"❌ Log file not found: {log_file}")
    
    print("✅ Logging tests completed!")

def test_api_configuration():
    """Test API configuration (without making actual calls)"""
    print("🧪 Testing API configuration...")
    
    try:
        # This will fail if environment variables are not set
        # That's expected for testing - we're just checking the config loading
        config = BinanceConfig.from_env()
        print("✅ Environment variables found!")
        print(f"   Using testnet: {config.testnet}")
        
    except ValueError as e:
        print(f"⚠️  Environment variables not set: {e}")
        print("   This is expected if you haven't configured API keys yet")
        print("   Set BINANCE_API_KEY and BINANCE_API_SECRET to test with real API")
    
    print("✅ API configuration test completed!")

def test_strategy_imports():
    """Test that all strategy modules can be imported"""
    print("🧪 Testing strategy imports...")
    
    try:
        from market_orders import MarketOrderBot
        print("✅ Market orders module imported")
        
        from limit_orders import LimitOrderBot  
        print("✅ Limit orders module imported")
        
        # Advanced strategies
        sys.path.append(os.path.join('src', 'advanced'))
        
        from oco import OCOOrderBot
        print("✅ OCO orders module imported")
        
        from twap import TWAPOrderBot
        print("✅ TWAP strategy module imported")
        
        from stop_limit_orders import StopLimitOrderBot
        print("✅ Stop-limit orders module imported")
        
        from grid_strategy import GridStrategyBot
        print("✅ Grid strategy module imported")
        
        print("✅ All strategy modules imported successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Binance Futures Trading Bot Tests\n")
    
    try:
        test_validation()
        print()
        
        test_configuration()
        print()
        
        test_logging()
        print()
        
        test_api_configuration()
        print()
        
        success = test_strategy_imports()
        print()
        
        if success:
            print("🎉 All tests completed successfully!")
            print("\n📝 Next steps:")
            print("1. Set up your API keys in environment variables")
            print("2. Test with a small order on testnet:")
            print("   python src/market_orders.py BTCUSDT BUY 0.001 --testnet")
            print("3. Check bot.log for detailed logging")
        else:
            print("❌ Some tests failed. Check the errors above.")
            return 1
            
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
