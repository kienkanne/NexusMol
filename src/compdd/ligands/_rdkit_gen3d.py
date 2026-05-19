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