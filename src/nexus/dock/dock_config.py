from pydantic import BaseModel, ConfigDict, model_validator, Field
from typing import Literal, Optional, Union, List, Annotated
from pathlib import Path


class CommonConfig(BaseModel):
    job_name: Optional[str] = "docking"
    output_dir: Optional[Path] = Path.cwd() / "results"

    padding: Optional[float] = 5.0
    n_jobs: Optional[int] = 1
    max_poses: Optional[int] = 8


class ReceptorsConfig(BaseModel):
    source: Path = None
    suffix: Optional[str] = ".pdb"

    pocket_option: Literal["selection", "reference"] = "selection"
    selection: Optional[Union[Path, str]] = None
    reference: Optional[Path] = None
    reference_suffix: Optional[str] = "_pocket.pdb"


class LigandsConfig(BaseModel):
    source: Path = None
    suffix: Optional[str] = ".sdf"


class VinaConfig(BaseModel):
    program: Literal["vina"]
    exhaustiveness: Optional[int] = 32
    num_modes: Optional[int] = 8

class DOCK6Config(BaseModel):
    program: Literal["dock6"]
    max_orientations: Optional[int] = 1000
    radius: Optional[float] = 10.0
    num_poses: Optional[int] = 8

EngineConfig = Annotated[
    Union[VinaConfig, DOCK6Config],
    Field(discriminator="program")
]

class MetadataConfig(BaseModel):
    model_config = ConfigDict(extra="allow")


class DockConfig(BaseModel):
    common: CommonConfig = Field(default_factory=CommonConfig)
    receptors: ReceptorsConfig = Field(default_factory=ReceptorsConfig)
    ligands: LigandsConfig = Field(default_factory=LigandsConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    engine: EngineConfig

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def run_setup(self) -> "DockConfig":
        _find_files(self)
        _validate_and_normalize_receptors(self)
        return self


def _find_files(cfg: DockConfig):
    from nexus.core.utils.extract_files import extract_files
    
    if ".pdb" not in cfg.receptors.suffix and ".cif" not in cfg.receptors.suffix:
        raise ValueError("Input receptor suffix must have 'pdb' or 'cif'.")

    receptors_source = cfg.receptors.source
    cfg.receptors.source = extract_files(cfg.receptors.source, cfg.receptors.suffix)
    if not cfg.receptors.source:
        raise ValueError(f"No receptor with '{cfg.receptors.suffix}' found in  {receptors_source}.")
        
    if cfg.receptors.reference is not None:
        cfg.receptors.reference = extract_files(cfg.receptors.reference, cfg.receptors.reference_suffix)

    ligands_source = cfg.ligands.source
    cfg.ligands.source = extract_files(cfg.ligands.source, cfg.ligands.suffix)
    if not cfg.ligands.source:
        raise ValueError(f"No ligand with '{cfg.ligands.suffix}' found in  {ligands_source}.")


from dataclasses import dataclass


@dataclass
class ReceptorConfigBundle:
    """Bundle containing a receptor and its resolved selection/reference."""
    receptor: Path
    name: str
    selection_string: Optional[str] = None
    reference_path: Optional[Path] = None


def _validate_and_normalize_receptors(cfg: DockConfig) -> List[ReceptorConfigBundle]:
    """
    Validate and normalize receptor-related fields on `cfg` (RootConfig).
    Returns a list of ReceptorConfigBundle objects with resolved selection strings and reference paths.
    """
    receptors = cfg.receptors.source
    pocket_option = cfg.receptors.pocket_option
    bundles: List[ReceptorConfigBundle] = []

    # Handle reference-based pockets: either a single global reference or per-receptor references
    if pocket_option == "reference":
        references = sorted(cfg.receptors.reference)
        if not references:
            raise FileNotFoundError(f"pocket_option is 'reference' but no reference pockets found/provided (expected suffix {reference_suffix})")

        if len(receptors) == 1 and len(references) > 1:
            raise ValueError("Single receptor provided but multiple reference pocket files provided; provide a single reference file or use selection option.")

        if len(references) == 1:
            # Single global reference for all receptors
            for rec in receptors:
                bundles.append(ReceptorConfigBundle(receptor=rec, name=rec.stem, reference_path=references[0]))
        else:
            # Multiple references: match by base name and attach per-receptor reference paths
            reference_suffix = cfg.receptors.reference_suffix
            ref_map = match_references_to_receptors(receptors, references, reference_suffix)
            for rec in receptors:
                bundles.append(ReceptorConfigBundle(receptor=rec, name=rec.stem, reference_path=ref_map[rec]))

    # Handle selection-based pockets: either a global selection string or a per-receptor CSV mapping
    elif pocket_option == "selection":
        sel = cfg.receptors.selection
        if sel is None:
            raise ValueError("pocket_option is 'selection' but no selection provided in config")

        # If the provided selection refers to an existing CSV file, parse it now (at config time)
        sel_path = Path(sel) if isinstance(sel, (str, Path)) and Path(sel).exists() else None
        if sel_path and sel_path.suffix.lower() == ".csv":
            if len(receptors) == 1:
                raise ValueError("A per-receptor selection CSV was provided but only a single receptor file was given; provide a single selection string instead.")
            selection_map = parse_selection_csv(sel_path)
            for rec in receptors:
                sel_str = selection_map.get(rec.stem)
                if sel_str is None:
                    raise KeyError(f"No selection string found in CSV for receptor {rec.stem}")
                bundles.append(ReceptorConfigBundle(receptor=rec, name=rec.stem, selection_string=sel_str))
        else:
            # Global selection string for all receptors
            global_sel = str(sel)
            for rec in receptors:
                bundles.append(ReceptorConfigBundle(receptor=rec, name=rec.stem, selection_string=global_sel))

    else:
        raise ValueError(f"Unknown pocket_option: {pocket_option}")

    # Attach normalized receptor list and the built bundles to the cfg object so downstream code
    try:
        setattr(cfg.receptors, "bundles", bundles)
    except Exception:
        # As a fallback, set attribute directly (pydantic models allow attribute assignment post-creation)
        cfg.receptors.__dict__["bundles"] = bundles

    return bundles

import csv

def parse_selection_csv(csv_path: Path) -> dict:
    mapping = {}
    with open(csv_path, newline='') as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                raise ValueError(f"Invalid selection CSV row: {row}")
            name = row[0].strip()
            sel = row[1].strip()
            mapping[name] = sel
    return mapping


def match_references_to_receptors(receptors: List[Path], references: List[Path], reference_suffix: str) -> dict:
    """Match receptor files to reference pocket files by base name.
    Receptor 'X_protein.cif' matches reference 'X{reference_suffix}' (e.g., 'X_pocket.cif').
    """
    ref_map = {}
    for rec in receptors:
        base = rec.stem.split("_")[0]
        expected = f"{base}{reference_suffix}"
        matched = [r for r in references if r.name == expected]
        if not matched:
            raise FileNotFoundError(f"No reference pocket found for receptor {rec} expected name {expected}")
        ref_map[rec] = matched[0]
    return ref_map
