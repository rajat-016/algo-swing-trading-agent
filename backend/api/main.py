from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.database import init_db
from core.config import get_settings
from core.logging import logger
from core.exceptions import (
    TradingSystemError, ZerodhaError, IPRestrictionError, 
    AuthenticationError, RateLimitError, OrderError, 
    InsufficientFundsError, ModelError, DatabaseError, ValidationError
)
from api.routes import router
from api.routes.trading import set_trading_loop
from api.routes.monitoring import router as monitoring_router
from api.routes.stress_test import router as stress_router
from api.routes.websocket import router as ws_router, get_manager
from services.broker.kite import get_broker
from services.broker.chartink import get_chartink_client
from services.trading.loop import TradingLoop


_trading_loop = None


def _start_loop_sync(loop_instance):
    import asyncio
    from threading import Thread
    loop = asyncio.new_event_loop()

    def run():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(loop_instance.start())

    t = Thread(target=run, daemon=True)
    t.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _trading_loop

    logger.info("Starting application...")
    init_db()

    settings = get_settings()

    broker = get_broker()

    if settings.is_live_trading:
        broker.connect()
        logger.info("Connected to Zerodha")
    else:
        logger.info("Running in paper trading mode")

    chartink = get_chartink_client()

    _trading_loop = TradingLoop(
        broker=broker,
        chartink=chartink,
        interval_seconds=settings.cycle_interval_seconds,
    )
    set_trading_loop(_trading_loop)

    logger.info(f"Trading mode: {settings.trading_mode.upper()}")

    if settings.auto_start_trading:
        try:
            logger.info("Auto-starting trading loop in background...")
            _start_loop_sync(_trading_loop)
        except Exception as e:
            logger.error(f"Auto-start failed: {e}")

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

    # Global exception handler
    @app.exception_handler(TradingSystemError)
    async def trading_system_error_handler(request: Request, exc: TradingSystemError):
        logger.error(f"Trading system error: {exc.message} | Details: {exc.details}")
        return JSONResponse(
            status_code=500,
            content={
                "error": type(exc).__name__,
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(IPRestrictionError)
    async def ip_restriction_handler(request: Request, exc: IPRestrictionError):
        logger.critical(f"IP Restriction: {exc.message}")
        return JSONResponse(
            status_code=403,
            content={
                "error": "IPRestrictionError",
                "message": "IP not allowed. Please add your IP to Zerodha developer console.",
                "ip_address": exc.details.get("ip_address", "unknown")
            }
        )
    
    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        logger.error(f"Authentication error: {exc.message}")
        return JSONResponse(
            status_code=401,
            content={
                "error": "AuthenticationError",
                "message": "Authentication failed. Please check your API credentials."
            }
        )
    
    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request: Request, exc: RateLimitError):
        logger.error(f"Rate limit: {exc.message}")
        retry_after = exc.details.get("retry_after", 60)
        return JSONResponse(
            status_code=429,
            content={
                "error": "RateLimitError",
                "message": f"Rate limit exceeded. Retry after {retry_after}s"
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    @app.exception_handler(OrderError)
    async def order_error_handler(request: Request, exc: OrderError):
        logger.error(f"Order error: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "OrderError",
                "message": exc.message,
                "order_id": exc.details.get("order_id"),
                "rejection_reason": exc.details.get("rejection_reason")
            }
        )
    
    @app.exception_handler(InsufficientFundsError)
    async def insufficient_funds_handler(request: Request, exc: InsufficientFundsError):
        logger.error(f"Insufficient funds: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "InsufficientFundsError",
                "message": "Insufficient funds to place order"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": type(exc).__name__,
                "message": "An internal error occurred"
            }
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(monitoring_router)
    app.include_router(stress_router)
    app.include_router(ws_router)

    @app.get("/")
    async def root():
        settings = get_settings()
        return {
            "name": "Algo Swing Trading Agent",
            "version": "1.0.0",
            "status": "running",
            "mode": settings.trading_mode,
        }

    @app.get("/health")
    async def health():
        """Health check endpoint with detailed status."""
        settings = get_settings()
        status = {
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "mode": settings.trading_mode,
            "broker_connected": False
        }
        
        try:
            from services.broker.kite import get_broker
            broker = get_broker()
            status["broker_connected"] = broker.is_connected()
        except Exception as e:
            status["status"] = "degraded"
            status["broker_error"] = str(e)
        
        return status

    return app


app = create_app()
