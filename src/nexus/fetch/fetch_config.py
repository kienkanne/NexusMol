from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path


class FetchConfig(BaseModel):
    input: Optional[List[str] | Path] = None
    ligand_name: Optional[str] = None
    output_dir: Optional[Path] = None
