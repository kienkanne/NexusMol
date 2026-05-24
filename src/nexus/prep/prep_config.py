from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, List
from pathlib import Path

class CommonConfig(BaseModel):
    input: Optional[Path] = None
    output_dir: Optional[Path] = None
    suffix: Optional[str] = None

    chimerax: Optional[Path] = "/usr/local/chimerax/bin/ChimeraX"

    model_config = ConfigDict(extra='allow')

class RecConfig(BaseModel):
    dry: Optional[bool] = False

class MutateConfig(BaseModel):
    mutations: Optional[List[str]] = None

class LigdockConfig(BaseModel):
    source: Optional[Literal["smiles", "sdf"]] = "sdf"
    format: Optional[Literal["pdbqt", "mol2"]] = "pdbqt"
    type: Optional[Literal["GAFF", "AM1-BCC"]] = "GAFF"

class PrepConfig(BaseModel):
    common: CommonConfig = CommonConfig()
    rec: RecConfig = RecConfig()
    mutate: MutateConfig = MutateConfig()
    ligdock: LigdockConfig = LigdockConfig()


def load_prep_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    pcfg = PrepConfig.model_validate(data)
    
    if pcfg.common.output is None:
        pcfg.common.output = pcfg.common.input.parent

    return pcfg
