from fastapi import APIRouter
from api.routes import stocks, trading, explanations, regime, trade_explain, trade_intelligence, trade_journal, reflection, portfolio, correlation_analysis, research, drift

router = APIRouter()

router.include_router(stocks.router)
router.include_router(trading.router)
router.include_router(explanations.router)
router.include_router(regime.router)
router.include_router(trade_explain.router)
router.include_router(trade_intelligence.router)
router.include_router(trade_journal.router)
router.include_router(reflection.router)
router.include_router(portfolio.router)
router.include_router(correlation_analysis.router)
router.include_router(research.router)
router.include_router(drift.router)
