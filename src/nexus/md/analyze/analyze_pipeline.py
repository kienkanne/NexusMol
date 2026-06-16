from pydantic import BaseModel
import os
from nexus.config import clear_scratch
from nexus.md.analyze.analyze_config import AnalyzeConfig
from nexus.md.analyze.generate_analysis_figures import generate_analysis_figures
from nexus.md.analyze.generate_cpptraj_input import generate_cpptraj_input
from nexus.md.analyze.run_cpptraj import run_cpptraj


class AnalyzePipeline(BaseModel):
    cfg: AnalyzeConfig

    def _run(self):
        AMBERHOME = os.environ.get("AMBERHOME")
        if not AMBERHOME:
            raise RuntimeError("AMBERHOME environment variable not set")
        
        cpptraj_input, outputs = generate_cpptraj_input(self.cfg)
        outputs = run_cpptraj(self.cfg, cpptraj_input, outputs)
        generate_analysis_figures(self.cfg, outputs)

        clear_scratch(self.cfg)
