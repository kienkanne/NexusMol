from string import Template
from pathlib import Path

from nexus.md.amber._run_pmemd import _run_pmemd
from nexus.md.md_config import MDConfig

''' Minimization n runs. 
The first run takes the input coordinates.
Each subsequent run takes the output coordinates of the previous run. 
The output coordinates are saved as min{run}.ncrst'''

def minimize(cfg: MDConfig, prmtop: Path, inpcrd: Path) -> Path:
    working_dir = cfg.common.working_dir
    working_dir.mkdir(parents=True, exist_ok=True)

    cut = cfg.common.cut
    n_min_runs = cfg.min.n_min_runs
    ncyc = cfg.min.ncyc
    maxcyc = cfg.min.maxcyc
    restraint = cfg.min.restraint

    with open(Path(__file__).resolve().parents[0] / "templates" / "min_template.txt") as f:
        min_template = f.read()

    last_ncrst = None
    for run in range(1, n_min_runs + 1):
        min_input = Template(min_template).substitute(
            ncyc=ncyc,
            maxcyc=maxcyc,
            cut=cut,
            restraint=restraint[run - 1],
        )

        if run == 1:
            _run_pmemd(min_input, prmtop, inpcrd, working_dir, f"min{run}")
        else:
            ncrst = working_dir / f"min{run - 1}.ncrst"
            _run_pmemd(min_input, prmtop, ncrst, working_dir, f"min{run}")
        last_ncrst = working_dir / f"min{run}.ncrst"

    return last_ncrst