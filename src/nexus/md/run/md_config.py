from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Literal, Annotated, Union
from pathlib import Path


class CommonConfig(BaseModel):
    prmtop: Path
    inpcrd: Path
    mask: str
    
    temp: Optional[float] = 300.0
    dt: Optional[float] = 0.002
    cut: Optional[float] = 10.0

    job_name: Optional[str] = "md"
    output_dir: Optional[Path] = Path.cwd() / "results"


class MinConfig(BaseModel):
    n_min_runs: Optional[int] = 7
    ncyc: Optional[int] = 1000
    maxcyc: Optional[int] = 5000
    restraints: Optional[List[float]] = [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]


class HeatConfig(BaseModel):
    mid_temp: Optional[float] = 100.0
    time_mid_temp: Optional[float] = 100.0
    time_temp: Optional[float] = 500.0
    total_time: Optional[float] = 2000.0
    restraint: Optional[float] = 10.0


class EqConfig(BaseModel):
    n_eq_runs: Optional[int] = 7
    eq_time: Optional[float] = 100.0
    restraints: Optional[List[float]] = [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]


class ProdConfig(BaseModel):
    num_seeds: Optional[int] = 1
    rand_time: Optional[float] = 200.0
    prod_time: Optional[float] = 2500.0
    prod_freq: Optional[float] = 10.0


class AmberConfig(BaseModel):
    program: Literal["amber"]


class OpenMMConfig(BaseModel):
    program: Literal["openmm"]


EngineConfig = Annotated[
    Union[AmberConfig, OpenMMConfig],
    Field(discriminator="program")
]


class MetadataConfig(BaseModel):
    model_config = ConfigDict(extra="allow")


class MDConfig(BaseModel):
    common: CommonConfig
    min: MinConfig = Field(default_factory=MinConfig)
    heat: HeatConfig = Field(default_factory=HeatConfig)
    eq: EqConfig = Field(default_factory=EqConfig)
    prod: ProdConfig = Field(default_factory=ProdConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    engine: EngineConfig

    model_config = ConfigDict(extra="allow")
