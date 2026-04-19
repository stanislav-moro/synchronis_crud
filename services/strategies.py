# services/strategies.py
from abc import ABC, abstractmethod
from models.price_list import PriceList
from typing import List
from services.log import LogInstance


class ISortingStrategy(ABC):
    @abstractmethod
    async def sort(self, items: List[PriceList]) -> List[PriceList]:
        pass


class SortByNameStrategy(ISortingStrategy):
    async def sort(self, items: List[PriceList]) -> List[PriceList]:
        await LogInstance.info("[Strategy] Применена сортировка: по имени (А-Я)")
        return sorted(items, key=lambda x: (x.name or "").lower())


class SortByDateStrategy(ISortingStrategy):
    async def sort(self, items: List[PriceList]) -> List[PriceList]:
        await LogInstance.info("[Strategy] Применена сортировка: по дате (новые сначала)")
        return sorted(items, key=lambda x: x.uploaded_at, reverse=True)