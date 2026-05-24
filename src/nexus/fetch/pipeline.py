from dataclasses import dataclass
from nexus.fetch.fetch_config import FetchConfig
from nexus.fetch.rcsb_fetch import rcsb_fetch
from pathlib import Path

@dataclass(frozen=True)
class FetchPipeline:
    fcfg: FetchConfig

    def run(self):
        if Path(self.fcfg.input[0]).is_file():
            with open(self.fcfg.input[0], "r") as f:
                self.fcfg.input = f.read().splitlines()
        else:
            self.fcfg.input = list(self.fcfg.input)

        if self.fcfg.output_dir is None:
            self.fcfg.output_dir = Path.cwd()

        rcsb_fetch(self.fcfg)
