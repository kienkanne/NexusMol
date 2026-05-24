from string import Template
from pathlib import Path

from nexus.md.amber._run_pmemd import _run_pmemd
from nexus.md.md_config import MDConfig


'''Heating takes the output coordinates of the last minimization step.
There is only 1 heating step, so the output coordinates are saved as heat.ncrst'''


def heat(mcfg: MDConfig, prmtop: Path, last_min_ncrst: Path):
    working_dir = mcfg.common.working_dir
    working_dir.mkdir(parents=True, exist_ok=True)

    dt = mcfg.common.dt
    cut = mcfg.common.cut
    mask = mcfg.common.mask
    temp = mcfg.common.temp

    mid_temp = mcfg.heat.mid_temp
    time_mid_temp = mcfg.heat.time1
    time_temp = mcfg.heat.time2
    total_time = mcfg.heat.total_time
    restraint = mcfg.heat.restraint

    nstlim = int((total_time) / dt)
    ntpr = ntwx = ntwr = int(nstlim // 100) or 10000

    with open(Path(__file__).resolve().parents[0] / "templates" / "heat_template.txt") as f:
        heat_template = f.read()

    heat_input = Template(heat_template).substitute(
        dt=dt,
        mid_temp=mid_temp,
        temp=temp,
        cut=cut,
        restraint=restraint,
        nstlim=nstlim,
        ntpr=ntpr,
        ntwx=ntwx,
        ntwr=ntwr,
        istep_mid_temp=int((time_mid_temp) / dt),
        istep_mid_temp_plus1=int((time_mid_temp) / dt) + 1,
        istep_temp=int((time_temp) / dt),
        mask=mask,
    )

    _run_pmemd(heat_input, prmtop, last_min_ncrst, working_dir, "heat")

    return working_dir / "heat.ncrst"