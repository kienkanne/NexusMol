from openmm.app import CheckpointReporter, DCDReporter, PDBFile, StateDataReporter


def clear_reporters(simulation):
    simulation.reporters.clear()
    return simulation

class CustomPrecisionReporter(StateDataReporter):
    def __init__(self, file, reportInterval, precision=3, **kwargs):
        """
        Custom StateDataReporter to control decimal precision.
        :param precision: Number of decimal places for float values (default: 4)
        """
        super().__init__(file, reportInterval, **kwargs)
        self.precision = precision

    def _constructReportValues(self, simulation, state):
        values = super()._constructReportValues(simulation, state)

        formatted_values = []
        for val in values:
            if isinstance(val, float):
                formatted_values.append(round(val, self.precision))
            else:
                formatted_values.append(val)

        return formatted_values
            

def add_reporters(
    simulation,
    output_name,
    working_dir,
    reportInterval,
    total_steps,
    precision=3,
    write_checkpoint=True,
):
    """
    Attach stage-specific DCD, log, and optional checkpoint reporters.
    The precision paramter is used to control decimal precision in the log file.
    """

    log = str(working_dir / f"{output_name}.log")
    traj = str(working_dir / f"{output_name}.dcd")

    simulation.reporters.append(DCDReporter(traj, reportInterval))
    simulation.reporters.append(
        CustomPrecisionReporter(
            file=log,
            reportInterval=reportInterval,
            precision=precision,
            step=True,
            time=True,
            potentialEnergy=True,
            kineticEnergy=True,
            totalEnergy=True,
            temperature=True,
            volume=True,
            density=True,
            progress=True,
            remainingTime=True,
            speed=True,
            totalSteps=total_steps,
        )
    )

    chk = None
    if write_checkpoint:
        chk = str(working_dir / f"{output_name}.chk")
        simulation.reporters.append(
            CheckpointReporter(chk, reportInterval)
        )

    return simulation, (traj, chk, log)
