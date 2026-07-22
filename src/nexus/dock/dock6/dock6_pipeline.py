from pydantic import BaseModel
from nexus.config import clear_scratch
from nexus.dock.dock_config import DockConfig
from nexus.dock.dock6._prep_rec import dock6_parallel_prep_rec
from nexus.dock.dock6._docking import dock6_parallel_docking
from nexus.dock.utils.matchmixer import matchmixer
from nexus.dock.utils.write_summary_csv import write_summary_csv, create_master_df
from nexus.dock.utils.final_copy import final_copy


class DOCK6Pipeline(BaseModel):
    cfg: DockConfig

    def _run(self):
        if ".mol2" not in self.cfg.ligands.suffix:
            raise ValueError("Ligands for DOCK6 must have '.mol2' suffix.")
        lig_paths = self.cfg.ligands.source

        rec_bundles = dock6_parallel_prep_rec(self.cfg)

        pairs = matchmixer(rec_bundles, lig_paths)
        out_files = dock6_parallel_docking(self.cfg, pairs)

        master_df = create_master_df(self.cfg, out_files, rec_bundles)

        final_copy(self.cfg, rec_bundles, master_df, out_files)

        clear_scratch(self.cfg)
