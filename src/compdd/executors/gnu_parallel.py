import os
from pathlib import Path
import subprocess
import re


def gnu_parallel(cfg, title=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            original_cwd = os.getcwd()
            try:
                Path(cfg.common.working_dir).mkdir(parents=True, exist_ok=True)
                os.chdir(cfg.common.working_dir)

                cmds = func(*args, **kwargs)
                cmds = [[os.path.expandvars(term) for term in cmd] for cmd in cmds]
                stdin = "\n".join([" ".join(cmd) for cmd in cmds])
                
                wrapped_cmds = []

                for i, cmd in enumerate(cmds):
                    joined = " ".join(cmd)

                    wrapped = (f'echo "__START__{i}__"; '
                               f'{joined}; '
                               f'echo "__END__{i}__"')

                    wrapped_cmds.append(wrapped)

                stdin = "\n".join(wrapped_cmds)
                
                total_jobs = len(cmds)
                local_title = title if title is not None else ""
                logger = cfg.common.logger
                logger.info(f"Running: Parallel {local_title} for {total_jobs} jobs")

                n_jobs = str(cfg.common.n_jobs)

                result = subprocess.run(
                    ["parallel", "-k", "-j", n_jobs],
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

                pattern = r"__START__(\d+)__(.*?)__END__\1__"
                matches = re.findall(pattern, result.stdout, re.DOTALL)
                outputs = [content.strip() for _, content in matches]
              
                return outputs
            
            except subprocess.CalledProcessError as e:
                logger.error(f"Command failed with exit code {e.returncode}")
                logger.error(f"Error output: {e.stderr}")
                raise

            finally:
                # This runs even if the function crashes
                os.chdir(original_cwd)
            
        return wrapper
    return decorator
