from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from pathlib import Path

class CommonConfig(BaseModel):
    input: Optional[Path] = None
    output_dir: Optional[Path] = Path.cwd()
    suffix: Optional[str] = None


class RecConfig(BaseModel):
    dry: Optional[bool] = False

class MutateConfig(BaseModel):
    mutations: Optional[List[str]] = None

class LigConfig(BaseModel):
    n_jobs: Optional[int] = 1
    

class PrepConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    rec: RecConfig = Field(default_factory=RecConfig)
    mutate: MutateConfig = Field(default_factory=MutateConfig)
    lig: LigConfig = Field(default_factory=LigConfig)

    model_config = ConfigDict(extra="allow")
