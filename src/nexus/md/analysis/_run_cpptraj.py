from pathlib import Path
from nexus.core.executors.shell import shell
import os


def _run_cpptraj(cpptraj_input: str, output_dir: Path, name: str= "", logger=None):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cwd = os.getcwd()
    try:
        os.chdir(output_dir)

        cpptraj_in = output_dir / f"{name}.in"
        cpptraj_in.write_text(cpptraj_input)

        cpptraj_cmd = [
        "cpptraj",
        "-i",
        str(cpptraj_in),
        ]

        with shell(cpptraj_cmd) as stdout:
            pass
        return stdout

    except Exception as e:
        raise RuntimeError(f"Failed to change working directory to {output_dir}: {e}")
    
    finally:
        os.chdir(cwd)