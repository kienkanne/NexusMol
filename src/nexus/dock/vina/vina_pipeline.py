from pydantic import BaseModel
from nexus.config import clear_scratch
from nexus.dock.dock_config import DockConfig
from nexus.dock.vina._prep_rec import vina_parallel_prep_rec
from nexus.dock.utils.matchmixer import matchmixer
from nexus.dock.vina._docking import vina_parallel_docking
from nexus.dock.utils.create_master_df import create_master_df, write_summary_csv
from nexus.dock.utils.final_copy import final_copy


class VinaPipeline(BaseModel):
    cfg: DockConfig

    def _run(self):
        if ".pdbqt" not in self.cfg.ligands.suffix:
            raise ValueError("Ligands for Vina must have '.pdbqt' suffix.")
        
        lig_paths = self.cfg.ligands.source
        rec_bundles = vina_parallel_prep_rec(self.cfg)

        pairs = matchmixer(rec_bundles, lig_paths)
        out_files = vina_parallel_docking(self.cfg, pairs)

        master_df = create_master_df(self.cfg, out_files, rec_bundles)

        final_copy(self.cfg, rec_bundles, master_df, out_files)

        clear_scratch(self.cfg)
