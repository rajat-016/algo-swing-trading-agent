# Algo Swing Trading Agent

AI-powered swing trading agent for the Indian stock market using AI/ML intelligence and professional swing trading strategies.

## Overview

This project automates stock trading in the Indian market using:
- **Backend**: FastAPI (Python)
- **Frontend**: React.js
- **Database**: SQLite
- **Broker**: Zerodha Kite API
- **Stock Screening**: ChartInk
- **AI/ML**: Machine learning with 10 professional swing strategies

## Features

- **10 Professional Swing Strategies**: Trend Pullback, Breakout+Retest, Stage Analysis, Relative Strength, VCP, and more
- **Strategy-Specific Targets**: Each strategy has optimized target/stop-loss based on proven results
- **Auto-Strategy Detection**: AI automatically selects best strategy for each stock
- **20%+ Target**: Designed to generate 20%+ returns per stock
- **Paper Trading**: Test strategies without real money
- **Live Trading**: Switch to live trading when ready
- **Risk Management**: 1% risk per trade with position sizing
- **Real-time Monitoring**: Dashboard to track positions and P&L

## Architecture

```
algo-swing-trading-agent/
├── backend/                 # FastAPI backend
│   ├── api/                 # API endpoints
│   ├── core/                # Config, database, logging
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   │   ├── broker/          # Zerodha & ChartInk
│   │   ├── ai/              # ML features, model, analyzer
│   │   └── trading/         # Trading loop
│   ├── main.py              # Entry point
│   └── requirements.txt     # Dependencies
├── frontend/                # React frontend
│   ├── src/                 # React components
│   ├── public/              # Static files
│   └── package.json         # Dependencies
├── docker-compose.yml       # Docker deployment
└── README.md               # This file
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Zerodha trading account
- ChartInk account (for stock screening)

## Installation

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your settings
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install
```

### Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Configuration

### Environment Variables

Edit `backend/.env`:

```env
# Trading Parameters (default - overridden by strategy-specific targets)
TARGET_PROFIT_PCT=20.0
STOP_LOSS_PCT=3.0
MAX_POSITIONS=3
RISK_PER_TRADE=1.0
CYCLE_INTERVAL_SECONDS=300

# Trading Mode: 'paper' or 'live'
TRADING_MODE=paper

# Paper Trading Capital
PAPER_TRADING_CAPITAL=100000

# Database
DATABASE_URL=sqlite:///trading.db

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# ChartInk Screener URL
CHARTINK_URL=https://chartink.com/screener/your-screener

# Zerodha API (get from https://developers.kite.trade/)
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
ZERODHA_ACCESS_TOKEN=your_access_token
```

### Getting Zerodha API Credentials

1. Visit https://developers.kite.trade/
2. Create an app to get API Key and Secret
3. Generate access token using the request token flow

### ChartInk Setup

1. Create a screener at https://chartink.com/screener/
2. Copy the screener URL
3. Add to `.env` as `CHARTINK_URL`

## Running the Project

### Quick Start (Single Command)

```powershell
# Run with PowerShell
.\run.ps1
```

Options:
```powershell
# Paper trading (default)
.\run.ps1

# Live trading
.\run.ps1 -Mode live

# Full stack (backend + frontend)
.\run.ps1 -Full

# Full stack with live trading
.\run.ps1 -Full -Mode live

# Without Docker
.\run.ps1 -NoDocker
```

### Manual Setup

#### Backend Only

```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000`

#### Backend + Frontend (Development)

Terminal 1 - Backend:
```bash
cd backend
python main.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm start
```

Frontend will be available at `http://localhost:3000`

### Running with Docker

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

## API Endpoints

### Stocks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stocks/` | Get all stocks |
| GET | `/stocks/{symbol}` | Get stock by symbol |
| GET | `/stocks/status/{status}` | Get stocks by status |
| GET | `/stocks/summary/portfolio` | Get portfolio summary |
| POST | `/stocks/{symbol}/exit` | Exit a position |

### Trading

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/trading/status` | Get trading status |
| POST | `/trading/mode` | Switch paper/live mode |
| POST | `/trading/start` | Start trading loop |
| POST | `/trading/stop` | Stop trading loop |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |

## Trading Modes

### Paper Trading (Default)

- Simulated trading with fake money
- No real orders placed
- Default capital: ₹100,000
- Safe for testing strategies

### Live Trading

- Real money at risk
- Orders placed via Zerodha API
- Requires valid API credentials

### Switching Modes

Via API:
```bash
curl -X POST http://localhost:8000/trading/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "live"}'
```

Via Frontend:
Click "Paper Mode" or "Live Mode" buttons in the dashboard.

## Trading Flow

```
ChartInk Screener → Fetch stock list
       ↓
