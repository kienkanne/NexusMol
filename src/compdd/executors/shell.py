import subprocess
import os
from pathlib import Path

def shell(cfg):
    def decorator(func):
        def wrapper(*args, **kwargs):
            original_cwd = os.getcwd()
            try:
                Path(cfg.common.working_dir).mkdir(parents=True, exist_ok=True)
                os.chdir(cfg.common.working_dir)

                cmd, stdin = func(*args, **kwargs)
                cmd = [os.path.expandvars(i) for i in cmd]
                logger = cfg.common.logger
                logger.info(f"Running: {' '.join([str(arg) for arg in cmd])}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    input=stdin
                )
                
                # logger stdout/stderr for debugging
                if result.stdout:
                    logger.debug(f"STDOUT: {result.stdout}")
                if result.stderr:
                    logger.warning(f"STDERR: {result.stderr}")

                result.check_returncode()
                return result.stdout

            except subprocess.CalledProcessError as e:
                logger.error(f"Command failed with exit code {e.returncode}")
                logger.error(f"Error output: {e.stderr}")
                raise

            finally:
                # This runs even if the function crashes
                os.chdir(original_cwd)

        return wrapper
    return decorator

@shell
def ngu():
    return (['ls', "-la"], None)