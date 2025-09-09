#!/usr/bin/env python3
"""
Demo Script - Demonstrates Binance Futures Trading Bot capabilities
This script shows all features without placing real orders (testnet recommended)
"""

import os
import sys
import time

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'-'*40}")
    print(f"  {title}")
    print(f"{'-'*40}")

def run_command(description, command, wait=2):
    """Run a command with description"""
    print(f"\n🚀 {description}")
    print(f"Command: {command}")
    
    # Ask user if they want to run it
    run_it = input("Run this command? (y/N): ").strip().lower()
    if run_it == 'y':
        os.system(command)
        time.sleep(wait)
    else:
        print("⏭️  Skipped")

def main():
    """Main demo function"""
    print_header("Binance Futures Trading Bot - DEMO")
    
    print("This demo showcases all bot capabilities.")
    print("⚠️  Make sure you're using testnet (BINANCE_TESTNET=true)")
    print("⚠️  All examples use small quantities for safety")
    
    # Check if setup is complete
    if not os.path.exists('.env'):
        print("\n❌ Configuration not found!")
        print("Please run: python setup.py")
        return 1
    
    print_section("1. Core Orders (50% of evaluation)")
    
    run_command(
        "Market Order - Buy 0.001 BTC immediately",
        "python src/market_orders.py BTCUSDT BUY 0.001 --testnet"
    )
    
    run_command(
        "Limit Order - Buy 0.001 BTC at $60,000",
        "python src/limit_orders.py BTCUSDT BUY 0.001 60000.0 --testnet"
    )
    
    print_section("2. Advanced Orders (30% of evaluation - Higher Priority)")
    
    run_command(
        "Stop-Limit Order - Sell with stop-loss protection",
        "python src/advanced/stop_limit_orders.py BTCUSDT SELL 0.001 64000.0 63900.0 --testnet"
    )
    
    run_command(
        "OCO Order - Simultaneous take-profit and stop-loss",
        "python src/advanced/oco.py BTCUSDT SELL 0.001 64000.0 66000.0 --testnet"
    )
    
    run_command(
        "TWAP Strategy - Split 0.01 BTC over 5 minutes in 5 chunks",
        "python src/advanced/twap.py BTCUSDT BUY 0.01 5 --chunks 5 --testnet"
    )
    
    run_command(
        "Grid Strategy - Create 5-level grid between $64,000-$66,000",
        "python src/advanced/grid_strategy.py BTCUSDT 0.001 64000.0 66000.0 --levels 5 --testnet"
    )
    
    print_section("3. Unified Interface")
    
    run_command(
        "Using unified bot interface for market order",
        "python bot.py market BTCUSDT BUY 0.001 --testnet"
    )
    
    run_command(
        "Using unified bot interface for TWAP strategy",
        "python bot.py twap BTCUSDT BUY 0.005 3 --chunks 3 --testnet"
    )
    
    print_section("4. Testing & Validation")
    
    run_command(
        "Run comprehensive test suite",
        "python test_bot.py"
    )
    
    print_section("5. Logging & Monitoring")
    
    print("\n📋 Check bot.log for detailed execution logs:")
    if os.path.exists('bot.log'):
        print("Last 10 log entries:")
        os.system("tail -10 bot.log")
    else:
        print("No log file found yet - run some orders first!")
    
    print_header("Demo Completed!")
    
    print("🎉 All bot features demonstrated!")
    print("\n📝 Next Steps:")
    print("1. Check bot.log for detailed execution logs")
    print("2. Try different symbols (ETHUSDT, ADAUSDT, etc.)")
    print("3. Experiment with different quantities and prices")
    print("4. Read the documentation in README.md")
    print("5. Fill out the report template in REPORT_TEMPLATE.md")
    
    print("\n⚠️  Remember:")
    print("- Always test on testnet first")
    print("- Start with small quantities")
    print("- Understand the risks of futures trading")
    print("- This bot is for educational purposes")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Demo cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)
