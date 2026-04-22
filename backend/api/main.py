from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db
from core.config import get_settings
from core.logging import logger
from api.routes import router
from api.routes.trading import set_trading_loop
from api.routes.websocket import router as ws_router, get_manager
from services.broker.zerodha import get_broker
from services.broker.chartink import get_chartink_client
from services.ai.analyzer import StockAnalyzer
from services.trading.loop import TradingLoop


_trading_loop = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _trading_loop

    logger.info("Starting application...")
    init_db()
    logger.info("Database initialized")

    settings = get_settings()

    broker = get_broker()
    if settings.is_live_trading:
        broker.connect()
        logger.info("Connected to Zerodha")
    else:
        logger.info("Running in paper trading mode")

    chartink = get_chartink_client()
    analyzer = StockAnalyzer(broker)

    _trading_loop = TradingLoop(
        broker=broker,
        chartink=chartink,
        analyzer=analyzer,
        interval_seconds=300,
    )
    set_trading_loop(_trading_loop)

    logger.info(f"Trading mode: {settings.trading_mode.upper()}")

    yield

    if _trading_loop:
        _trading_loop.stop()
    logger.info("Shutting down application...")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Algo Swing Trading Agent",
        description="AI-powered swing trading for Indian stock market",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(ws_router)

    @app.get("/")
    async def root():
        return {
            "name": "Algo Swing Trading Agent",
            "version": "1.0.0",
            "status": "running",
            "mode": get_settings().trading_mode,
        }

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


app = create_app()
