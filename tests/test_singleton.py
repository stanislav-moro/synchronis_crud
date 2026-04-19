import pytest
from services.log import Log, LogInstance

def test_singleton_returns_same_instance():
    """Проверяет, что многократные обращения возвращают один объект в памяти"""
    log1 = LogInstance
    log2 = Log()  # Прямой вызов конструктора
    assert log1 is log2, "Singleton нарушен: созданы разные экземпляры"

def test_singleton_has_logging_methods():
    """Проверяет наличие асинхронных методов логирования"""
    assert hasattr(LogInstance, "info"), "Отсутствует метод info"
    assert hasattr(LogInstance, "debug"), "Отсутствует метод debug"
    assert hasattr(LogInstance, "error"), "Отсутствует метод error"
    assert callable(LogInstance.info), "Метод info не является вызываемым"