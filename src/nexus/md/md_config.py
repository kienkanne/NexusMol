from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


class CommonConfig(BaseModel):
    project_name: Optional[str] = "md"
    working_dir: Optional[Path] = Path.cwd() / "artifacts"
    results_dir: Optional[Path] = Path.cwd() / "results"
    
    temp: Optional[float] = 300.0
    dt: Optional[float] = 0.002
    cut: Optional[float] = 10.0
    mask: Optional[str] = None

    prmtop: Optional[Path] = None
    inpcrd: Optional[Path] = None

'''class TleapConfig(BaseModel):
    protein_pdb: Path
    working_dir: Path
    forcefield: str
    water_model: str
    box_type: str
    box_size: float
'''

class MinConfig(BaseModel):
    n_min_runs: Optional[int] = 7
    ncyc: Optional[int] = 1000
    maxcyc: Optional[int] = 1000
    restraint: Optional[List[float]] = [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]


class HeatConfig(BaseModel):
    mid_temp: Optional[float] = 100.0
    time1: Optional[float] = 100.0
    time2: Optional[float] = 500.0
    total_time: Optional[float] = 2000.0
    restraint: Optional[float] = 10.0


class EqConfig(BaseModel):
    n_eq_runs: Optional[int] = 7
    eq_time: Optional[float] = 100.0
    restraint: Optional[List[float]] = [10.0, 5.0, 2.0, 1.0, 0.5, 0.1, 0.0]


class ProdConfig(BaseModel):
    num_seeds: Optional[int] = 1
    rand_time: Optional[float] = 200.0
    prod_time: Optional[float] = 2500.0
    prod_freq: Optional[float] = 10.0


class MDConfig(BaseModel):
    common: Optional[CommonConfig] = CommonConfig()
    #tleap: Optional[TleapConfig] =  TleapConfig()
    min: Optional[MinConfig] = MinConfig()
    heat: Optional[HeatConfig] = HeatConfig()
    eq: Optional[EqConfig] = EqConfig()
    prod: Optional[ProdConfig] = ProdConfig()


def load_md_config(path):
    import yaml
    with open(path) as f:
        mcfg = yaml.safe_load(f)
    return MDConfig.model_validate(mcfg)
    