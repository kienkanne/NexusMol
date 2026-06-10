from nexus.md.run.md_config import MDConfig
from openmm.app import Simulation
from openmm.unit import kelvin
from nexus.md.run.openmm._setup import set_positional_restraint_strength

from nexus.core.trackers.main_tracker import main_tracker, TrackerContext

@main_tracker("Minimization")
def minimize(cfg: MDConfig, simulation: Simulation):
    logger = TrackerContext.get_ctx().logger

    n_min_runs = cfg.min.n_min_runs
    maxcyc = cfg.min.maxcyc
    restraints = cfg.min.restraints

    state = simulation.context.getState(getEnergy=True)
    logger.info(f"Initial PE: {state.getPotentialEnergy()}")

    for run in range(n_min_runs):
        set_positional_restraint_strength(simulation, restraints[run])
        simulation.minimizeEnergy(maxIterations=maxcyc)

    state = simulation.context.getState(getEnergy=True)
    logger.info(f"Final PE: {state.getPotentialEnergy()}")

    return simulation