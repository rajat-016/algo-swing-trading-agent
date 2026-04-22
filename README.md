# Algo Swing Trading Agent

AI-powered swing trading agent for the Indian stock market using AI/ML intelligence.

## Overview

This project automates stock trading in the Indian market using:
- **Backend**: FastAPI (Python)
- **Frontend**: React.js
- **Database**: SQLite
- **Broker**: Zerodha Kite API
- **Stock Screening**: ChartInk
- **AI/ML**: Machine learning for stock analysis and entry/exit decisions

## Features

- **AI-Powered Trading**: Uses ML models to analyze stocks and generate entry signals
- **10% Target**: Designed to generate 10%+ returns per stock
- **Paper Trading**: Test strategies without real money
- **Live Trading**: Switch to live trading when ready
- **Risk Management**: Configurable stop loss and position sizing
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
# Trading Parameters
TARGET_PROFIT_PCT=10.0
STOP_LOSS_PCT=3.0
MAX_POSITIONS=10
RISK_PER_TRADE=1.0
MIN_CONFIDENCE=70.0

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

## AI/ML Strategy

The AI engine uses:

1. **Feature Engineering**: Technical indicators
   - Moving averages (SMA, EMA)
   - RSI, MACD, Bollinger Bands
   - Volume ratios
   - Price momentum

2. **ML Model**: Gradient Boosting Classifier
   - Trained to predict 10%+ returns
   - Uses 60-day historical data
   - Confidence threshold: 70%

3. **Entry Criteria**:
   - ML confidence > 70%
   - Momentum score > 0.6
   - Risk-reward ratio > 2.5:1
   - Target: 10%, Stop Loss: 3%

4. **Position Sizing**:
   - Risk: 1% of capital per trade
   - Max positions: 10

## Database Schema

### Stocks Table

| Column | Type | Description |
|--------|------|-------------|
| symbol | String | Stock symbol (unique) |
| status | Enum | PENDING, ENTERED, EXITED |
| entry_price | Float | Entry price |
| target_price | Float | Target price |
| stop_loss | Float | Stop loss price |
| entry_quantity | Integer | Number of shares |
| pnl | Float | Profit/Loss |
| pnl_percentage | Float | P&L percentage |
| entry_reason | String | AI reason for entry |
| ai_confidence | Float | ML confidence score |
| entry_date | DateTime | Entry timestamp |
| exit_date | DateTime | Exit timestamp |
| exit_reason | Enum | TARGET, SL, MANUAL |

## Development

### Project Structure (Backend)

```
backend/
├── api/
│   ├── main.py           # FastAPI app
│   └── routes/           # API endpoints
│       ├── stocks.py
│       └── trading.py
├── core/
│   ├── config.py         # Settings
│   ├── database.py       # DB connection
│   ├── enums.py         # Enumerations
│   └── logging.py       # Logging config
├── models/
│   └── stock.py         # Stock model
└── services/
    ├── broker/           # Broker integrations
    │   ├── zerodha.py
    │   └── chartink.py
    ├── ai/              # AI/ML
    │   ├── features.py
    │   ├── model.py
    │   └── analyzer.py
    └── trading/
        └── loop.py      # Trading loop
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

- [ ] Add more ML models
- [ ] Backtesting module
- [ ] Telegram notifications
- [ ] Portfolio rebalancing
- [ ] Multi-broker support
