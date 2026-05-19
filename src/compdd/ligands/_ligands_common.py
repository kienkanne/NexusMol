from pathlib import Path
import csv
import re


def _sanitize_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    sanitized = sanitized.strip("._-")
    if not sanitized:
        raise ValueError(f"Invalid ligand name {name!r}")
    return sanitized


def _parse_ligands_csv(csv_path):
    if not csv_path.exists():
        raise FileNotFoundError(f"Ligand CSV not found: {csv_path}")

    seen_smiles = set()
    seen_names = set()
    smiles_list = []
    names = []

    with open(csv_path, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["smiles", "name"]:
            raise ValueError("Ligand CSV must have exactly this header: smiles,name")

        for row_number, row in enumerate(reader, start=2):
            smiles = (row.get("smiles") or "").strip()
            raw_name = (row.get("name") or "").strip()
            if not smiles or not raw_name:
                raise ValueError(f"Ligand CSV row {row_number} must include smiles and name")

            name = _sanitize_name(raw_name)

            if smiles in seen_smiles:
                raise ValueError(f"Duplicate smiles: {smiles!r}")
            seen_smiles.add(smiles)

            if name in seen_names:
                raise ValueError(f"Duplicate ligand name after sanitization: {raw_name!r}")
            seen_names.add(name)

            smiles_list.append(smiles)
            names.append(name)

    if not smiles_list:
        raise ValueError(f"Ligand CSV contains no ligands: {csv_path}")

    return smiles_list, names


def _ligand_extension(program):
    if program == "vina":
        return ".pdbqt"
    if program == "dock6":
        return ".mol2"
    raise ValueError(f"Unsupported docking program: {program}")



def _prepared_path(directory, name, prepared_suffix, extension):
    def _prepared_filename(name, prepared_suffix, extension):
        if not extension.startswith("."):
            extension = f".{extension}"
        return f"{name}_{prepared_suffix}{extension}"
    
    return Path(directory) / _prepared_filename(name, prepared_suffix, extension)


def _strip_prepared_suffix(path, prepared_suffix):
    stem = Path(path).stem
    marker = f"_{prepared_suffix}"
    if stem.endswith(marker):
        return stem[: -len(marker)]
    return stem


def _discover_prepared_ligands(cfg):
    existing_dir = cfg.ligands.existing_dir
    if not existing_dir.is_dir():
        raise FileNotFoundError(f"Ligand directory not found: {existing_dir}")

    extension = _ligand_extension(cfg.common.program)
    pattern = f"*_{cfg.common.prepared_suffix}{extension}"
    ligands = sorted(existing_dir.glob(pattern))

    if not ligands:
        raise FileNotFoundError(f"No prepared ligand files matched {existing_dir / pattern}")
    if ligands is None:
        raise ValueError("ngu")

    return ligands
