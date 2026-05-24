from dataclasses import dataclass

from nexus.dock.dock_config import DockConfig
from nexus.dock.vina._prep_rec import vina_prep_rec
from nexus.dock.utils.matchmixer import matchmixer
from nexus.dock.vina._docking import vina_docking
from nexus.dock.utils.write_summary_csv import write_summary_csv
from nexus.dock.utils.final_copy import final_copy

@dataclass(frozen=True)
class VinaPipeline():
    dcfg: DockConfig

    def run(self):
        self.dcfg.common.program = "vina"
        if ".pdbqt" not in self.dcfg.ligands.suffix:
            raise ValueError("Ligands for Vina must have '.pdbqt' suffix.")
        lig_paths = self.dcfg.ligands.source
        rec_bundles = vina_prep_rec(self.dcfg)

        pairs = matchmixer(rec_bundles, lig_paths, 
                           "self.dcfg.common.prepared_suffix", self.dcfg.common.mode)
        # Disable validate for now
        out_files = vina_docking(self.dcfg, pairs)
        docking_summary = write_summary_csv(self.dcfg, out_files, rec_bundles)

        final_copy(self.dcfg, rec_bundles, docking_summary, out_files)
