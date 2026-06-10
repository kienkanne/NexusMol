import os
from pathlib import Path
from typing import Optional, Tuple, Dict

from pydantic import BaseModel, field_validator
import platformdirs
import yaml


class SoftwareConfig(BaseModel):
    chimerax: Optional[Path] = None
    chimera: Optional[Path] = None
    dock6: Optional[Path] = None


class PathConfig(BaseModel):
    scratch_dir: Optional[Path] = "/localscratch/$USER"

    @field_validator("scratch_dir", mode="before")
    @classmethod
    def expand_env_vars(cls, v):
        if isinstance(v, str):
            return os.path.expandvars(v)
        return v

class GlobalConfig(BaseModel):
    software: SoftwareConfig = SoftwareConfig()
    path: PathConfig = PathConfig()


def get_global_config_path() -> Path:
    """Return the path to the global nexus config file."""
    cfg_dir = Path(platformdirs.user_config_dir("nexus"))
    return cfg_dir / "config.yaml"


def load_global_config(path: Optional[Path] = None) -> GlobalConfig:
    """Load and validate the global config file. If missing, return defaults."""
    cfg_path = Path(path) if path else get_global_config_path()
    if not cfg_path.exists():
        return GlobalConfig()

    with open(cfg_path) as fh:
        data = yaml.safe_load(fh)
        
    if not isinstance(data, dict):
        data = {}

    return GlobalConfig.model_validate(data)


def save_global_config(cfg: GlobalConfig, path: Optional[Path] = None, force: bool = False) -> Path:
    """Save the current GlobalConfig state to the YAML file."""
    cfg_path = Path(path) if path else get_global_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    
    if cfg_path.exists() and not force:
        return cfg_path

    data = cfg.model_dump(mode="json")
    
    with open(cfg_path, "w") as fh:
        yaml.safe_dump(data, fh)
    return cfg_path


def write_default_config(path: Optional[Path] = None, force: bool = False) -> Path:
    """Create a default config file based dynamically on GlobalConfig defaults."""
    return save_global_config(GlobalConfig(), path=path, force=force)

def validate_global_config(path: Optional[Path] = None) -> Tuple[Dict[str, str], bool]:
    """Dynamically validate all configured paths across ALL sub-configs."""
    cfg = load_global_config(path)
    results = {}
    has_missing = False

    for section_name in GlobalConfig.model_fields.keys():
        sub_config = getattr(cfg, section_name)
        if isinstance(sub_config, BaseModel):
            for field_name, value in sub_config:
                if isinstance(value, Path):
                    if value.exists():
                        results[f"{section_name}.{field_name}"] = "OK"
                    else:
                        results[f"{section_name}.{field_name}"] = "Missing path"
                        has_missing = True
                elif value is None:
                    results[f"{section_name}.{field_name}"] = "Not configured"
                    
    return results, has_missing