StockAnalyzer.analyze() → For each stock:
  - Fetch OHLCV data from Kite
  - Fetch NIFTY data (for relative strength)
  - Calculate features (80+ indicators)
  - Score each strategy (10 strategies)
  - Auto-detect best matching strategy
       ↓
ML Model Prediction + Strategy-Specific Target
       ↓
Entry: buy signal, entry price, strategy-based target/SL
```

## 10 Professional Swing Strategies

This AI system implements 10 proven swing trading strategies from expert traders:

| # | Strategy | Target | Stop Loss | Description |
|---|---------|--------|---------|-------------|
| 1 | Trend Pullback | 25% | 3% | Buy on pullbacks to EMA20 in uptrend |
| 2 | Breakout+Retest | 20% | 3% | Wait for retest after breakout |
| 3 | Stage Analysis | 30% | 4% | Weinstein method (Stage 2 buy) |
| 4 | Relative Strength | 18% | 3% | Outperform NIFTY 50 |
| 5 | VCP | 35% | 4% | Volatility contraction pattern |
| 6 | Gap-Up | 15% | 2% | Professional gap-up setup |
| 7 | Support Zone | 20% | 3% | Support zone reversal |
| 8 | Sector Rotation | 25% | 3% | Trade strong sectors |
| 9 | Multi-Timeframe | 20% | 3% | Weekly+daily alignment |
| 10 | Risk Management | 1% | 3% | Position sizing only |

### Strategy Descriptions

**Strategy 1: Trend Pullback (My #1 Money Maker)**
- Concept: Buy strong stocks on pullbacks to EMA20/50, not breakouts
- Trend is your edge, pullback is your entry
- Timeframe: Daily + Weekly for trend confirmation

**Strategy 2: Breakout + Retest**
- Most traders buy breakout candles, professionals wait for retest
- Fake breakouts trap traders, retests confirm real buyers
- Dramatically improves breakout success rate

**Strategy 3: Stage Analysis (Weinstein Method)**
- Four stages: Base, Uptrend, Distribution, Downtrend
- Buy during Stage 2 beginning
- Very powerful in Indian markets

**Strategy 4: Relative Strength**
- Professionals don't buy weak stocks
- Buy stocks outperforming NIFTY 50
- Money flows into strong stocks first

**Strategy 5: VCP (Volatility Contraction Pattern)**
- Stock forms tightening price ranges
- Volume decreases as range contracts
- Then explosive breakout

**Strategy 6: Gap-Up Professional**
- Retail traders chase gaps, professionals wait
- Wait 30-60 minutes for consolidation
- Buy when price holds above VWAP

**Strategy 7: Support Zone Reversal**
- Smart money accumulates at support
- Look for hammer/bullish engulfing at support
- Simple but effective

**Strategy 8: Sector Rotation**
- Most traders ignore sectors, professionals trade sectors
- Find strongest sectors, pick strongest stocks
- Monitor NIFTY BANK, NIFTY IT

**Strategy 9: Multi-Timeframe**
- Trade only when weekly trend = UP + daily = pullback
- Weekly confirms direction, daily finds entry
- This reduces bad trades significantly

## AI/ML Technical Details

### Feature Engineering (80+ indicators)

1. **Price Features**: returns, log_returns, price_range, HL ratio
2. **Moving Averages**: SMA, EMA (5-200 periods), crossovers
3. **Momentum**: RSI, MACD, ROC, momentum
4. **Volatility**: ATR, Bollinger Bands, stddev
5. **Volume**: Volume ratio, OBV, VWAP
6. **Strategy-Specific** (NEW):
   - Trend Pullback: ema_20_above_50, pullback_pct, trend_strength
   - Breakout: breakout_volume, retest_holds, resistance_distance
   - Stage: stage, stage_2_start, weekly_ma_30
   - Relative Strength: vs_nifty_return, nifty_correlation
   - VCP: range_contraction, tightness_score, vcp_signal
   - Support Zone: reversal_candle, near_support
   - Multi-Timeframe: weekly_trend, daily_weekly_aligned

### ML Model

- **Type**: Gradient Boosting Classifier
- **Estimators**: 150 trees
- **Data**: 60-day historical (60min candles)
- **Prediction**: BUY/HOLD/SELL with confidence

### Entry Decision Process

1. Fetch stock data from Kite
2. Generate strategy features
3. Calculate scores for each of 10 strategies
4. Select strategy with highest score
5. Get strategy-specific target/stop-loss
6. Run ML prediction
7. Apply strategy filter and confidence threshold
8. Calculate position size (1% risk rule)
9. Place entry order

### Position Sizing

- **Risk**: 1% of capital per trade (golden rule)
- **Formula**: Position Size = Risk Amount / (Entry - Stop Loss)
- **Max Exposure**: 60% of capital across positions
- **Max Positions**: 3 concurrent

### Strategy-Specific Configuration

Defined in `backend/core/config.py`:

```python
STRATEGY_TARGETS = {
    "trend_pullback": {"target": 0.25, "stop_loss": 0.03, "min_score": 0.6},
    "breakout_retest": {"target": 0.20, "stop_loss": 0.03, "min_score": 0.6},
    "stage_2": {"target": 0.30, "stop_loss": 0.04, "min_score": 0.6},
    "relative_strength": {"target": 0.18, "stop_loss": 0.03, "min_score": 0.5},
    "vcp": {"target": 0.35, "stop_loss": 0.04, "min_score": 0.7},
    "gap_up": {"target": 0.15, "stop_loss": 0.02, "min_score": 0.6},
    "support_zone": {"target": 0.20, "stop_loss": 0.03, "min_score": 0.5},
    "sector_rotation": {"target": 0.25, "stop_loss": 0.03, "min_score": 0.6},
    "multi_timeframe": {"target": 0.20, "stop_loss": 0.03, "min_score": 0.6},
}
```

## Database Schema

### Stocks Table

| Column | Type | Description |
|--------|------|-------------|
| symbol | String | Stock symbol (unique) |
| status | Enum | PENDING, ENTERED, EXITED |
| broker_status | Enum | OPEN, HOLDING, REJECTED, COMPLETE, TRIGGER_PENDING |
| entry_price | Float | Entry price |
| target_price | Float | Target price |
| stop_loss | Float | Stop loss price |
| entry_quantity | Integer | Number of shares |
| pnl | Float | Profit/Loss |
| pnl_percentage | Float | P&L percentage |
| entry_reason | String | AI reason for entry |
| ai_confidence | Float | ML confidence score |
| strategy | String | Trading strategy used |
| entry_date | DateTime | Entry timestamp |
| exit_date | DateTime | Exit timestamp |
| exit_reason | Enum | TARGET, SL, MANUAL, ORDER_REJECTED |

## Development

### Project Structure (Backend)

```
backend/
├── api/
│   ├── main.py           # FastAPI app
│   └── routes/           # API endpoints
│       ├── stocks.py
│       ├── trading.py
│       └── websocket.py
├── core/
│   ├── config.py         # Settings + STRATEGY_TARGETS
│   ├── database.py       # DB connection
│   ├── enums.py         # Enumerations
│   └── logging.py       # Logging config
├── models/
│   └── stock.py         # Stock model
└── services/
    ├── broker/           # Broker integrations
    │   ├── kite.py       # Zerodha Kite (get_nifty_data, get_weekly_data)
    │   └── chartink.py  # ChartInk screener
    ├── ai/              # AI/ML
    │   ├── features.py   # 80+ indicators + strategy features
    │   ├── model.py    # ModelTrainer
    │   ├── adaptive_model.py # AdaptiveModel with strategy detection
    │   ├── analyzer.py # StockAnalyzer with strategy scores
    │   ├── train_model.py # Training pipeline
    │   └── strategy_optimizer.py
    ├── trading/
    │   └── loop.py     # Trading loop
    └── risk/
        └── manager.py # Risk management
