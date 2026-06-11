from dataclasses import dataclass
from nexus.fetch.fetch_config import FetchConfig
from nexus.fetch.rcsb_fetch import rcsb_fetch
from pathlib import Path

@dataclass(frozen=True)
class FetchPipeline:
    cfg: FetchConfig

    def _run(self):
        if Path(self.cfg.input[0]).is_file():
            with open(self.cfg.input[0], "r") as f:
                self.cfg.input = f.read().splitlines()
        else:
            self.cfg.input = list(self.cfg.input)

        if self.cfg.output_dir is None:
            self.cfg.output_dir = Path.cwd()

        rcsb_fetch(self.cfg)
