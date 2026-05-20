from pathlib import Path
from rdkit import Chem

def _strip_queries(mol):
    """Rebuilds an RDKit molecule from scratch to drop all query features."""
    clean_mol = Chem.RWMol()
    
    # 1. Copy atoms without query features
    for atom in mol.GetAtoms():
        new_atom = Chem.Atom(atom.GetSymbol())
        new_atom.SetFormalCharge(atom.GetFormalCharge())
        new_atom.SetIsAromatic(atom.GetIsAromatic())
        clean_mol.AddAtom(new_atom)
        
    # 2. Copy bonds
    for bond in mol.GetBonds():
        clean_mol.AddBond(
            bond.GetBeginAtomIdx(), 
            bond.GetEndAtomIdx(), 
            bond.GetBondType()
        )
        
    # 3. Explicitly copy 3D coordinates
    if mol.GetNumConformers() > 0:
        old_conf = mol.GetConformer()
        new_conf = Chem.Conformer(mol.GetNumAtoms())
        for i in range(mol.GetNumAtoms()):
            new_conf.SetAtomPosition(i, old_conf.GetAtomPosition(i))
        clean_mol.AddConformer(new_conf)
        
    # 4. Finalize the structure
    Chem.SanitizeMol(clean_mol)
    return clean_mol


def _load_sdf(file_path):
    name = Path(file_path).stem

    with open(file_path, 'rb') as f:
        supplier = Chem.ForwardSDMolSupplier(f)
        for mol in supplier:
            if mol is not None:
                # Strip queries to appease Meeko
                clean_mol = _strip_queries(mol)
                
                # Now it is safe to add Hs
                mol_with_h = Chem.AddHs(clean_mol, addCoords=True)
            else:
                raise ValueError(f"Warning: A molecule could not be read in {file_path}")
    
    return mol_with_h, name
