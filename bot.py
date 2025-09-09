#!/usr/bin/env python3
"""
Main Bot Launcher - Unified entry point for all trading strategies
Usage: python bot.py --help
"""

import argparse
import sys
import os

def main():
    """Main CLI entry point with strategy selection"""
    
    parser = argparse.ArgumentParser(
        description="Binance Futures Trading Bot - Unified Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Strategies:

Basic Orders:
  market       Market orders (immediate execution)
  limit        Limit orders (execute at specific price)

Advanced Orders:
  stop-limit   Stop-limit orders (trigger limit on stop price)
  oco          OCO orders (One-Cancels-the-Other)
  twap         TWAP strategy (Time-Weighted Average Price)
  grid         Grid trading strategy (buy-low/sell-high)

Examples:
  python bot.py market BTCUSDT BUY 0.01
  python bot.py limit BTCUSDT BUY 0.01 65000.0
  python bot.py oco BTCUSDT SELL 0.01 64000.0 66000.0
  python bot.py twap BTCUSDT BUY 1.0 60 --chunks 10
  python bot.py grid BTCUSDT 0.01 64000.0 66000.0 --levels 10

For strategy-specific help:
  python bot.py market --help
  python bot.py twap --help
        """
    )
    
    parser.add_argument('strategy', 
                       choices=['market', 'limit', 'stop-limit', 'oco', 'twap', 'grid'],
                       help='Trading strategy to execute')
    
    # Parse known args to get strategy, then delegate to specific script
    args, remaining_args = parser.parse_known_args()
    
    # Map strategies to their script files
    strategy_scripts = {
        'market': 'src/market_orders.py',
        'limit': 'src/limit_orders.py',
        'stop-limit': 'src/advanced/stop_limit_orders.py',
        'oco': 'src/advanced/oco.py',
        'twap': 'src/advanced/twap.py',
        'grid': 'src/advanced/grid_strategy.py'
    }
    
    script_path = strategy_scripts[args.strategy]
    
    # Check if script exists
    if not os.path.exists(script_path):
        print(f"❌ Error: Strategy script not found: {script_path}")
        sys.exit(1)
    
    # Execute the specific strategy script with remaining arguments
    import subprocess
    
    cmd = [sys.executable, script_path] + remaining_args
    
    try:
        result = subprocess.run(cmd, check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
