import pytest
from datetime import datetime
from services.strategies import SortByNameStrategy, SortByDateStrategy

# Заглушка, имитирующая модель PriceList
class MockPriceList:
    def __init__(self, name, uploaded_at):
        self.name = name
        self.uploaded_at = uploaded_at

@pytest.mark.asyncio
async def test_sort_by_name_ascending():
    """Стратегия сортировки по имени должна возвращать список А-Я"""
    items = [
        MockPriceList("Zebra", datetime.now()),
        MockPriceList("Apple", datetime.now()),
        MockPriceList("Banana", datetime.now())
    ]
    strategy = SortByNameStrategy()
    result = await strategy.sort(items)
    names = [item.name for item in result]
    assert names == ["Apple", "Banana", "Zebra"], "Сортировка по имени нарушена"

@pytest.mark.asyncio
async def test_sort_by_date_descending():
    """Стратегия сортировки по дате должна возвращать список от новых к старым"""
    now = datetime.now()
    items = [
        MockPriceList("A", now.replace(day=1)),
        MockPriceList("B", now.replace(day=15)),
        MockPriceList("C", now.replace(day=10))
    ]
    strategy = SortByDateStrategy()
    result = await strategy.sort(items)
    dates = [item.uploaded_at for item in result]
    assert dates == sorted(dates, reverse=True), "Сортировка по дате нарушена"