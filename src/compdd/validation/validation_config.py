from compdd.configs.docking_config import RootConfig, load_config

def load_validation_config(path):
    cfg = load_config(path)

    cfg.receptors.source = "pdb"
    cfg.receptors.pdbs = "this"
    cfg.receptors.pocket_option = "reference"
    cfg.receptors.reference = "this"

    cfg.ligands.source = "sdf"
    cfg.ligands.sdfs = "this"
    cfg.ligands.output_dir = cfg.common.working_dir

"""class ReceptorsConfig(BaseModel):
    source: Optional[Literal["pdb", "existing"]] = "pdb"

    pdbs: list[Path] | Path | None = None
    pocket_option: Literal["selection", "reference"] = "selection"
    selection: Optional[str] = None
    reference: Optional[Path] = None

    existing_dir: Optional[Path] = None


class LigandsConfig(BaseModel):
    source: Literal["smiles", "sdf","existing"] = "smiles"

    smiles_csv: Optional[Path] = None
    sdfs: list[Path] | Path | None = None
    output_dir : Optional[Path] = None
    existing_dir: Optional[Path] = None"""