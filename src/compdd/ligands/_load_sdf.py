from pathlib import Path
from rdkit import Chem

from compdd.utils.extract_files import extract_files

def _load_sdf(input_inputs):
    final_file_list = extract_files(input_inputs, ".sdf")
    mol_with_h_list = []
    names = []
    for file_path in final_file_list:
        name = Path(file_path).stem
        names.append(name)
        with open(file_path, 'rb') as f:
            supplier = Chem.ForwardSDMolSupplier(f)
            for mol in supplier:
                if mol is not None:
                    mol_with_h = Chem.AddHs(mol)
                    mol_with_h_list.append(mol_with_h)
                else:
                    print(f"Warning: A molecule could not be read in {file_path}")
    
    return mol_with_h_list, names
