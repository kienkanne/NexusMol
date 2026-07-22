from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from pathlib import Path


class CommonConfig(BaseModel):
    seq_file: Path
    output_dir: Optional[Path] = Path.cwd() / "results"
    job_name: str = "peptide_systems"


class SystemConfig(BaseModel):
    force_field: Optional[str] = "ff19SB"
    water_model: Optional[str] = "opc"

    box_type: Optional[Literal["Box", "Oct"]] = "Oct"
    box_size: Optional[float] = 12.0


class BuildPepConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)

    model_config = ConfigDict(extra='allow')
