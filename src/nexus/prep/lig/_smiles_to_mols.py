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


from rdkit import Chem
from rdkit.Chem import AllChem

def _rdkit_gen3d(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")

    mol_with_h = Chem.AddHs(mol)

    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    embed_status = AllChem.EmbedMolecule(mol_with_h, params)
    if embed_status == -1:
        raise RuntimeError(f"3D embedding failed for SMILES: {smiles}")

    props = AllChem.MMFFGetMoleculeProperties(mol_with_h)
    if props is not None:
        force_field = AllChem.MMFFGetMoleculeForceField(mol_with_h, props)
    else:
        force_field = AllChem.UFFGetMoleculeForceField(mol_with_h)

    if force_field is None:
        raise RuntimeError(f"Force field setup failed for SMILES: {smiles}")

    force_field.Initialize()
    force_field.Minimize(maxIts=500)

    return mol_with_h


from functools import partial
from nexus.core.executors.python_parallel import python_parallel


def _smiles_to_mols(csv_path, n_jobs):
    smiles_list, names = _parse_ligands_csv(csv_path)

    tasks = []
    for smiles in smiles_list:
        tasks.append(partial(_rdkit_gen3d, smiles))

    with python_parallel(tasks, n_jobs, "parallel_rdkit_gen3d()", skip=True) as mol_with_h_list:
        pass
    
    return mol_with_h_list, names
