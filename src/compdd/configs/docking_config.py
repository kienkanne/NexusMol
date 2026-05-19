from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional
from pathlib import Path
import os


class LibsConfig(BaseModel):
    chimerax: Path
    chimera: Path

    dock_home: Path

    obabel: Path
    parallel: Path
    vina: Path


class CommonConfig(BaseModel):
    model_config = ConfigDict(extra='allow')

    project_name: str
    working_dir: Path
    results_dir: Path
    prepared_suffix: str = "prepped"

    padding: Optional[float] = 5.0
    n_jobs: int = 1
    max_poses: int = 8

    program: Optional[Literal["vina", "dock6"]] = None


class VinaConfig(BaseModel):
    exhaustiveness: Optional[int] = 32
    num_modes: Optional[int] = 8


class DOCK6Config(BaseModel):
    max_orientations: float = 1000
    radius: Optional[float] = 10.0


class ReceptorsConfig(BaseModel):
    source: Optional[Literal["pdb", "existing"]] = "pdb"

    pdbs: list[Path] | Path | None = None
    pocket_option: Literal["selection", "reference"] = "selection"
    pocket_selection: Optional[str] = None
    reference: Optional[Path] = None

    existing_dir: Optional[Path] = None


class LigandsConfig(BaseModel):
    source: Literal["smiles", "sdf","existing"] = "smiles"

    smiles_csv: Optional[Path] = None
    sdfs: list[Path] | Path | None = None
    output_dir : Optional[Path] = None
    existing_dir: Optional[Path] = None


class RootConfig(BaseModel):
    libs: LibsConfig
    common: CommonConfig
    vina: VinaConfig
    dock6: DOCK6Config
    receptors: ReceptorsConfig
    ligands: LigandsConfig
    


from compdd.utils.logging_utils import setup_logger
from compdd.utils.manifest import Manifest
from compdd.utils.runstate import State


def _expand_path(path):
    return Path(os.path.expandvars(str(path))).expanduser()


def load_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = RootConfig.model_validate(data)

    for subcfg_name in RootConfig.model_fields:
        subcfg = getattr(cfg, subcfg_name)

        for field_name in subcfg.__class__.model_fields:
            value = getattr(subcfg, field_name)
            if isinstance(value, Path):
                expanded_path = _expand_path(value)
                setattr(subcfg, field_name, expanded_path)
                if not expanded_path.is_file():
                    expanded_path.mkdir(parents=True, exist_ok=True)

    cfg.common.working_dir = cfg.common.working_dir/ cfg.common.project_name
    cfg.common.results_dir = cfg.common.results_dir / cfg.common.project_name
    
    cfg.common.logger = setup_logger(cfg.common.working_dir / "run.log")
    cfg.common.manifest = Manifest(cfg.common.working_dir / "manifest.json")
    cfg.common.runstate = State(cfg.common.working_dir / "state.json") 

    return cfg
