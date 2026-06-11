from pathlib import Path
from pydantic import BaseModel
from nexus.prep.prep_config import PrepConfig
from nexus.core.utils.extract_files import extract_files
from nexus.prep.rec._chimerax_rec_prep import chimerax_rec_prep


class RecPipeline(BaseModel):
    cfg: PrepConfig

    def _run(self):
        self.cfg.common.input = extract_files(self.cfg.common.input, [".pdb", ".cif"])
        if not self.cfg.common.input:
            raise ValueError("Invalid input, no pdb of cif file found.")
        
        if self.cfg.common.suffix is None:
            self.cfg.common.suffix = "_cleaned.pdb"
        if ".pdb" not in self.cfg.common.suffix and ".cif" not in self.cfg.common.suffix:
            raise ValueError("Output receptor format must be 'pdb' or 'cif'.")
   
        if self.cfg.common.output_dir is None:
            self.cfg.common.output_dir = Path.cwd()
        self.cfg.common.output_dir.mkdir(parents=True, exist_ok=True)
        
        chimerax_rec_prep(self.cfg)
