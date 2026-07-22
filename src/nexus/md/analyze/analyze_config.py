from pydantic import BaseModel, ConfigDict, Field
from pathlib import Path
from typing import Literal


class CommonConfig(BaseModel):
    prmtop: Path
    trajin: Path
    receptor_mask: str
    ligand_mask: str = None
    pca_cluster_mask: str = "@N,C,CA"
    interval: int = 1
    
    job_name: str = "analysis"
    output_dir: Path = Path.cwd() / "results"


class RMSConfig(BaseModel):
    rms_option: Literal["alpha", "backbone"] = "alpha"


class HbondsConfig(BaseModel):
    pp: bool = False
    bb: bool = False
    pl: bool = False


class SSConfig(BaseModel):
    run: bool = False


class PCAConfig(BaseModel):
    run: bool = False
    n_eigen: int = 10


class ClusterConfig(BaseModel):
    run: bool = False
    n_cluster: int = 5


class FiguresConfig(BaseModel):
    dt_frame: float = 10
    format: Literal["pdf", "png", "svg"] = "pdf"


class AnalyzeConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    rms: RMSConfig = Field(default_factory=RMSConfig)
    hbonds: HbondsConfig = Field(default_factory=HbondsConfig)
    ss: SSConfig = Field(default_factory=SSConfig)
    pca: PCAConfig = Field(default_factory=PCAConfig)
    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    figures: FiguresConfig = Field(default_factory=FiguresConfig)

    model_config = ConfigDict(extra='allow')
