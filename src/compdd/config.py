from pydantic import BaseModel, ConfigDict
from typing import Optional
from pathlib import Path


class LibsConfig(BaseModel):
    chimerax: Path
    chimera: Path

    mgltools: Path
    dock_home: Path

    obabel: Path
    parallel: Path
    vina: Path


class CommonConfig(BaseModel):
    model_config = ConfigDict(extra='allow')

    project_name: str
    working_dir: Path
    results_dir: Path

    receptor: Path
    ligands_csv: Path

    padding: Optional[float] = 5.0
    n_jobs: int = 1
    max_poses: int = 8
    pocket_selection: Optional[str] = None


class VinaConfig(BaseModel):
    exhaustiveness: Optional[int] = 32
    num_modes: Optional[int] = 8
    cpu: Optional[int] = 1
    reference: Optional[Path] = None
    write_box : Optional[bool] = True


class DOCK6Config(BaseModel):
    max_orientations: float = 1000
    radius: Optional[float] = 10.0


class RootConfig(BaseModel):
    libs: LibsConfig
    common: CommonConfig
    vina: VinaConfig
    dock6: DOCK6Config


from compdd.utils.logging_utils import setup_logger
from compdd.utils.manifest import Manifest
from compdd.utils.runstate import State

def load_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = RootConfig.model_validate(data)
    
    cfg.common.working_dir = Path(cfg.common.working_dir / cfg.common.project_name)
    cfg.common.results_dir = Path(cfg.common.results_dir / cfg.common.project_name)

    cfg.common.logger = setup_logger(Path(cfg.common.working_dir / "run.log"))
    cfg.common.manifest = Manifest(Path(cfg.common.working_dir / "manifest.json"))
    cfg.common.runstate = State(Path(cfg.common.working_dir / "state.json"))   

    return cfg


