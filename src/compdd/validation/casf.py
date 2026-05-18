from dataclasses import dataclass
from pathlib import Path
from collections import Counter


class UnsupportedLigandError(ValueError):
    pass


@dataclass(frozen=True)
class CASFEntry:
    entry_id: str
    entry_dir: Path
    receptor_pdb: Path
    pocket_pdb: Path
    crystal_ligand_mol2: Path
    crystal_ligand_sdf: Path | None = None


def discover_casf_entries(validation_data):
    root = Path(validation_data)
    if not root.is_dir():
        raise FileNotFoundError(f"Validation data directory not found: {root}")

    entries = []
    for entry_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        entry_id = entry_dir.name.lower()
        receptor = entry_dir / f"{entry_id}_protein.pdb"
        pocket = entry_dir / f"{entry_id}_pocket.pdb"
        ligand = entry_dir / f"{entry_id}_ligand.mol2"
        if not (receptor.is_file() and pocket.is_file() and ligand.is_file()):
            continue
        ligand_sdf = entry_dir / f"{entry_id}_ligand.sdf"
        entries.append(CASFEntry(
            entry_id=entry_id,
            entry_dir=entry_dir,
            receptor_pdb=receptor,
            pocket_pdb=pocket,
            crystal_ligand_mol2=ligand,
            crystal_ligand_sdf=ligand_sdf if ligand_sdf.is_file() else None,
        ))

    if not entries:
        raise FileNotFoundError(f"No CASF entry folders found under: {root}")
    return entries


def parse_mol2_ligand_id(mol2_path):
    mol2_path = Path(mol2_path)
    in_atoms = False
    residue_names = []

    with open(mol2_path) as handle:
        for line in handle:
            stripped = line.strip()
            if stripped == "@<TRIPOS>ATOM":
                in_atoms = True
                continue
            if stripped.startswith("@<TRIPOS>") and in_atoms:
                break
            if not in_atoms or not stripped:
                continue

            parts = stripped.split()
            if len(parts) >= 8:
                residue_names.append(parts[7])

    counts = Counter(residue_names)
    ligand_ids = sorted(name for name in counts if name and name.upper() not in {"MOL", "UNK", "UNL"})
    if not ligand_ids:
        raise UnsupportedLigandError("Crystal ligand has no clear CCD residue name")
    if len(ligand_ids) != 1:
        raise UnsupportedLigandError(f"Crystal ligand has ambiguous residue names: {', '.join(ligand_ids)}")
    return ligand_ids[0].upper()
