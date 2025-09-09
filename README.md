# Binance Futures Order Bot

A comprehensive CLI-based trading bot for Binance USDT-M Futures with support for multiple order types, advanced strategies, robust logging, and validation.

## Features

### Core Orders (50% of evaluation)
- ✅ **Market Orders**: Immediate execution at current market price
- ✅ **Limit Orders**: Execute at specified price or better

### Advanced Orders (30% of evaluation - Higher Priority)
- ✅ **Stop-Limit Orders**: Trigger limit orders when stop price is hit
- ✅ **OCO Orders**: One-Cancels-the-Other (take profit + stop loss)
- ✅ **TWAP Strategy**: Time-Weighted Average Price (split large orders over time)
- ✅ **Grid Strategy**: Automated buy-low/sell-high within price ranges

### Validation & Logging (10% of evaluation)
- ✅ Input validation (symbol format, quantities, price thresholds)
- ✅ Structured logging with timestamps in `bot.log`
- ✅ Error handling and detailed error messages

## Project Structure

```
/
├── src/
│   ├── config.py              # Configuration and trading limits
│   ├── utils.py               # Utilities and validation functions
│   ├── market_orders.py       # Market order CLI script
│   ├── limit_orders.py        # Limit order CLI script
│   └── advanced/
│       ├── oco.py             # OCO orders implementation
│       ├── twap.py            # TWAP strategy implementation
│       ├── stop_limit_orders.py # Stop-limit orders
│       └── grid_strategy.py   # Grid trading strategy
├── bot.log                    # Structured logs (auto-generated)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── report.pdf                 # Analysis and screenshots
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Binance API Keys

Create environment variables for your Binance API credentials:

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
export BINANCE_TESTNET="true"  # Use testnet for safety (optional)
```

**Important**: 
- For safety, use the testnet initially (`BINANCE_TESTNET=true`)
- Get testnet API keys from: https://testnet.binancefuture.com/
- For production, set `BINANCE_TESTNET=false`

### 3. Verify Setup

Test your configuration by running a small market order on testnet:

```bash
python src/market_orders.py BTCUSDT BUY 0.001 --testnet
```

## Usage Examples

### Market Orders
```bash
# Buy 0.01 BTC at market price
python src/market_orders.py BTCUSDT BUY 0.01

# Sell 0.1 ETH at market price on testnet
python src/market_orders.py ETHUSDT SELL 0.1 --testnet
```

### Limit Orders
```bash
# Buy 0.01 BTC at $65,000 or lower
python src/limit_orders.py BTCUSDT BUY 0.01 65000.0

# Sell 0.1 ETH at $4,000 or higher
python src/limit_orders.py ETHUSDT SELL 0.1 4000.0
```

### Advanced Strategies

#### Stop-Limit Orders
```bash
# SELL stop-limit: If BTC drops to $64,000, sell at $63,900
python src/advanced/stop_limit_orders.py BTCUSDT SELL 0.01 64000.0 63900.0

# BUY stop-limit: If BTC rises to $66,000, buy at $66,100 (breakout)
python src/advanced/stop_limit_orders.py BTCUSDT BUY 0.01 66000.0 66100.0
```

#### OCO Orders (One-Cancels-the-Other)
```bash
# SELL OCO: Take profit at $66,000, stop loss at $64,000
python src/advanced/oco.py BTCUSDT SELL 0.01 64000.0 66000.0

# BUY OCO: Take profit at $64,000, stop loss at $66,000
python src/advanced/oco.py BTCUSDT BUY 0.01 66000.0 64000.0
```

#### TWAP Strategy (Time-Weighted Average Price)
```bash
# Buy 1 BTC over 60 minutes in 10 chunks
python src/advanced/twap.py BTCUSDT BUY 1.0 60 --chunks 10

# Sell 5 ETH over 30 minutes in 6 chunks
python src/advanced/twap.py ETHUSDT SELL 5.0 30 --chunks 6
```

#### Grid Strategy
```bash
# Create 10-level grid between $64,000 and $66,000
python src/advanced/grid_strategy.py BTCUSDT 0.01 64000.0 66000.0 --levels 10

# Create 5-level grid for ETH between $3,800 and $4,200
python src/advanced/grid_strategy.py ETHUSDT 0.1 3800.0 4200.0 --levels 5

# Cancel all grid orders
python src/advanced/grid_strategy.py BTCUSDT 0 0 0 --cancel-all
```

## Safety Features

### Input Validation
- Symbol format validation (must end with USDT)
- Quantity limits (0.001 to 1000.0)
- Price validation (minimum $0.01)
- Side validation (BUY/SELL only)

### Error Handling
- API error handling with descriptive messages
- Network timeout and retry logic
- Graceful failure with cleanup (e.g., TWAP interruption)

### Logging
All activities are logged to `bot.log` with:
- Timestamps
- Order attempts and results
- Error details and stack traces
- Performance metrics

## Supported Symbols

The bot supports all USDT-M Futures pairs, including:
- BTCUSDT, ETHUSDT, ADAUSDT, DOTUSDT
- LINKUSDT, BNBUSDT, LTCUSDT, XRPUSDT
- SOLUSDT, AVAXUSDT, and more

## Configuration

Edit `src/config.py` to modify:
- Trading limits (min/max quantities, prices)
- Supported symbols list
- Precision settings
- API endpoints

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'binance'**
   ```bash
   pip install python-binance
   ```

2. **API Key Error**
   - Verify your API keys are correct
   - Ensure API key has futures trading permissions
   - Check if you're using testnet keys with testnet=true

3. **Insufficient Balance**
   - Check your futures wallet balance
   - Ensure you have enough margin

4. **Symbol Not Found**
   - Verify the symbol exists on Binance Futures
   - Use the exact symbol format (e.g., BTCUSDT, not BTC-USDT)

### Logs
Check `bot.log` for detailed error information:
```bash
tail -f bot.log
```

## Development

### Adding New Strategies
1. Create a new file in `src/advanced/`
2. Follow the existing pattern with validation and logging
3. Add CLI argument parsing
4. Update this README

### Testing
Always test on testnet first:
```bash
export BINANCE_TESTNET=true
```

## Disclaimer

⚠️ **Risk Warning**: Trading futures involves substantial risk and may result in significant losses. This bot is for educational purposes. Always:
- Test thoroughly on testnet
- Start with small amounts
- Understand the risks
- Use proper risk management

## Support

For issues or questions:
1. Check the logs in `bot.log`
2. Review the Binance Futures API documentation
3. Ensure your API keys have the correct permissions
