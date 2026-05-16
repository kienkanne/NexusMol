from dataclasses import dataclass

from compdd.config import RootConfig
from compdd.docking_utils._ligands_prep import _ligands_prep
from compdd.dock6._dock6_prep_rec import _dock6_prep_rec
from compdd.dock6._dock6_docking import _dock6_docking
from compdd.docking_utils._write_summary_csv import _write_summary_csv
from compdd.docking_utils._copy_to_results import _copy_to_results

@dataclass(frozen=True)
class DOCK6Pipeline():
    cfg: RootConfig

    def run(self):
        lig_files = _ligands_prep(self.cfg, program="dock6")
        prepped_rec, selected_spheres = _dock6_prep_rec(self.cfg)
        out_files, lig_names = _dock6_docking(self.cfg, lig_files, selected_spheres)
        _write_summary_csv(self.cfg, out_files, lig_names, program="dock6")
        _copy_to_results(self.cfg, prepped_rec, out_files)

        logger = self.cfg.common.logger
        manifest = self.cfg.common.manifest
        manifest.finalize(success=True)
        logger.info("DOCK 6 pipeline completed")
