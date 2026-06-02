from nexus.md.md_config import MDConfig
from openmm.app import Simulation
from openmm.unit import kelvin
from nexus.md.openmm._setup import set_positional_restraint_strength
from nexus.md.openmm._reporter import add_reporters

from nexus.core.trackers.main_tracker import main_tracker

# NVT Heating, then NPT Equilibration (with barostat added in equilibration step)
@main_tracker("Heating")
def heat(mcfg: MDConfig, simulation: Simulation):
    working_dir = mcfg.common.working_dir

    temp = mcfg.common.temp # This temp here is the final desired temperature
    dt = mcfg.common.dt

    mid_temp = mcfg.heat.mid_temp # Adjustable middle temp for heating strategy
    time_mid_temp = mcfg.heat.time_mid_temp # Timestamp when mid_temp is reached
    time_temp = mcfg.heat.time_temp # Timestap when temp is reached
    total_time = mcfg.heat.total_time

    simulation.reporters.clear()
    # Ignore heating outputs for now
    simulation, h_outputs = add_reporters(simulation, "heat", working_dir, 10000, int(total_time / dt))
    
    restraint = mcfg.heat.restraint
    set_positional_restraint_strength(simulation, restraint)

    curr_temp = 0
    # From 0 to time_mid_temp picoseconds
    simulation, curr_temp = continuous_heat(simulation, curr_temp, int(time_mid_temp / dt), mid_temp)

    # From time_mid_temp to time_temp
    simulation, curr_temp = continuous_heat(simulation, curr_temp, int((time_temp - time_mid_temp) / dt), temp) 

    # Finally, current temp should be at temp, and we step the rest from time_temp to total_time
    simulation.step(int((total_time - time_temp) / dt))

    return simulation


def continuous_heat(simulation: Simulation, curr_temp: float, total_steps: int, top_temperature: float):
    import numpy as np
    """Divide a step count across windows while preserving the exact total."""
    number_of_windows = 100
    temp_range = top_temperature - curr_temp
    # np.repeat creates a flat array of 1s, and array_split divides it evenly/smoothly
    # Then we sum each split section to get the step counts per window
    dummy_array = np.ones(total_steps, dtype=int)
    step_windows = np.array([len(w) for w in np.array_split(dummy_array, number_of_windows)])

    # Each temperature window stores the temperature to increase, proportional to the step size
    temperature_windows = np.array([s/total_steps*temp_range for s in step_windows])
    
    for step, temp_increase in zip(step_windows, temperature_windows):
        curr_temp += temp_increase
        simulation.integrator.setTemperature(curr_temp * kelvin)
        simulation.step(step)

    return simulation, curr_temp