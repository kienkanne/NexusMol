import subprocess
import os
from nexus.core.trackers.logging_utils import DummyLogger
from nexus.core.trackers.main_tracker import TrackerContext
from contextlib import contextmanager


@contextmanager
def shell(cmd, stdin=None, title=""):
    try:
        cmd = [os.path.expandvars(i) for i in cmd]

        ctx = TrackerContext.get_ctx()
        try:
            logger = ctx.logger if ctx.logger is not None else DummyLogger()
        except:
            logger = DummyLogger()
            
        logger.info(f"Running: {title}; cmd: {' '.join([str(arg) for arg in cmd])}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=stdin
        )
        
        # logger stdout/stderr for debugging
        if result.stdout:
            logger.info(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR: {result.stderr}")

        result.check_returncode()
        yield result.stdout

    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        raise