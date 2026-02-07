import asyncio
from datetime import datetime, timedelta

import yfinance as yf
from loguru import logger


class MarketDataService:
    """Fetch market index data via yfinance with caching."""

    INDICES = [
        {"symbol": "^IXIC", "name": "Nasdaq"},
        {"symbol": "^GSPC", "name": "S&P 500"},
        {"symbol": "^KS11", "name": "KOSPI"},
        {"symbol": "^KQ11", "name": "KOSDAQ"},
        {"symbol": "USDKRW=X", "name": "USD/KRW"},
    ]

    CACHE_TTL = timedelta(minutes=5)

    def __init__(self):
        self._cache: dict | None = None
        self._cache_time: datetime | None = None

    async def get_indices(self) -> dict:
        """Get market indices with 5-min caching."""
        now = datetime.utcnow()

        if self._cache and self._cache_time and (now - self._cache_time) < self.CACHE_TTL:
            return self._cache

        data = await asyncio.to_thread(self._fetch_indices)
        self._cache = data
        self._cache_time = now
        return data

    def _fetch_indices(self) -> dict:
        """Fetch index data from yfinance (runs in thread)."""
        indices = []

        for idx in self.INDICES:
            try:
                ticker = yf.Ticker(idx["symbol"])
                info = ticker.fast_info

                price = info.last_price
                prev_close = info.previous_close

                if price and prev_close:
                    change = price - prev_close
                    change_pct = (change / prev_close) * 100
                else:
                    change = 0.0
                    change_pct = 0.0

                indices.append({
                    "symbol": idx["symbol"],
                    "name": idx["name"],
                    "price": round(price, 2) if price else 0.0,
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                })
            except Exception as e:
                logger.warning(f"Failed to fetch {idx['symbol']}: {e}")
                indices.append({
                    "symbol": idx["symbol"],
                    "name": idx["name"],
                    "price": 0.0,
                    "change": 0.0,
                    "change_pct": 0.0,
                })

        return {
            "indices": indices,
            "updated_at": datetime.utcnow().isoformat(),
        }


# Singleton
market_data_service = MarketDataService()
