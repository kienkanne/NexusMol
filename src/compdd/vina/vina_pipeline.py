from dataclasses import dataclass

from compdd.config import RootConfig
from compdd.docking_utils._ligands_prep import _ligands_prep
from compdd.vina._vina_prep_rec import _vina_prep_rec
from compdd.vina._vina_docking import _vina_docking
from compdd.docking_utils._write_summary_csv import _write_summary_csv
from compdd.docking_utils._copy_to_results import _copy_to_results

@dataclass(frozen=True)
class VinaPipeline():
    cfg: RootConfig

    def run(self):
        lig_files = _ligands_prep(self.cfg, program="vina")
        prepped_rec, vina_config = _vina_prep_rec(self.cfg)
        out_files, lig_names = _vina_docking(self.cfg, lig_files, prepped_rec, vina_config)
        _write_summary_csv(self.cfg, out_files, lig_names, program="vina")
        _copy_to_results(self.cfg, prepped_rec, out_files)

        logger = self.cfg.common.logger
        manifest = self.cfg.common.manifest
        manifest.finalize(success=True)
        logger.info("Vina pipeline completed")
