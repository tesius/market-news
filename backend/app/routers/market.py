from fastapi import APIRouter

from app.services.market_data import market_data_service

router = APIRouter(prefix="/api/market-data", tags=["market"])


@router.get("")
async def get_market_data():
    """Get current market index data."""
    return await market_data_service.get_indices()
