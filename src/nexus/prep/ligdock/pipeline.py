from pathlib import Path
from pydantic import BaseModel
from nexus.prep.prep_config import PrepConfig
from nexus.prep.ligdock.ligands_prep import ligands_prep
from nexus.core.extract_files import extract_files


class LigdockPipeline(BaseModel):
    pcfg: PrepConfig

    def _run(self):
        
        if self.pcfg.common.suffix is None:
            self.pcfg.common.suffix = "_prepared.pdbqt"
        if ".pdbqt" not in self.pcfg.common.suffix and ".mol2" not in self.pcfg.common.suffix:
            raise ValueError("Output receptor format must be 'pdbqt' or 'mol2'.")

        if self.pcfg.common.input.suffix == ".csv":
            self.pcfg.ligdock.source = "smiles"

        else:
            self.pcfg.ligdock.source = "sdf"
            self.pcfg.common.input = extract_files(self.pcfg.common.input, ".sdf", recursive=True)
            if not self.pcfg.common.input:
                raise ValueError("Invalid input, no sdf file found.")

        if self.pcfg.common.output_dir is None:
            self.pcfg.common.output_dir = Path.cwd()
        self.pcfg.common.output_dir.mkdir(parents=True, exist_ok=True)
        
        return ligands_prep(self.pcfg)