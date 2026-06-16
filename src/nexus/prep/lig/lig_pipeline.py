from pathlib import Path
from pydantic import BaseModel
from nexus.prep.prep_config import PrepConfig
from nexus.core.utils.extract_files import extract_files


class LigPipeline(BaseModel):
    cfg: PrepConfig

    def _run(self):
        n_jobs = self.cfg.lig.n_jobs

        output_dir = self.cfg.common.output_dir
        suffix = self.cfg.common.suffix

        if output_dir is None:
            output_dir = Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        if suffix is None:
            suffix = "_prepared.pdbqt"
        if ".pdbqt" not in suffix and ".mol2" not in suffix:
            raise ValueError("Output receptor format must be 'pdbqt' or 'mol2'.")

        if self.cfg.common.input.suffix == ".csv":
            csv_path = self.cfg.common.input
            from nexus.prep.lig._rdkit_gen3d import _parallel_rdkit_gen3d
            mol_with_h_list, names = _parallel_rdkit_gen3d(csv_path, n_jobs)

        else:
            sdfs = extract_files(self.cfg.common.input, ".sdf", recursive=True)
            if not sdfs:
                raise ValueError("Invalid input, no sdf file found.")
            from nexus.prep.lig._sdfs_to_mols import _sdfs_to_mols
            mol_with_h_list, names = _sdfs_to_mols(sdfs, n_jobs)

        output_list = [output_dir / f"{name}{suffix}" for name in names]

        if output_list[0].suffix == ".pdbqt":
            from nexus.prep.lig._meeko_charge import _parallel_meeko_charge
            prepared_ligs = _parallel_meeko_charge(mol_with_h_list, output_list, n_jobs)

        elif output_list[0].suffix == ".mol2":
            from nexus.prep.lig._obabel_charge import _parallel_obabel_charge
            prepared_ligs = _parallel_obabel_charge(mol_with_h_list, output_list, n_jobs)

        return prepared_ligs