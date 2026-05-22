import logging
import sys
from pathlib import Path

def setup_logger(log_path: str, level=logging.INFO, time_verbose=True):

    #Creates console + file logger.
    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("docking")
    logger.setLevel(level)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    fh = logging.FileHandler(log_file)
    sh = logging.StreamHandler(sys.stdout)
    
    if time_verbose:
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger
