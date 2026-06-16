import os
from pydantic import BaseModel
from nexus.md.run.md_config import MDConfig
from nexus.config import clear_scratch
from nexus.md.run.amber._minimize import minimize
from nexus.md.run.amber._heat import heat
from nexus.md.run.amber._equilibrate import equilibrate
from nexus.md.run.amber._produce import produce
from nexus.md.run.final_copy import final_copy


class AmberPipeline(BaseModel):
    cfg: MDConfig

    def _run(self):
        AMBERHOME = os.environ.get("AMBERHOME")
        if not AMBERHOME:
            raise RuntimeError("AMBERHOME environment variable not set")

        prmtop = self.cfg.common.prmtop
        inpcrd = self.cfg.common.inpcrd

        if prmtop is None or not prmtop.is_file():
            raise FileNotFoundError(f"Missing prmtop at: {prmtop}")
        if inpcrd is None or not inpcrd.is_file():
            raise FileNotFoundError(f"Missing prmtop at: {inpcrd}")
        
        last_min_ncrst = minimize(self.cfg, prmtop, inpcrd)
        last_heat_ncrst = heat(self.cfg, prmtop, last_min_ncrst)
        last_eq_ncrst = equilibrate(self.cfg, prmtop, last_heat_ncrst)

        outputs = produce(self.cfg, prmtop, last_eq_ncrst)

        final_copy(self.cfg, outputs)

        clear_scratch(self.cfg)
