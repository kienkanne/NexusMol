import os
from pathlib import Path

def base(cfg, title=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            original_cwd = os.getcwd()

            try:
                Path(cfg.common.working_dir).parent.mkdir(parents=True, exist_ok=True)
                os.chdir(cfg.common.working_dir)
                
                logger = cfg.common.logger
                if not title:
                    logger.info(f"Running: {title}")

                return func(*args, **kwargs)
            finally:
                # This runs even if the function crashes
                os.chdir(original_cwd)

        return wrapper
    return decorator
