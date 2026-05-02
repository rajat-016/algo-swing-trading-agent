# Algo Swing Trading Agent

AI-powered swing trading agent for the Indian stock market using AI/ML intelligence and professional swing trading strategies.

## Overview

This project automates stock trading in the Indian market using:
- **Backend**: FastAPI (Python)
- **Frontend**: React.js
- **Database**: SQLite
- **Broker**: Zerodha Kite API
- **Stock Screening**: ChartInk
- **AI/ML**: XGBoost with 80+ features and adaptive labeling

## Features

- **10 Professional Swing Strategies**: Trend Pullback, Breakout+Retest, Stage Analysis, Relative Strength, VCP, and more
- **Strategy-Specific Targets**: Each strategy has optimized target/stop-loss based on proven results
- **Auto-Strategy Detection**: AI automatically selects best strategy for each stock
- **20%+ Target**: Designed to generate 20%+ returns per stock
- **Paper Trading**: Test strategies without real money
- **Live Trading**: Switch to live trading when ready
- **Walk-Forward Backtesting**: Offline validation with 5+ years historical data
- **XGBoost ML Model**: 3-class prediction (STRONG_BUY/HOLD/SELL) with ATR-based adaptive labeling
- **Risk Management**: 1% risk per trade with position sizing
- **Real-time Monitoring**: Dashboard to track positions and P&L

## Architecture

```
algo-swing-trading-agent/
├── backend/                 # FastAPI backend (live trading)
│   ├── api/                 # API endpoints
│   ├── core/                # Config, database, logging
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   │   ├── broker/          # Zerodha & ChartInk
│   │   ├── ai/              # ML features, model, analyzer
│   │   └── trading/         # Trading loop
│   ├── main.py              # Entry point
│   └── requirements.txt     # Dependencies
├── backtesting/             # Walk-forward backtesting engine (offline)
│   ├── data_pipeline/       # Yahoo Finance + DuckDB
│   ├── training/            # Walk-forward trainer
│   ├── backtest_engine/     # Trade simulator
│   ├── metrics/             # Performance metrics
│   ├── model_selection/      # Best model selector
│   ├── analysis/            # Report analysis
│   ├── config/              # backtest_config.yaml
│   └── run_backtest.py      # Entry point
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
  - Fetch NIFTY 50 data (for relative strength)
  - Calculate features (80+ indicators)
  - Score each strategy (10 strategies)
  - Auto-detect best matching strategy
       ↓
XGBoost ML Model Prediction (3-class) + Strategy-Specific Target
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
4. **Volatility**: ATR, Bollinger Bands, stddev, historical volatility
5. **Volume**: Volume ratio, OBV, VWAP, order flow
6. **Strategy-Specific**:
   - Trend Pullback: ema_20_above_50, pullback_pct, trend_strength
   - Breakout: breakout_volume, retest_holds, resistance_distance
   - Stage: stage, stage_2_start, weekly_ma_30
   - Relative Strength: vs_nifty_return, nifty_correlation, nifty_bias
   - VCP: range_contraction, tightness_score, vcp_signal
   - Support Zone: reversal_candle, near_support
   - Multi-Timeframe: weekly_trend, daily_weekly_aligned
7. **Candlestick Patterns**: hammer, engulfing, morning/evening star, etc.
8. **Advanced Volatility**: Kelly bands, Donchian channels
9. **Market Context**: market_correlation, momentum_persistency, trend_persistency
10. **Price Action**: Pivot points, Fibonacci retracements, gap analysis

### ML Model

- **Type**: XGBoost Classifier
- **Classes**: 3-class output (STRONG_BUY=2, HOLD=0, SELL=-2)
- **Estimators**: 300 trees (configurable)
- **Data**: 5+ years historical (daily candles)
- **Training**: Walk-forward validation with sample weights for class balance
- **Prediction**: STRONG_BUY/HOLD/SELL with confidence scores

### Labeling Method

Adaptive 3-class labeling based on ATR (Average True Range):
- **STRONG_BUY (2)**: Future return > adaptive_target (ATR-based, min 3%)
- **HOLD (0)**: Return between -adaptive_stop and +adaptive_target
- **SELL (-2)**: Future return < -adaptive_stop (ATR-based, min 3%)

Uses 10-day lookahead period with ATR-scaled stop-loss and target thresholds.

### Entry Decision Process

1. Fetch stock data from Kite
2. Generate 80+ strategy features
3. Calculate scores for each of 10 strategies
4. Select strategy with highest score
5. Get strategy-specific target/stop-loss
6. Run ML prediction (3-class XGBoost)
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

## Walk-Forward Backtesting System

> Offline training and validation engine that improves model reliability before live deployment.
> **Completely isolated** from the live trading system — no broker connections, no shared state.

### Purpose

- Trains the ML model with 5+ years of historical data (Yahoo Finance)
- Validates robustness via walk-forward sequential windows
- Simulates trades and evaluates Sharpe, Drawdown, Win Rate, Accuracy
- Exports best-performing model for manual review before live deployment

### Architecture

```
algo-swing-trading-agent/
├── backend/                    ← LIVE TRADING (never modified by backtesting)
│
├── backtesting/                ← OFFLINE: walk-forward engine
│   ├── data_pipeline/          ← Yahoo fetcher, DuckDB storage
│   ├── feature_engineering/    ← Reuses backend FeatureEngineer
│   ├── labeling/               ← 3-class BUY/HOLD/SELL label generation
│   ├── training/               ← Walk-forward splits, model trainer
│   ├── backtest_engine/        ← Trade simulator, position manager
│   ├── metrics/                ← Sharpe, CAGR, Drawdown, ML metrics
│   ├── model_selection/        ← Best model selector with threshold gates
│   ├── analysis/               ← Report analysis & health checks
│   ├── export/                 ← Versioned model + metadata + reports
│   ├── config/
│   │   └── backtest_config.yaml
│   ├── data/
│   │   └── market_data.duckdb  ← Isolated database
│   ├── models/                 ← Output: versioned models
│   ├── reports/                ← Output: metrics.json, trades.csv
│   ├── logs/
│   ├── requirements.txt        ← Separate deps (yfinance, duckdb)
│   └── run_backtest.py         ← Entry point
│
└── frontend/
```

### Installation

```bash
cd backtesting
pip install -r requirements.txt
```

### Usage

```bash
# Validate pipeline (no data fetch, no training)
python run_backtest.py --dry-run

# Full walk-forward pipeline
python run_backtest.py

# Skip safeguard confirmations (CI/automation)
python run_backtest.py --force

# Analyze latest backtest report
python run_backtest.py --analyze
```

### Safeguards

| Safeguard | Behavior |
|-----------|----------|
| Market hours check | Blocks execution during 9:15 AM – 3:30 PM IST (NSE hours) |
| Live process detection | Detects if `backend/main.py` is running, prompts confirmation |
| Import guard | Scans for forbidden broker imports (kiteconnect, zerodha, etc.) |
| Threshold gates | Models only exported if Sharpe ≥ 0.5, DD ≤ 25%, Accuracy ≥ 50% |
| Config validation | Fails fast on missing/invalid config fields |
| Versioned models | Every run creates new file — never overwrites previous models |

### Configuration

Edit `backtesting/config/backtest_config.yaml`:

```yaml
symbols:
  - RELIANCE.NS
  - TCS.NS
  - INFY.NS
  - HDFCBANK.NS
  - ICICIBANK.NS
  - WIPRO.NS
  - SBIN.NS
  - BHARTIARTL.NS
  - BAJAJ-AUTO.NS
  - SUNPHARMA.NS
  - TECHM.NS
  - KOTAKBANK.NS
  - ADANIPORTS.NS
  - NESTLEIND.NS

timeframe: 1d

data:
  start_date: "2019-01-01"
  end_date: "2026-01-01"

labeling:
  lookahead_periods: 10
  return_threshold: 0.03
  stop_loss: 0.03
  num_classes: 3

training:
  model_type: xgboost
  num_classes: 3
  parameters:
    max_depth: 6
    learning_rate: 0.05
    n_estimators: 300
    subsample: 0.8
    colsample_bytree: 0.8
    min_child_weight: 3
    gamma: 0.1
    random_state: 42

walk_forward:
  train_window_years: 3
  test_window_months: 6
  step_months: 6

backtest:
  initial_capital: 100000
  position_size_pct: 0.10
  max_positions: 3
  stop_loss_pct: 0.03
  target_pct: 0.15
  slippage_pct: 0.001
  use_atr_sl: true
  atr_sl_multiplier: 1.5
  atr_target_multiplier: 3.0
  cooldown_bars: 3

model_selection:
  primary_metric: sharpe_ratio
  min_sharpe: 0.5
  max_drawdown: 0.25
  min_accuracy: 0.50

output:
  models_dir: models
  reports_dir: reports
  logs_dir: logs
  export_latest: true
  deploy_to_backend: true
```

### Pipeline Flow

```
Yahoo Finance → DuckDB → Features (with NIFTY 50 data) → Labels → Walk-Forward Splits
    ↓
For each window:
  Load existing model → Retrain (3-class XGBoost) → Predict → Simulate trades → Evaluate
    ↓
Select best model (threshold gates) → Export versioned model → Generate reports
```

### Outputs

- `models/model_window_N.pkl` — Trained model per window
- `models/latest_model.pkl` — Best performing model
- `models/latest_model_metadata.json` — Metrics + metadata
- `reports/metrics.json` — Performance metrics
- `reports/trades.csv` — Trade log
- `reports/full_report_TIMESTAMP.json` — All window results
- `reports/health_report_TIMESTAMP.json` — Automated health analysis

### Deploy to Live System

After reviewing backtest results:

```powershell
# Windows
copy backtesting\models\latest_model.pkl backend\services\ai\model.joblib

# Linux/Mac
cp backtesting/models/latest_model.pkl backend/services/ai/model.joblib
```

The live system will use the new model on next restart.

---

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
    │   ├── model.py     # ModelTrainer
    │   ├── adaptive_model.py # AdaptiveModel with strategy detection
    │   ├── analyzer.py  # StockAnalyzer with strategy scores
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

5. **Backtesting NIFTY Correlation Feature NaN**
   - Fixed in latest version: NIFTY 50 data is now fetched and properly aligned
   - Feature uses `^NSEI` symbol from Yahoo Finance

6. **Low Sharpe Ratio in Backtest**
   - Check stop-loss/target ratio (now 1.5x/3.0x ATR multiplier)
   - Verify labeling configuration (3-class recommended)
   - Review model selection thresholds (lowered to Sharpe ≥ 0.5)

### Logs

Backend logs are stored in `backend/logs/app.log`
Backtesting logs are stored in `backtesting/logs/backtest.log`

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
- [x] Walk-Forward Backtesting System
- [x] 3-Class ML Model (BUY/HOLD/SELL)
- [x] Adaptive ATR-Based Labeling
- [x] NIFTY 50 Integration for Relative Strength
- [ ] Telegram notifications
- [ ] Portfolio rebalancing
- [ ] Multi-broker support
- [ ] Alternative ML models (LSTM, Transformer)
- [ ] Paper trading dashboard improvements
