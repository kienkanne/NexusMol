from dataclasses import dataclass

from compdd.configs.root_config import RootConfig
from compdd.ligands.ligands_prep import ligands_prep
from compdd.dock6._dock6_prep_rec import dock6_prep_rec
from compdd.dock6._dock6_docking import dock6_docking
from compdd.utils.matchmixer import matchmixer
from compdd.utils.write_summary_csv import write_summary_csv
from compdd.utils.copy_to_results import copy_to_results

@dataclass(frozen=True)
class DOCK6Pipeline():
    cfg: RootConfig

    def run(self):
        self.cfg.common.program = "dock6"

        lig_files = ligands_prep(self.cfg)
        prepped_recs = dock6_prep_rec(self.cfg)
        pairs = matchmixer(prepped_recs, lig_files, 
                           self.cfg.common.prepared_suffix, self.cfg.common.mode)

        out_files = dock6_docking(self.cfg, pairs)
        docking_summary = write_summary_csv(self.cfg, out_files, prepped_recs)

        copy_to_results(self.cfg, prepped_recs, docking_summary, out_files)
