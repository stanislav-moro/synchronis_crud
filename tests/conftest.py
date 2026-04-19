import pytest
import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы импорты работали из папки tests/
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Настройка event loop для асинхронных тестов
@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()