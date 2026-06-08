from dataclasses import dataclass

from nexus.dock.dock_config import DockConfig
from nexus.dock.vina._prep_rec import vina_parallel_prep_rec
from nexus.dock.utils.matchmixer import matchmixer
from nexus.dock.vina._docking import vina_parallel_docking
from nexus.dock.utils.write_summary_csv import write_summary_csv
from nexus.dock.utils.final_copy import final_copy

@dataclass(frozen=True)
class VinaPipeline():
    dcfg: DockConfig

    def _run(self):
        self.dcfg.common.program = "vina"
        if ".pdbqt" not in self.dcfg.ligands.suffix:
            raise ValueError("Ligands for Vina must have '.pdbqt' suffix.")
        lig_paths = self.dcfg.ligands.source
        rec_bundles = vina_parallel_prep_rec(self.dcfg)

        pairs = matchmixer(rec_bundles, lig_paths)
        out_files = vina_parallel_docking(self.dcfg, pairs)
        written_scores, written_clusters = write_summary_csv(self.dcfg, out_files, rec_bundles)

        final_copy(self.dcfg, rec_bundles, written_scores, written_clusters, out_files)
