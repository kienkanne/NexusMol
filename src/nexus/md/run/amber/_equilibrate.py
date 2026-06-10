from string import Template
from pathlib import Path

from nexus.core.trackers.main_tracker import main_tracker
from nexus.md.run.amber._run_pmemd import _run_pmemd
from nexus.md.run.md_config import MDConfig


@main_tracker("Equilibration")
def equilibrate(cfg: MDConfig, prmtop: Path, last_heat_ncrst: Path) -> Path:
    '''Equilibration n runs.
    The first run takes the output coordinates of the heating run.
    Each subsequent run takes the output coordinates of the previous run.
    The output coordinates are saved as eq{run}.ncrst'''

    scratch_dir = cfg._global.path.scratch_dir

    dt = cfg.common.dt
    temp = cfg.common.temp
    cut = cfg.common.cut
    mask = cfg.common.mask

    restraints = cfg.eq.restraints
    eq_time = cfg.eq.eq_time
    n_eq_runs = cfg.eq.n_eq_runs

    nstlim = int((eq_time) / dt)
    ntpr = ntwx = ntwr = int(nstlim // 100) or 1000

    with open(Path(__file__).resolve().parents[0] / "templates" / "eq_template.txt") as f:
        eq_template = f.read()

    last_eq_ncrst = None
    for run in range(1, n_eq_runs + 1):
        eq_input = Template(eq_template).substitute(
            dt=dt,
            temp=temp,
            cut=cut,
            restraint=restraints[run - 1],
            nstlim=nstlim,
            ntpr=ntpr,
            ntwx=ntwx,
            ntwr=ntwr,
            mask=mask,
        )
        if run == 1:
            ncrst = last_heat_ncrst
            _run_pmemd(eq_input, prmtop, ncrst, scratch_dir, f"eq{run}")
        else:
            ncrst = scratch_dir / f"eq{run - 1}.ncrst"
            _run_pmemd(eq_input, prmtop, ncrst, scratch_dir, f"eq{run}")

        last_eq_ncrst = scratch_dir / f"eq{run}.ncrst"

    return last_eq_ncrst
