from pathlib import Path
from typing import Literal, Optional
import os

from pydantic import BaseModel, ConfigDict, model_validator

from compdd.configs.docking_config import DOCK6Config, LibsConfig, VinaConfig


def _expand_path(path):
    return Path(os.path.expandvars(str(path))).expanduser()


class ValidationCommonConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_name: str
    working_dir: Path
    results_dir: Path
    validation_data: Path
    prepare_tool: Literal["obabel", "meeko"] = "meeko"

    num_analysis: int = 3
    prepared_suffix: str = "prepped"
    pocket_option: Literal["selection", "reference"] = "reference"
    pocket_selection: Optional[str] = None
    reference: Optional[Path] = None

    padding: float = 6.0
    n_jobs: int = 1
    max_poses: int = 16

    @model_validator(mode="after")
    def validate_fields(self):
        if self.num_analysis < 1:
            raise ValueError("num_analysis must be at least 1")
        if self.n_jobs < 1:
            raise ValueError("n_jobs must be at least 1")
        return self


class ValidationConfig(BaseModel):
    libs: LibsConfig
    common: ValidationCommonConfig
    vina: VinaConfig = VinaConfig()
    dock6: DOCK6Config = DOCK6Config()


def load_validation_config(path):
    import yaml

    with open(path) as handle:
        data = yaml.safe_load(handle)

    cfg = ValidationConfig.model_validate(data)
    cfg.common.working_dir = _expand_path(cfg.common.working_dir) / cfg.common.project_name
    cfg.common.results_dir = _expand_path(cfg.common.results_dir) / cfg.common.project_name
    cfg.common.validation_data = _expand_path(cfg.common.validation_data)
    if cfg.common.reference is not None:
        cfg.common.reference = _expand_path(cfg.common.reference)

    for field_name in LibsConfig.model_fields:
        setattr(cfg.libs, field_name, _expand_path(getattr(cfg.libs, field_name)))

    return cfg
