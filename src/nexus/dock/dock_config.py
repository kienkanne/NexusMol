from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional, Union, List
from pathlib import Path
import os


class LibsConfig(BaseModel):
    chimerax: Path
    chimera: Path

    dock_home: Path


class CommonConfig(BaseModel):
    model_config = ConfigDict(extra='allow')

    project_name: str
    working_dir: Path
    results_dir: Path

    padding: Optional[float] = 5.0
    n_jobs: int = 1
    max_poses: int = 8

    mode: Optional[Literal["mix", "match"]] = "mix"
    program: Optional[Literal["vina", "dock6"]] = None


class ReceptorsConfig(BaseModel):
    source: Optional[Path] = None
    suffix: Optional[str] = ".pdb"

    pocket_option: Literal["selection", "reference"] = "selection"
    selection: Optional[Union[Path, str]] = None
    reference: Optional[Path] = None
    reference_suffix: Optional[str] = "_pocket.pdb"


class LigandsConfig(BaseModel):
    source: Optional[Path] = None
    suffix: Optional[str] = ".sdf"

class VinaConfig(BaseModel):
    exhaustiveness: Optional[int] = 32
    num_modes: Optional[int] = 8


class DOCK6Config(BaseModel):
    max_orientations: float = 1000
    radius: Optional[float] = 10.0


class ValidationConfig(BaseModel):
    data: Optional[Path] = None
    protein_suffix: Optional[str] = "_protein.pdb"
    pocket_suffix: Optional[str] = "_pocket.pdb"
    ligand_suffix: Optional[str] = "_ligand.sdf"


class DockConfig(BaseModel):
    libs: LibsConfig
    common: CommonConfig
    vina: VinaConfig
    dock6: DOCK6Config
    receptors: ReceptorsConfig
    ligands: LigandsConfig
    validation: ValidationConfig


def load_dock_config(path):
    import yaml
    with open(path) as f:
        data = yaml.safe_load(f)
    dcfg = DockConfig.model_validate(data)

    dcfg = _setup_dirs(dcfg)
    dcfg = _find_files(dcfg)

    # Validate and normalize receptor-related configuration (selection/reference semantics)
    validate_and_normalize_receptors(dcfg, dcfg.receptors.reference_suffix)

    return dcfg


def _find_files(dcfg: DockConfig):
    from nexus.core.extract_files import extract_files
    
    if ".pdb" not in dcfg.receptors.suffix and ".cif" not in dcfg.receptors.suffix:
        raise ValueError("Input receptor suffix must have 'pdb' or 'cif'.")

    receptors_source = dcfg.receptors.source
    dcfg.receptors.source = extract_files(dcfg.receptors.source, dcfg.receptors.suffix)
    if not dcfg.receptors.source:
        raise ValueError(f"No receptor with '{dcfg.receptors.suffix}' found in  {receptors_source}.")
        
    if dcfg.receptors.reference is not None:
        dcfg.receptors.reference = extract_files(dcfg.receptors.reference, dcfg.receptors.reference_suffix)

    ligands_source = dcfg.ligands.source
    dcfg.ligands.source = extract_files(dcfg.ligands.source, dcfg.ligands.suffix)
    if not dcfg.ligands.source:
        raise ValueError(f"No ligand with '{dcfg.ligands.suffix}' found in  {ligands_source}.")
    return dcfg


def _setup_dirs(dcfg: DockConfig):
    from nexus.core.trackers.logging_utils import setup_logger
    from nexus.core.trackers.manifest import Manifest
    from nexus.core.trackers.runstate import State

    for subcfg_name in DockConfig.model_fields:
        subcfg = getattr(dcfg, subcfg_name)
        for field_name in subcfg.__class__.model_fields:
            value = getattr(subcfg, field_name)
            if isinstance(value, Path):
                expanded_path = Path(os.path.expandvars(str(value))).expanduser()
                setattr(subcfg, field_name, expanded_path)

    dcfg.common.working_dir = dcfg.common.working_dir/ dcfg.common.project_name
    dcfg.common.results_dir = dcfg.common.results_dir / dcfg.common.project_name

    setattr(dcfg.common, "logger", setup_logger(dcfg.common.working_dir / "run.log"))
    setattr(dcfg.common, "manifest", Manifest(dcfg.common.working_dir / "manifest.json"))
    setattr(dcfg.common, "runstate", State(dcfg.common.working_dir / "state.json") )

    return dcfg


from dataclasses import dataclass

@dataclass
class ReceptorConfigBundle:
    """Bundle containing a receptor and its resolved selection/reference."""
    receptor: Path
    name: str
    selection_string: Optional[str] = None
    reference_path: Optional[Path] = None


def validate_and_normalize_receptors(dcfg: DockConfig, reference_suffix: str = "_pocket.cif") -> List[ReceptorConfigBundle]:
    """
    Validate and normalize receptor-related fields on `dcfg` (RootConfig).
    Returns a list of ReceptorConfigBundle objects with resolved selection strings and reference paths.
    """
    receptors = dcfg.receptors.source
    pocket_option = dcfg.receptors.pocket_option
    bundles: List[ReceptorConfigBundle] = []

    # Handle reference-based pockets: either a single global reference or per-receptor references
    if pocket_option == "reference":
        references = sorted(dcfg.receptors.reference)
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
            ref_map = match_references_to_receptors(receptors, references, reference_suffix)
            for rec in receptors:
                bundles.append(ReceptorConfigBundle(receptor=rec, name=rec.stem, reference_path=ref_map[rec]))

    # Handle selection-based pockets: either a global selection string or a per-receptor CSV mapping
    elif pocket_option == "selection":
        sel = dcfg.receptors.selection
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

    # Attach normalized receptor list and the built bundles to the dcfg object so downstream code
    try:
        setattr(dcfg.receptors, "bundles", bundles)
    except Exception:
        # As a fallback, set attribute directly (pydantic models allow attribute assignment post-creation)
        dcfg.receptors.__dict__["bundles"] = bundles

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
