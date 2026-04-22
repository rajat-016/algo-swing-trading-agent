# Quick Start Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Docker (optional)

## Quick Start

### Run Everything with One Command

```powershell
.\run.ps1
```

This will:
1. Start Docker services (if available)
2. Create virtual environment
3. Install dependencies
4. Start the API server

## Available Options

| Command | Description |
|---------|-------------|
| `.\run.ps1` | Backend only (paper trading) |
| `.\run.ps1 -Mode live` | Backend with live trading |
| `.\run.ps1 -Full` | Backend + Frontend |
| `.\run.ps1 -Full -Mode live` | Full stack + live trading |
| `.\run.ps1 -NoDocker` | Run without Docker |

## Access Points

- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Configuration

1. Edit `backend/.env` with your settings
2. At minimum, configure:
   - `TRADING_MODE=paper` (start with paper)
   - `CHARTINK_URL=your-screener-url` (optional)
   - Zerodha credentials (for live trading)

## Trading Modes

### Paper Trading (Default)
- Safe testing mode
- No real money
- Default capital: ₹100,000
- Edit `.env`: `TRADING_MODE=paper`

### Live Trading
- Real money at risk
- Requires Zerodha credentials
- Edit `.env`: `TRADING_MODE=live`

## Switch Modes via API

```bash
curl -X POST http://localhost:8000/trading/mode -H "Content-Type: application/json" -d '{"mode": "live"}'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Change API_PORT in .env |
| Module not found | Run `pip install -r requirements.txt` |
| CORS error | Restart backend |
| Database error | Delete trading.db and restart |

## Next Steps

1. Read full README.md for details
2. Configure ChartInk screener URL
3. Test with paper trading
4. Switch to live when ready
