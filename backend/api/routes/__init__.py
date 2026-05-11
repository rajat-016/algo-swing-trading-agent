from fastapi import APIRouter
from api.routes import stocks, trading, explanations

router = APIRouter()

router.include_router(stocks.router)
router.include_router(trading.router)
router.include_router(explanations.router)
