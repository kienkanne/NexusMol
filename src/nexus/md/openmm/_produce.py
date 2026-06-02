from nexus.md.md_config import MDConfig
from openmm.app import Simulation
from openmm.unit import kelvin
from nexus.md.openmm._setup import set_positional_restraint_strength
from nexus.md.openmm._reporter import add_reporters

from nexus.core.trackers.main_tracker import main_tracker, PipelineContext

@main_tracker("Production")
def produce(mcfg: MDConfig, simulation: Simulation):
    working_dir = mcfg.common.working_dir
    temp = mcfg.common.temp
    dt = mcfg.common.dt

    num_seeds = mcfg.prod.num_seeds
    rand_time = mcfg.prod.rand_time
    prod_time = mcfg.prod.prod_time
    prod_freq = mcfg.prod.prod_freq

    set_positional_restraint_strength(simulation, 0)

    # Reset all to provide a clean equilibrated STATE
    # Force & velocities are saved just as metadata padding
    # They are going to be overwritten with setVelocitiesToTemperature(temp)
    equilibrated_state = simulation.context.getState(
        getPositions=True, getEnergy=True, enforcePeriodicBox=True, getForces=True, getVelocities=True
    )

    outputs = []
    for i in range(1, num_seeds + 1):
        # Load in the shared saved equilibrated state
        simulation.context.setState(equilibrated_state)

        # Randomize velocities with seed i
        simulation.reporters.clear()
        simulation.context.setVelocitiesToTemperature(temp * kelvin, i)
        simulation.step(int(rand_time / dt))

        simulation.context.setStepCount(0)
        simulation.context.setTime(0.0)
        simulation, outputs_per_seed = add_reporters(simulation, f"prod{i}", working_dir, int(prod_freq / dt), int(prod_time / dt))
        simulation.step(int(prod_time / dt))
        
        outputs.append(outputs_per_seed)

        logger = PipelineContext.get_ctx().logger
        logger.info(f"Finished full run with seed {i}")

    # outputs contain (traj, chk, log)
    # corresponds to amber: (nc, ncrst, out)
    return outputs