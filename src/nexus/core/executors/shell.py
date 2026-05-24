import subprocess
import os
from nexus.core.trackers.logging_utils import DummyLogger

def shell(logger=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                cmd, stdin = func(*args, **kwargs)
                cmd = [os.path.expandvars(i) for i in cmd]

                local_logger = logger if logger is not None else DummyLogger()
                local_logger.info(f"Running: {' '.join([str(arg) for arg in cmd])}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    input=stdin
                )
                
                # logger stdout/stderr for debugging
                if result.stdout:
                    local_logger.debug(f"STDOUT: {result.stdout}")
                if result.stderr:
                    local_logger.warning(f"STDERR: {result.stderr}")

                result.check_returncode()
                return result.stdout

            except subprocess.CalledProcessError as e:
                local_logger.error(f"Command failed with exit code {e.returncode}")
                local_logger.error(f"Error output: {e.stderr}")
                raise

        return wrapper
    return decorator
