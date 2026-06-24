from nexus.core.executors.shell import shell
import os

from nexus.md.analyze.analyze_config import AnalyzeConfig

# Change to run_cpptraj(), takes in cfg: AnalyzeConfig and cpptraj_input
def run_cpptraj(cfg: AnalyzeConfig, cpptraj_input: str, outputs: dict):
    scratch_dir = cfg._global.path.scratch_dir

    cwd = os.getcwd()
    try:
        os.chdir(scratch_dir)

        cpptraj_in = scratch_dir / f"analysis_{cfg.common.job_name}.in"
        cpptraj_in.write_text(cpptraj_input)

        cpptraj_cmd = [
        "cpptraj",
        "-i",
        str(cpptraj_in),
        ]

        with shell(cpptraj_cmd):
            pass

    except Exception as e:
        raise RuntimeError(f"cpptraj crashed at {scratch_dir}: {e}")
    
    finally:
        os.chdir(cwd)

    outputs = {k: scratch_dir / v for k, v in outputs.items()}

    return outputs