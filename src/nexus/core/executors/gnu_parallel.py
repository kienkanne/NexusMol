import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from nexus.core.trackers.logging_utils import DummyLogger

def gnu_parallel(n_jobs=1, logger=None, title=None, skip=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            local_logger = logger if logger is not None else DummyLogger()
            local_title = title if title is not None else ""
            
            # 1. Use your safe local scratch location to bypass /tmp lockouts
            scratch_tmp = "/localscratch/kbui/tmp"
            
            # Initialize to None so the finally block can safely inspect it
            joblog_path = None 
            
            try:
                # 2. Crucial: Ensure the custom directory actually exists first!
                os.makedirs(scratch_tmp, exist_ok=True)
                
                cmds = func(*args, **kwargs)
                processed_cmds = []
                for cmd in cmds:
                    expanded = [os.path.expandvars(term) for term in cmd]
                    processed_cmds.append(shlex.join(expanded))
                
                stdin = "\n".join(processed_cmds)
                
                local_logger.info(f"Running: Parallel {local_title} for {len(cmds)} jobs")

                # 3. Create the temp file directly within our verified scratch location
                with tempfile.NamedTemporaryFile(mode="w+", dir=scratch_tmp, delete=False) as tmp_log:
                    joblog_path = tmp_log.name

                parallel_flags = ["parallel", "--tag", "--joblog", joblog_path, "-j", str(n_jobs)]
                if skip:
                    parallel_flags.append("--halt=never")

                # 4. Update environment variables so GNU Parallel's internal shell 
                # also uses our executable scratch folder instead of system /tmp
                env = os.environ.copy()
                env["TMPDIR"] = scratch_tmp

                result = subprocess.run(
                    parallel_flags,
                    capture_output=True,
                    text=True,
                    input=stdin,
                    env=env
                )

                if result.stderr:
                    local_logger.warning(f"STDERR: {result.stderr}")

                if not skip:
                    result.check_returncode()

                # 5. Extract our tagged job outputs cleanly
                outputs = []
                for line in result.stdout.splitlines():
                    if "\t" in line:
                        _, content = line.split("\t", 1)
                        outputs.append(content.strip())
                    else:
                        outputs.append(line.strip())

                # 6. Parse the joblog file to pull the exact success metrics
                total_jobs = len(cmds)
                successful_jobs = 0

                if os.path.exists(joblog_path):
                    log_content = Path(joblog_path).read_text()
                    lines = log_content.strip().splitlines()
                    
                    if len(lines) > 1:
                        # Parse the header line to find exactly where 'Exitval' lives
                        header_parts = lines[0].split("\t")
                        try:
                            exitval_idx = header_parts.index("Exitval")
                        except ValueError:
                            # Fallback to index 6 if the header text match fails
                            exitval_idx = 6

                        for line in lines[1:]:
                            parts = line.split("\t")
                            # Extract using our dynamically verified index
                            if len(parts) > exitval_idx and parts[exitval_idx] == "0":
                                successful_jobs += 1

                local_logger.info(f"Parallel execution completed. Kept {successful_jobs}/{total_jobs} successful jobs.")
                return outputs
            
            except subprocess.CalledProcessError as e:
                local_logger.error(f"Command failed with exit code {e.returncode}")
                raise
            finally:
                # 7. Rigid guard condition to block TypeErrors on cleanup
                if joblog_path is not None and os.path.exists(joblog_path):
                    try:
                        os.unlink(joblog_path)
                    except OSError:
                        pass
            
        return wrapper
    return decorator