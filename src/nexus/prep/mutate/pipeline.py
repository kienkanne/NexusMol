from pathlib import Path
from pydantic import BaseModel
from nexus.prep.prep_config import PrepConfig
from nexus.core.extract_files import extract_files
from nexus.prep.mutate._chimerax_mutate import chimerax_mutate


class MutatePipeline(BaseModel):
    pcfg: PrepConfig

    def _run(self):
        
        if self.pcfg.mutate.mutations is not None:
            mutation_list = []
            for mutation in self.pcfg.mutate.mutations:
                sel_res = mutation.split("-")
                mutation_list.append(sel_res)
            self.pcfg.mutate.mutations = mutation_list

        self.pcfg.common.input = extract_files(self.pcfg.common.input, [".pdb", ".cif"])
        if not self.pcfg.common.input:
            raise ValueError("Invalid input, no pdb of cif file found.")
        
        if self.pcfg.common.suffix is None:
            self.pcfg.common.suffix = "_mutated.pdb"
        if ".pdb" not in self.pcfg.common.suffix and ".cif" not in self.pcfg.common.suffix:
            raise ValueError("Output receptor format must be 'pdb' or 'cif'.")

        if self.pcfg.common.output_dir is None:
            self.pcfg.common.output_dir = Path.cwd()
        self.pcfg.common.output_dir.mkdir(parents=True, exist_ok=True)
        
        chimerax_mutate(self.pcfg)

