import os
from string import Template
from pathlib import Path
import shutil

from nexus.md.fbe._run_mmpbsa import _run_mmpbsa

def fbe(prmtop: Path, trajin: Path, mask: str, name: str, output_dir: Path, 
                 startframe: int = 1, endframe: int = 9999999, interval: int = 10, n_cores: int=1):
    AMBERHOME = os.environ.get("AMBERHOME")
    if not AMBERHOME:
        raise RuntimeError("AMBERHOME environment variable not set")

    with open(Path(__file__).resolve().parents[0] / "mmpbsa_template.txt") as f:
        mmpbsa_template = f.read()

    absolute_prmtop = Path(prmtop).resolve()
    absolute_trajin = Path(trajin).resolve()

    output_dir = output_dir / name

    mmgbsa_input = Template(mmpbsa_template).substitute(startframe=startframe, endframe=endframe, interval=interval)

    _run_mmpbsa(mmgbsa_input, 
                prmtop=absolute_prmtop, 
                trajin=absolute_trajin, 
                output_dir=output_dir, 
                mask=mask, 
                name=name,
                n_cores=n_cores)

    shutil.copy2((Path(__file__).resolve().parents[0] / "visual_temnplate.ipynb"), output_dir / f"Visual_{name}.ipynb")
