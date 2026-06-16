
from pydantic import BaseModel
from nexus.md.run.md_config import MDConfig
from nexus.config import clear_scratch
from nexus.md.run.openmm._setup import setup
from nexus.md.run.openmm._minimize import minimize
from nexus.md.run.openmm._heat import heat
from nexus.md.run.openmm._equilibrate import equilibrate
from nexus.md.run.openmm._produce import produce
from nexus.md.run.final_copy import final_copy


class OpenMMPipeline(BaseModel):
    cfg: MDConfig

    def _run(self):

        simulation = setup(self.cfg)

        simulation = minimize(self.cfg, simulation)
        simulation = heat(self.cfg, simulation)
        simulation = equilibrate(self.cfg, simulation)

        outputs = produce(self.cfg, simulation)

        final_copy(self.cfg, outputs)

        clear_scratch(self.cfg)
        