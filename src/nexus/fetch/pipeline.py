from dataclasses import dataclass
from pathlib import Path
from nexus.prep.chimerax_fix import chimerax_fix
from nexus.fetch.fetch_config import FetchConfig
from nexus.fetch.rcsb_fetch import rcsb_fetch
from nexus.prep._experimental.gemmi_strip import gemmi_strip

@dataclass(frozen=True)
class FetchPipeline:
    fcfg: FetchConfig

    def run(self):
        for id in self.fcfg.id_list:
            raw_path = rcsb_fetch(self.fcfg, id)
