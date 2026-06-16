from pydantic import BaseModel
import os
from nexus.config import clear_scratch
from nexus.md.mmpbsa.generate_mmpbsa_figures import generate_mmpbsa_figures
from nexus.md.mmpbsa.mmpbsa_config import MMPBSAConfig
from nexus.md.mmpbsa.generate_mmpbsa_input import generate_mmpbsa_input
from nexus.md.mmpbsa.run_mmpbsa import run_mmpbsa


class MMPBSAPipeline(BaseModel):
    cfg: MMPBSAConfig

    def _run(self):

        AMBERHOME = os.environ.get("AMBERHOME")
        if not AMBERHOME:
            raise RuntimeError("AMBERHOME environment variable not set")

        mmpbsa_input = generate_mmpbsa_input(self.cfg)
        outputs = run_mmpbsa(self.cfg, mmpbsa_input)
        generate_mmpbsa_figures(self.cfg, outputs)
        
        clear_scratch(self.cfg)
        