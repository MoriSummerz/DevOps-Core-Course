import logging
import threading
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from config import settings

logger = logging.getLogger(__name__)


class VisitsCounter:
    def __init__(self, file_path: Path):
        self._file_path = file_path
        self._lock = threading.Lock()
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> int:
        try:
            return int(self._file_path.read_text().strip() or "0")
        except FileNotFoundError:
            return 0
        except ValueError:
            logger.warning("Invalid visits file content, resetting to 0")
            return 0

    def _write(self, value: int) -> None:
        tmp = self._file_path.with_suffix(".tmp")
        tmp.write_text(str(value))
        tmp.replace(self._file_path)

    def get(self) -> int:
        with self._lock:
            return self._read()

    def increment(self) -> int:
        with self._lock:
            value = self._read() + 1
            self._write(value)
            return value


_counter: VisitsCounter | None = None


def get_visits_counter() -> VisitsCounter:
    global _counter
    if _counter is None:
        _counter = VisitsCounter(Path(settings.visits_file))
    return _counter


VisitsCounterDep = Annotated[VisitsCounter, Depends(get_visits_counter)]
