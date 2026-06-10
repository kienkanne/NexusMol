from pathlib import Path
from pydantic import BaseModel
import yaml
import os


def load_config(cfg_class: BaseModel, path: Path):
    """Unified YAML config loader. Validate the config based on the given BaseModel class, 
    attach the global config to the object, and append `job_name` to output_dir and scratch_dir."""
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg = cfg_class.model_validate(cfg)

    from nexus.config import load_global_config
    setattr(cfg, "_global", load_global_config())

    cfg = expand_paths(cfg)

    try:
        job_name = getattr(cfg.common, "job_name")

        cfg.common.output_dir = setup_dir(cfg.common.output_dir, job_name)

        if cfg._global.path.scratch_dir is None:
            raise ValueError("Scratch directory is not yet specified in config file.")    
        cfg._global.path.scratch_dir = setup_dir(cfg._global.path.scratch_dir, job_name)

        from nexus.core.trackers.main_tracker import setup_context
        setup_context(cfg._global.path.scratch_dir, cfg.common.job_name)

    except:
        # Prep or fetch configs is simple, so "job_name" is not included and setting up directories is not needed.
        pass
    
    return cfg


def setup_dir(path, name):
    path_name = Path(path / name)
    path_name.mkdir(parents=True, exist_ok=True)

    return path_name


def expand_paths(model: BaseModel) -> BaseModel:
    """
    Recursively traverses a Pydantic model to find Path attributes
    and expands environment variables and user shortcuts (~).
    """
    updated_data = {}

    for field_name in type(model).model_fields:
        value = getattr(model, field_name)

        if isinstance(value, Path):
            expanded_str = os.path.expandvars(str(value))
            updated_data[field_name] = Path(expanded_str).expanduser()
            
        elif isinstance(value, BaseModel):
            updated_data[field_name] = expand_paths(value)
            
        elif isinstance(value, (list, tuple)):
            updated_data[field_name] = [
                expand_paths(item) if isinstance(item, BaseModel) else item 
                for item in value
            ]

        else:
            updated_data[field_name] = value

    # Return a new copy of the model with the updated fields
    return model.model_copy(update=updated_data)
