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


from pathlib import Path
from rdkit import Chem

def _load_sdf(file_path):
    name = Path(file_path).stem

    with open(file_path, 'rb') as f:
        # Set sanitize=False to allow the 'broken' molecule to load
        supplier = Chem.ForwardSDMolSupplier(f, sanitize=False)
        
        for mol in supplier:
            if mol is not None:
                # 1. Update property cache so RDKit knows the valency 
                # (Essential before adding Hs)
                mol.UpdatePropertyCache(strict=False)
                
                # 2. Strip queries as you were doing
                clean_mol = _strip_queries(mol)
                
                # 3. Manually sanitize except for Kekulization
                # This fixes the structure enough for Meeko to work
                Chem.SanitizeMol(clean_mol, 
                                 Chem.SanitizeFlags.SANITIZE_ALL ^ 
                                 Chem.SanitizeFlags.SANITIZE_KEKULIZE)
                
                # 4. Add Hydrogens - usually safer with addCoords=True for docking
                mol_with_h = Chem.AddHs(clean_mol, addCoords=True)
                
                return mol_with_h, name
            else:
                raise ValueError(f"Warning: A molecule could not be read in {file_path}")