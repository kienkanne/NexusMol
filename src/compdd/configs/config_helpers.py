from pathlib import Path
import csv
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ReceptorConfigBundle:
    """Bundle containing a receptor and its resolved selection/reference."""
    receptor: Path
    name: str
    selection_string: Optional[str] = None
    reference_path: Optional[Path] = None


def validate_and_normalize_receptors(cfg, reference_suffix: str = "_pocket.cif") -> List[ReceptorConfigBundle]:
    """
    Validate and normalize receptor-related fields on `cfg` (RootConfig).
    Returns a list of ReceptorConfigBundle objects with resolved selection strings and reference paths.
    """

    if cfg.receptors.source == "cif":
        receptors = sorted(cfg.receptors.cifs)
    elif cfg.receptors.source == "pdb":
        receptors = sorted(cfg.receptors.pdbs)

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