```

### Running Tests

```bash
cd backend
pytest tests/
```

### Adding New Features

1. **New Broker**: Add to `services/broker/`
2. **New Strategy**: Modify `services/ai/analyzer.py`
3. **New Indicator**: Add to `services/ai/features.py`

## Troubleshooting

### Common Issues

1. **Zerodha Connection Failed**
   - Check API credentials in `.env`
   - Ensure access token is valid

2. **ChartInk Not Fetching Stocks**
   - Verify screener URL
   - Check cookies if required

3. **Database Errors**
   - Delete `trading.db` and restart
   - Check SQLite permissions

4. **Frontend Not Connecting to Backend**
   - CORS might be blocked
   - Check API URL in frontend

### Logs

Backend logs are stored in `backend/logs/app.log`

## Deployment

### Self-Hosted (Recommended)

Use Docker Compose for easy deployment:

```bash
# Production build
docker-compose -f docker-compose.yml up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Cloud Hosting

Compatible with:
- Railway
- Render
- Heroku
- DigitalOcean App Platform

## License

MIT License

## Support

For issues and questions:
- Open an issue on GitHub
- Check the wiki for detailed documentation

## Roadmap

- [x] 10 Professional Swing Strategies
- [x] Strategy Auto-Detection
- [x] Strategy-Specific Targets
- [x] Relative Strength (NIFTY)
- [x] Multi-Timeframe Analysis
- [ ] Backtesting module
- [ ] Telegram notifications
- [ ] Portfolio rebalancing
- [ ] Multi-broker support
- [ ] Alternative ML models (LSTM, Transformer)
