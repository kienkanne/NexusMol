from dataclasses import dataclass

from nexus.dock.dock_config import DockConfig
from nexus.dock.dock6._prep_rec import dock6_parallel_prep_rec
from nexus.dock.dock6._docking import dock6_parallel_docking
from nexus.dock.utils.matchmixer import matchmixer
from nexus.dock.utils.write_summary_csv import write_summary_csv
from nexus.dock.utils.final_copy import final_copy

@dataclass(frozen=True)
class DOCK6Pipeline():
    dcfg: DockConfig

    def _run(self):
        self.dcfg.common.program = "dock6"
        if self.dcfg.libs.dock_home is None:
            raise ValueError("libs.dock_home is missing")

        if ".mol2" not in self.dcfg.ligands.suffix:
            raise ValueError("Ligands for DOCK6 must have '.mol2' suffix.")
        lig_paths = self.dcfg.ligands.source

        rec_bundles = dock6_parallel_prep_rec(self.dcfg)
        pairs = matchmixer(rec_bundles, lig_paths)
        out_files = dock6_parallel_docking(self.dcfg, pairs)

        written_scores, written_clusters = write_summary_csv(self.dcfg, out_files, rec_bundles)

        final_copy(self.dcfg, rec_bundles, written_scores, written_clusters, out_files)
