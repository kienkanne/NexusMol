
from pydantic import BaseModel
from nexus.md.md_config import MDConfig

from nexus.md.openmm._setup import setup
from nexus.md.openmm._minimize import minimize
from nexus.md.openmm._heat import heat
from nexus.md.openmm._equilibrate import equilibrate
from nexus.md.openmm._produce import produce
from nexus.md.final_copy import final_copy


class OpenMMPipeline(BaseModel):
    mcfg: MDConfig

    def _run(self):

        simulation = setup(self.mcfg)

        simulation = minimize(self.mcfg, simulation)
        simulation = heat(self.mcfg, simulation)
        simulation = equilibrate(self.mcfg, simulation)

        outputs = produce(self.mcfg, simulation)

        final_copy(self.mcfg, outputs)