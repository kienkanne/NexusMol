from pdbfixer import PDBFixer

# 1. Load the protein (can be a local file or a 4-letter PDB ID)
# To load a local file: fixer = PDBFixer(filename='your_protein.pdb')
fixer = PDBFixer(filename="/localscratch/kbui/NexusMol/data/my_receptors_ligands/8C9V_fixed.pdb")  # Example using a PDB ID

# 2. Find the missing residues
fixer.findMissingResidues()

# 3. List and print them out using original PDB numbering
if not fixer.missingResidues:
    print("No missing residues found!")
else:
    print(f"{'Chain':<6} | {'Insertion Context (Original PDB Numbers)':<42} | {'Residues to Add'}")
    print("-" * 90)
    
    chains = list(fixer.topology.chains())
    
    for (chain_idx, res_idx), res_names in fixer.missingResidues.items():
        chain = chains[chain_idx]
        chain_id = chain.id
        residues = list(chain.residues())
        
        # Determine the human-readable PDB numbering context
        if res_idx == 0:
            # N-terminus gap: happens BEFORE the first existing residue
            next_res_pdb_id = residues[0].id
            context = f"Before Seq Start (Preceding PDB #{next_res_pdb_id})"
        elif res_idx >= len(residues):
            # C-terminus gap: happens AFTER the last existing residue
            prev_res_pdb_id = residues[-1].id
            context = f"After Seq End (Following PDB #{prev_res_pdb_id})"
        else:
            # Internal gap: happens between two existing residues
            prev_res_pdb_id = residues[res_idx - 1].id
            next_res_pdb_id = residues[res_idx].id
            context = f"Between PDB #{prev_res_pdb_id} and PDB #{next_res_pdb_id}"
            
        res_list_str = ", ".join(res_names)
        print(f"{chain_id:<6} | {context:<42} | {res_list_str}")