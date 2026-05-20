from dataclasses import dataclass

from compdd.configs.root_config import RootConfig
from compdd.ligands.ligands_prep import ligands_prep
from compdd.vina._vina_prep_rec import vina_receptors_prep
from compdd.utils.matchmixer import matchmixer
from compdd.vina._vina_docking import vina_docking
from compdd.utils.write_summary_csv import write_summary_csv
from compdd.utils.copy_to_results import copy_to_results

@dataclass(frozen=True)
class VinaPipeline():
    cfg: RootConfig

    def run(self):
        self.cfg.common.program = "vina"

        prepped_ligs = ligands_prep(self.cfg)
        prepped_recs = vina_receptors_prep(self.cfg)

        pairs = matchmixer(prepped_recs, prepped_ligs, 
                           self.cfg.common.prepared_suffix, self.cfg.common.mode)

        out_files = vina_docking(self.cfg, pairs)
        docking_summary = write_summary_csv(self.cfg, out_files, prepped_recs)

        config_files = [bundle.vina_config for bundle in prepped_recs]
        copy_to_results(self.cfg, prepped_recs, docking_summary, out_files, config_files)
