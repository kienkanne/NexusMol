from string import Template
from pathlib import Path

from nexus.md.amber._run_pmemd import _run_pmemd
from nexus.md.md_config import MDConfig

'''Randomization takes the output coordinates of the last equilibration step and resets the velocities.
The output coordinates are saved as rand{seed}.ncrst'''

'''Production run takes the output coordinates of the last equilibration step and runs for a long time. 
The output coordinates are saved as prod{seed}.ncrst'''


def produce(mcfg: MDConfig, prmtop: Path, last_eq_ncrst: Path) -> None:
    working_dir = mcfg.common.working_dir
    working_dir.mkdir(parents=True, exist_ok=True)

    dt = mcfg.common.dt
    temp = mcfg.common.temp
    cut = mcfg.common.cut
    mask = mcfg.common.mask

    num_seeds = mcfg.prod.num_seeds
    rand_time = mcfg.prod.rand_time
    prod_time = mcfg.prod.prod_time
    prod_freq = mcfg.prod.prod_freq

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
    ntpr = ntwx = ntwr = int(nstlim // prod_freq) or 10000

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

    for i in range(1, num_seeds + 1):
        ncrst = last_eq_ncrst
        _run_pmemd(rand_input, prmtop, ncrst, working_dir, f"seed{i}")

        ncrst = working_dir / f"seed{i}.ncrst"
        _run_pmemd(prod_input, prmtop, ncrst, working_dir, f"prod{i}")

        print(f"Finished full run with seed {i}")