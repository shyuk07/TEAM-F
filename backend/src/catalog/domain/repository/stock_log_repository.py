from abc import ABC, abstractmethod

from catalog.domain.stock_log import StockLog


class StockLogRepository(ABC):
    @abstractmethod
    async def add(self, log: StockLog) -> StockLog: ...
