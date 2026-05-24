from pathlib import Path
from pydantic import BaseModel
from nexus.prep.prep_config import PrepConfig, default_output
from nexus.core.extract_files import extract_files
from nexus.prep.rec._chimerax_rec_prep import chimerax_rec_prep


class RecPipeline(BaseModel):
    pcfg: PrepConfig

    def _run(self):
        self.pcfg.common.input = extract_files(self.pcfg.common.input, [".pdb", ".cif"])
        if not self.pcfg.common.input:
            raise ValueError("Invalid input, no pdb of cif file found.")
        
        if self.pcfg.common.suffix is None:
            self.pcfg.common.suffix = "_cleaned.pdb"
        if ".pdb" not in self.pcfg.common.suffix and ".cif" not in self.pcfg.common.suffix:
            raise ValueError("Output receptor format must be 'pdb' or 'cif'.")
   
        if self.pcfg.common.output_dir is None:
            self.pcfg.common.output_dir = Path.cwd()

        chimerax_rec_prep(self.pcfg)
