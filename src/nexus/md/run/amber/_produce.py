from string import Template
from pathlib import Path

from nexus.core.trackers.main_tracker import main_tracker, TrackerContext
from nexus.md.run.amber._run_pmemd import _run_pmemd
from nexus.md.run.md_config import MDConfig


@main_tracker("Production")
def produce(cfg: MDConfig, prmtop: Path, last_eq_ncrst: Path) -> None:
    '''Randomization takes the output coordinates of the last equilibration step and resets the velocities.
    The output coordinates are saved as rand{seed}.ncrst'''

    '''Production run takes the output coordinates of the last equilibration step and runs for a long time. 
    The output coordinates are saved as prod{seed}.ncrst'''

    scratch_dir = cfg._global.path.scratch_dir

    dt = cfg.common.dt
    temp = cfg.common.temp
    cut = cfg.common.cut
    mask = cfg.common.mask

    num_seeds = cfg.prod.num_seeds
    rand_time = cfg.prod.rand_time
    prod_time = cfg.prod.prod_time
    prod_freq = cfg.prod.prod_freq

    nstlim = int((rand_time) / dt)
    ntpr = ntwx = ntwr = int(nstlim // 1000) or 10000

    with open(Path(__file__).resolve().parents[0] / "templates" / "rand_template.txt") as f:
        rand_template = f.read()

    with open(Path(__file__).resolve().parents[0] / "templates" / "prod_template.txt") as f:
        prod_template = f.read()

    rand_input = Template(rand_template).substitute(
        dt=dt,
        temp=temp,
        cut=cut,
        nstlim=nstlim,
        ntpr=ntpr,
        ntwx=ntwx,
        ntwr=ntwr,
        mask=mask,
    )

    nstlim = int((prod_time) / dt)
    ntpr = ntwx = ntwr = int((prod_freq / dt)) or 10000

    prod_input = Template(prod_template).substitute(
        dt=dt,
        temp=temp,
        cut=cut,
        nstlim=nstlim,
        ntpr=ntpr,
        ntwx=ntwx,
        ntwr=ntwr,
        mask=mask,
    )

    outputs = []
    for i in range(1, num_seeds + 1):
        ncrst = last_eq_ncrst
        _run_pmemd(rand_input, prmtop, ncrst, scratch_dir, f"seed{i}")

        ncrst = scratch_dir / f"seed{i}.ncrst"
        _run_pmemd(prod_input, prmtop, ncrst, scratch_dir, f"prod{i}")

        prod_nc = Path(scratch_dir) / f"prod{i}.nc"
        prod_ncrst = Path(scratch_dir) / f"prod{i}.ncrst"
        prod_out = Path(scratch_dir) / f"prod{i}.out"

        outputs.append((prod_nc, prod_ncrst, prod_out))

        logger = TrackerContext.get_ctx().logger
        logger.info(f"Finished full run with seed {i}")

    return outputs
