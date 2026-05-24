from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path


class FetchConfig(BaseModel):
    input: Optional[List[str] | Path] = None
    ligand_name: Optional[str] = None
    output_dir: Optional[Path] = None



def load_fetch_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    rcfg = FetchConfig.model_validate(data)

    return rcfg
