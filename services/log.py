# services/log.py
import asyncio
from datetime import datetime
from pathlib import Path


class Log:
    _instance = None
    _lock: asyncio.Lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        if Log._lock is None:
            Log._lock = asyncio.Lock()

        self._log_dir = Path("logs")
        self._log_dir.mkdir(exist_ok=True)
        self._log_file = self._log_dir / "synchronis_log.txt"

        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== Synchronis Log Started: {datetime.now()} ===\n")

    async def write(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        async with self._lock:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

    # Обёртки для удобства
    async def info(self, msg: str):
        await self.write(msg, "INFO")

    async def debug(self, msg: str):
        await self.write(msg, "DEBUG")

    async def warning(self, msg: str):
        await self.write(msg, "WARNING")

    async def error(self, msg: str):
        await self.write(msg, "ERROR")


LogInstance = Log()