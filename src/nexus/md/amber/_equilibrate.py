from string import Template
from pathlib import Path

from nexus.md.amber._run_pmemd import _run_pmemd
from nexus.md.md_config import MDConfig

'''Equilibration n runs.
The first run takes the output coordinates of the heating run.
Each subsequent run takes the output coordinates of the previous run.
The output coordinates are saved as eq{run}.ncrst'''

def equilibrate(mcfg: MDConfig, prmtop: Path, last_heat_ncrst: Path) -> Path:
    working_dir = mcfg.common.working_dir
    working_dir.mkdir(parents=True, exist_ok=True)

    dt = mcfg.common.dt
    temp = mcfg.common.temp
    cut = mcfg.common.cut
    mask = mcfg.common.mask

    restraint = mcfg.eq.restraint
    eq_time = mcfg.eq.eq_time
    n_eq_runs = mcfg.eq.n_eq_runs
    
    nstlim = int((eq_time) / dt)
    ntpr = ntwx = ntwr = int(nstlim // 100) or 1000

    with open(Path(__file__).resolve().parents[0] / "templates" / "eq_template.txt") as f:
        eq_template = f.read()

    last_ncrst = None
    for run in range(1, n_eq_runs + 1):
        eq_input = Template(eq_template).substitute(
            dt=dt,
            temp=temp,
            cut=cut,
            restraint=restraint[run - 1],
            nstlim=nstlim,
            ntpr=ntpr,
            ntwx=ntwx,
            ntwr=ntwr,
            mask=mask,
        )
        if run == 1:
            ncrst = last_heat_ncrst
            _run_pmemd(eq_input, prmtop, ncrst, working_dir, f"eq{run}")
        else:
            ncrst = working_dir / f"eq{run - 1}.ncrst"
            _run_pmemd(eq_input, prmtop, ncrst, working_dir, f"eq{run}")

        last_ncrst = working_dir / f"eq{run}.ncrst"

    return last_ncrst