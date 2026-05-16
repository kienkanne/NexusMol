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

                n_jobs = str(cfg.common.n_jobs)

                local_title = title if title is not None else ""
                logger = cfg.common.logger
                logger.info(f"Running: Parallel {local_title} for {n_jobs} jobs")

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


### EXPERIMENTAL FOP RESUME PARALLEL STATE

import json
import os
from typing import List, Tuple

def resume_parallel_state(
    task_tuple: Tuple[List[str], List[str]], 
    state_filepath: str = "parallel_state.json"
) -> Tuple[List[str], List[str]]:

    commands, names = task_tuple
    
    # 1. Load existing state or initialize a new one
    if os.path.exists(state_filepath):
        with open(state_filepath, 'r') as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                # Handle corrupted or empty JSON safely
                state = {}
    else:
        state = {}

    # 2. Update state with any *new* tasks found in the input tuple
    state_changed = False
    for name in names:
        if name not in state:
            state[name] = "pending"  # Initial status for new tasks
            state_changed = True

    if state_changed:
        with open(state_filepath, 'w') as f:
            json.dump(state, f, indent=4)

    # 3. Filter the tuple, keeping only tasks that are NOT completed
    resume_commands = []
    resume_names = []

    for cmd, name in zip(commands, names):
        if state.get(name) != "completed":
            resume_commands.append(cmd)
            resume_names.append(name)

    return resume_commands, resume_names