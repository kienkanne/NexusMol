from pathlib import Path
import shutil
from nexus.core.executors.shell import shell

def _get_pmemd_executable() -> str:
    """Returns 'pmemd.cuda' if available, otherwise falls back to 'pmemd'."""
    if shutil.which("pmemd.cuda"):
        return "pmemd.cuda"
    return "pmemd"

def _run_pmemd(mdin_input: str, prmtop: Path, inpcrd: Path, working_dir: Path, stepname: str):
    working_dir = Path(working_dir)

    mdin = working_dir / f"{stepname}.in"
    mdin.write_text(mdin_input)

    out = working_dir / f"{stepname}.out"
    ncrst = working_dir / f"{stepname}.ncrst"
    nc = working_dir / f"{stepname}.nc"
    mdinfo = working_dir / f"{stepname}.info"
    
    # Determine which executable to use
    executable = _get_pmemd_executable()
    
    pmemd_cmd = [
        executable,
        "-AllowSmallBox",
        "-O",
        "-i", str(mdin),
        "-o", str(out),
        "-p", str(prmtop),
        "-c", str(inpcrd),
        "-ref", str(inpcrd),
        "-r", str(ncrst),
        "-x", str(nc),
        "-inf", str(mdinfo)
    ]

    with shell(pmemd_cmd):
        pass

    return True
