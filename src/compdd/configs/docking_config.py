from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional
from pathlib import Path
import os


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
    prepared_suffix: str = "prepped"

    padding: Optional[float] = 5.0
    n_jobs: int = 1
    max_poses: int = 8
    pocket_option: Literal["selection", "reference"] = "selection"
    pocket_selection: Optional[str] = None
    reference: Optional[Path] = None
    program: Optional[Literal["vina", "dock6"]] = None


class VinaConfig(BaseModel):
    model_config = ConfigDict(extra='allow')

    exhaustiveness: Optional[int] = 32
    num_modes: Optional[int] = 8
    cpu: Optional[int] = 1
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


def _expand_path(path):
    return Path(os.path.expandvars(str(path))).expanduser()


def load_docking_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = RootConfig.model_validate(data)
    
    if getattr(cfg.vina, "reference", None) is not None and cfg.common.reference is None:
        cfg.common.reference = cfg.vina.reference

    cfg.common.working_dir = _expand_path(cfg.common.working_dir) / cfg.common.project_name
    cfg.common.results_dir = _expand_path(cfg.common.results_dir) / cfg.common.project_name
    cfg.common.receptor = _expand_path(cfg.common.receptor)
    if cfg.common.reference is not None:
        cfg.common.reference = _expand_path(cfg.common.reference)

    for field_name in LibsConfig.model_fields:
        setattr(cfg.libs, field_name, _expand_path(getattr(cfg.libs, field_name)))

    cfg.common.logger = setup_logger(Path(cfg.common.working_dir / "run.log"))
    cfg.common.manifest = Manifest(Path(cfg.common.working_dir / "manifest.json"))
    cfg.common.runstate = State(Path(cfg.common.working_dir / "state.json"))   

    return cfg


def load_config(path):
    return load_docking_config(path)
