from compdd.configs.root_config import RootConfig, _setup_dirs
from compdd.configs.config_helpers import validate_and_normalize_receptors
from compdd.utils.extract_files import extract_files
from pathlib import Path


def load_validation_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    cfg = RootConfig.model_validate(data)

    data = Path(cfg.validation.data)
    pdbs = extract_files(data, "_protein.pdb", recursive=True)
    reference = extract_files(data, "_pocket.pdb", recursive=True)
    sdfs = extract_files(data, "_ligand.sdf", recursive=True)

    cfg.receptors.source = "pdb"
    cfg.receptors.pdbs = pdbs
    cfg.receptors.pocket_option = "reference"
    cfg.receptors.reference = reference

    cfg.ligands.source = "sdf"
    cfg.ligands.sdfs = sdfs
    cfg.ligands.output_dir = cfg.common.working_dir

    cfg.common.mode = "match"

    cfg = _setup_dirs(cfg)

    validate_and_normalize_receptors(cfg, cfg.receptors.reference_suffix)

    return cfg
