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
    mode: Optional[Literal["mix", "match"]] = "mix"

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
    source: Optional[Literal["cif", "pdb", "existing"]] = "cif"

    cifs: Optional[Path | list[Path]] = None
    pdbs: Optional[Path | list[Path]] = None

    pocket_option: Literal["selection", "reference"] = "selection"
    selection: Optional[Path | str] = None
    reference: Optional[Path] = None
    reference_suffix : str = "_pocket.cif"

    existing_dir: Optional[Path] = None


class LigandsConfig(BaseModel):
    source: Literal["smiles", "sdf","existing"] = "smiles"

    smiles_csv: Optional[Path] = None
    sdfs: Optional[list[Path] | Path] = None
    output_dir : Optional[Path] = None
    existing_dir: Optional[Path] = None


class ValidationConfig(BaseModel):
    data: Optional[Path] = None


class RootConfig(BaseModel):
    libs: LibsConfig
    common: CommonConfig
    vina: VinaConfig
    dock6: DOCK6Config
    receptors: ReceptorsConfig
    ligands: LigandsConfig
    validation: ValidationConfig


def _setup_dirs(cfg: RootConfig):
    from compdd.utils.logging_utils import setup_logger
    from compdd.utils.manifest import Manifest
    from compdd.utils.runstate import State

    for subcfg_name in RootConfig.model_fields:
        subcfg = getattr(cfg, subcfg_name)
        for field_name in subcfg.__class__.model_fields:
            value = getattr(subcfg, field_name)
            if isinstance(value, Path):
                expanded_path = Path(os.path.expandvars(str(value))).expanduser()
                setattr(subcfg, field_name, expanded_path)

    cfg.common.working_dir = cfg.common.working_dir/ cfg.common.project_name
    cfg.common.results_dir = cfg.common.results_dir / cfg.common.project_name
    cfg.ligands.output_dir = cfg.ligands.output_dir / cfg.common.project_name

    cfg.common.logger = setup_logger(cfg.common.working_dir / "run.log")
    cfg.common.manifest = Manifest(cfg.common.working_dir / "manifest.json")
    cfg.common.runstate = State(cfg.common.working_dir / "state.json") 

    return cfg


def _find_files(cfg: RootConfig):
    from compdd.utils.extract_files import extract_files
    if cfg.receptors.source == "cif":
        cfg.receptors.cifs = extract_files(cfg.receptors.cifs, ".cif")
    elif cfg.receptors.source == "pdb":
        cfg.receptors.pdbs = extract_files(cfg.receptors.pdbs, ".pdb")
        
    if cfg.receptors.reference == "reference":
        cfg.receptors.reference = extract_files(cfg.receptors.reference, cfg.receptors.reference_suffix)

    if cfg.ligands.source == "sdf":
        cfg.ligands.sdfs = extract_files(cfg.ligands.sdfs, ".sdf")

    return cfg



def load_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = RootConfig.model_validate(data)

    cfg = _setup_dirs(cfg)
    cfg = _find_files(cfg)

    # Validate and normalize receptor-related configuration (selection/reference semantics)
    from compdd.configs.config_helpers import validate_and_normalize_receptors
    validate_and_normalize_receptors(cfg, cfg.receptors.reference_suffix)

    return cfg
