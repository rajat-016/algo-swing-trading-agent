from fastapi import APIRouter

from fastapi import APIRouter
from api.routes import stocks, trading

router = APIRouter()

router.include_router(stocks.router)
router.include_router(trading.router)
