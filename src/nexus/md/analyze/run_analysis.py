import os
from string import Template
from pathlib import Path
import shutil

from nexus.md.analyze.analyze_config import AnalyzeConfig
from nexus.md.analyze._run_cpptraj import _run_cpptraj

def run_analysis(cfg: AnalyzeConfig):
    AMBERHOME = os.environ.get("AMBERHOME")
    if not AMBERHOME:
        raise RuntimeError("AMBERHOME environment variable not set")

    with open(Path(__file__).resolve().parents[0] / "analysis_template.txt") as f:
        analysis_template = f.read()

    absolute_prmtop = Path(cfg.common.prmtop).resolve()
    absolute_trajin = Path(cfg.common.trajin).resolve()

    name = cfg.common.job_name

    cpptraj_input = Template(analysis_template).substitute(prmtop=absolute_prmtop, 
                                                           trajin=absolute_trajin, 
                                                           mask=cfg.common.mask, 
                                                           name=name)

    output_dir = cfg.common.output_dir

    _run_cpptraj(cpptraj_input, output_dir=output_dir, name=name)

    shutil.copy2((Path(__file__).resolve().parents[0] / "visual_template.ipynb"), output_dir / f"Visual_{name}.ipynb")
