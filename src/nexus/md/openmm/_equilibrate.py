from nexus.md.md_config import MDConfig
from openmm import MonteCarloBarostat
from openmm.app import Simulation
from openmm.unit import kelvin, atmosphere, picosecond
from nexus.md.openmm._setup import set_positional_restraint_strength
from nexus.md.openmm._reporter import add_reporters
from nexus.core.trackers.main_tracker import main_tracker


@main_tracker("Equilibration")
def equilibrate(mcfg: MDConfig, simulation: Simulation):
    working_dir = mcfg.common.working_dir
    dt = mcfg.common.dt
    
    n_eq_runs = mcfg.eq.n_eq_runs
    eq_time = mcfg.eq.eq_time
    restraints = mcfg.eq.restraints

    # NPT equilibration is done in the heating step
    # TODO: Pressure and barostat_interval are hardcoded for now
    simulation = add_barostat(simulation, simulation.system, temp=mcfg.common.temp * kelvin)

    # Set gamma to 1 ps^-1 for equilibration and production
    simulation.integrator.setFriction(1.0 / picosecond)

    # Reset repoters and clock
    simulation.reporters.clear()
    simulation.context.setStepCount(0)
    simulation.context.setTime(0.0)
    
    # Ignore equilibration outputs for now
    simulation, e_outputs = add_reporters(simulation, "eq", working_dir, 10000, int(eq_time * n_eq_runs / dt))

    for run in range(n_eq_runs):
        set_positional_restraint_strength(simulation, restraints[run])
        simulation.step(int(eq_time / dt))

    return simulation


def add_barostat(simulation, system, pressure=1 * atmosphere, temp=300 * kelvin, barostat_interval=25):
    """Add pressure coupling after heating and reinitialize while preserving state."""

    system.addForce(
        MonteCarloBarostat(
            pressure,
            temp,
            barostat_interval,
        )
    )
    simulation.context.reinitialize(preserveState=True)

    return simulation