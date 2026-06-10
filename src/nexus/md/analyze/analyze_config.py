from pydantic import BaseModel, ConfigDict, Field
from pathlib import Path


class CommonConfig(BaseModel):
    prmtop: Path
    trajin: Path
    mask: str
    
    job_name: str = "analysis"
    output_dir: Path = Path.cwd() / "results"


class TrajectoryConfig(BaseModel):
    rmsd: bool = False
    hbond: bool = False
    pca: bool = False


class AnalyzeConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    trajectory: TrajectoryConfig = Field(default_factory=TrajectoryConfig)

    model_config = ConfigDict(extra='allow')
