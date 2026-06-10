from pydantic import BaseModel, ConfigDict, Field
from pathlib import Path


class CommonConfig(BaseModel):
    prmtop: Path
    trajin: Path
    mask: str
    
    job_name: str = "mmpbsa"
    output_dir: Path = Path.cwd() / "results"

    start_frame: int = 1
    end_frame: int = 9999999
    interval: int = 10
    n_cores: int = 1


class GBConfig(BaseModel):
    run: bool = False
    igb: int = 5
    saltcon: float = 0.150


class PBConfig(BaseModel):
    run: bool = False
    istrng: float = 0.150
    fillratio: float = 4.0


class MMPBSAConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    gb: GBConfig = Field(default_factory=GBConfig)
    pb: PBConfig = Field(default_factory=PBConfig)

    model_config = ConfigDict(extra='allow')
