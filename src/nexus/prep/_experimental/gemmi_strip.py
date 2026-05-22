# 3. Clean Receptor via Gemmi
import os
import gemmi
from pathlib import Path
from nexus.fetch.fetch_config import FetchConfig

STANDARD_AMINO_ACIDS = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE", 
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL"
}

# A list of legal alphanumeric characters for standard mmCIF/PDB chain IDs
LEGAL_CHAIN_IDS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def gemmi_strip(fcfg: FetchConfig, retrieved_path: Path, id: str):
    stripped_suffix = fcfg.stripped_suffix
    remove_waters = fcfg.remove_waters
    kept_residues = fcfg.kept_residues
    output_dir = fcfg.output_dir

    if stripped_suffix == "":
        stripped_path = os.path.join(output_dir, f"{id}.cif")
    else:
        stripped_path = os.path.join(output_dir, f"{id}_{stripped_suffix}.cif")

    doc = gemmi.cif.read_file(retrieved_path)

    st = gemmi.make_structure_from_block(doc.sole_block())
    if remove_waters:
        st.remove_waters()

    removed_ligands = set()
    KEPT_RESIDUES = [i.upper() for i in kept_residues] # Moved outside the loop for efficiency

    for model in st:
        for chain in model:
            # Loop backwards to safely delete items while iterating
            for i in reversed(range(len(chain))):
                res_name = chain[i].name.upper()

                # Non-standard residues and covalently attached ligands are removed here
                if res_name not in STANDARD_AMINO_ACIDS and res_name not in KEPT_RESIDUES:
                    removed_ligands.add(res_name)
                    del chain[i]
        for idx, chain in enumerate(model):
            # Assign a sequential single character if possible, fallback to custom naming if extremely large
            if idx < len(LEGAL_CHAIN_IDS):
                chain.name = LEGAL_CHAIN_IDS[idx]
            else:
                chain.name = f"C{idx}"

    st.make_mmcif_document().write_file(stripped_path)
    
    if removed_ligands:
        print(f"✂️  Stripped structural components/ligands: {removed_ligands}")

    if KEPT_RESIDUES:
        str_kept_residues = ", ".join(KEPT_RESIDUES)
        print(f"❗ Non-standard residues kept: {str_kept_residues}")

    print(f"✅ Saved stripped biological assembly receptor to mmCIF with clean chain IDs -> {stripped_path}")

    return stripped_path