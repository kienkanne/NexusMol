from pydantic import BaseModel, model_validator
from typing import Optional, Literal
from pathlib import Path


class PrepConfig(BaseModel):
    chimerax: Optional[Path] = Path("/usr/local/chimerax/bin/ChimeraX")
    input_file: Optional[Path] = None
    output_format: Optional[Literal["pdb", "cif"]] = "pdb"
    cleaned_suffix: Optional[str] = "cleaned"
    log_file: Optional[Path] = None  # Default to None, computed later if missing
    output_dir: Optional[Path] = None

    @model_validator(mode="after")
    def set_default_log_file(self) -> "PrepConfig":
        # Only compute log_file if input_file is provided and log_file wasn't explicitly set
        if self.input_file and self.log_file is None:
            # .with_suffix() replaces the extension, e.g., "protein.pdb" -> "protein.log"
            self.log_file = self.output_dir / f"{self.input_file.stem}.log"
        return self


from nexus.core.trackers.logging_utils import setup_logger

def load_prep_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    pcfg = PrepConfig.model_validate(data)
    pcfg.log_file = setup_logger(pcfg.log_file, time_verbose=False)
    pcfg.output_dir.mkdir(parents=True, exist_ok=True)
    return pcfg