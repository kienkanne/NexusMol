from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from pathlib import Path


class CommonConfig(BaseModel):
    receptor: Path
    output_dir: Optional[Path] = Path.cwd() / "results"
    job_name: Optional[str] = "solvated_system"


class LigandConfig(BaseModel):
    ligand: Optional[Path] = None
    pose_num: Optional[int] = 1
    charge: Optional[int] = 0


class SystemConfig(BaseModel):
    # Technically these are literal, but there are a lot of options
    force_field: Optional[str] = "ff19SB"
    water_model: Optional[str] = "opc"

    box_type: Optional[Literal["Box", "Oct"]] = "Oct"
    box_size: Optional[float] = 12.0
    salt_conc: Optional[float] = 0.15


class BuildConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    ligand: LigandConfig = Field(default_factory=LigandConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)

    model_config = ConfigDict(extra='allow')
