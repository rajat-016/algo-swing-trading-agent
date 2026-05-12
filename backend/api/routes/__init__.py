from fastapi import APIRouter
from api.routes import stocks, trading, explanations, regime, trade_explain

router = APIRouter()

router.include_router(stocks.router)
router.include_router(trading.router)
router.include_router(explanations.router)
router.include_router(regime.router)
router.include_router(trade_explain.router)
