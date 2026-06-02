import logging
from logging import Logger
import sys
from pathlib import Path


# Global silence level for CLI: 0=default,1=info-muted,2=all-muted
_SILENCE_LEVEL = 0


def set_silence(level: int):
    """Set global silence level (0,1,2)."""
    global _SILENCE_LEVEL
    try:
        lvl = int(level)
    except Exception:
        lvl = 0
    if lvl < 0:
        lvl = 0
    if lvl > 2:
        lvl = 2
    _SILENCE_LEVEL = lvl


def get_silence() -> int:
    return _SILENCE_LEVEL


class _SilenceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # If this record came from the main_tracker, bypass ALL silence rules
        if getattr(record, "is_tracker", False):
            return True

        lvl = _SILENCE_LEVEL
        if lvl == 1:
            return record.levelno != logging.INFO
        if lvl == 2:
            return record.levelno >= logging.ERROR
        return True


class CustomLogger(Logger):
    def __init__(self, path: str, time_verbose: bool = True, silence: int | None = None):
        super().__init__(name="CustomLogger")
        self.path = path
        self.time_verbose = time_verbose
        # allow instance override, otherwise use global
        if silence is not None:
            set_silence(silence)

        self._setup_logger()

    def _setup_logger(self):
        # Creates console + file logger.
        log_file = Path(self.path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        self.setLevel(logging.INFO)

        for handler in self.handlers[:]:
            self.removeHandler(handler)
            handler.close()

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        fh = logging.FileHandler(log_file)
        sh = logging.StreamHandler(sys.stdout)

        if self.time_verbose:
            fh.setFormatter(formatter)
            sh.setFormatter(formatter)

        # Add a silence filter to the logger so that global --silence
        # can mute INFO and lower-priority messages without changing
        # the logger's base level semantics.
        self.addFilter(_SilenceFilter())

        self.addHandler(fh)
        self.addHandler(sh)

    def get_path(self) -> str:
        return self.path


class DummyLogger:
    """Fallback logger that mimics basic logging behavior using standard prints.

    This simple logger respects the global silence level set by `set_silence`.
    """
    def info(self, message: str):
        if get_silence() >= 1:
            return
        print(f"[INFO] {message}")

    def error(self, message: str):
        print(f"[ERROR] {message}")

    def debug(self, message: str):
        if get_silence() >= 2:
            return
        print(f"[DEBUG] {message}")

    def warning(self, message: str):
        if get_silence() >= 2:
            return
        print(f"[WARNING] {message}")