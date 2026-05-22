from chimerax.core.commands import run

# Define your legal chain IDs (A-Z, a-z, etc.)
LEGAL_CHAIN_IDS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def _run(session, input_file, cleaned_path):
    # 1. Open the file in ChimeraX
    # (Works for both .cif and .pdb automatically)
    models = run(session, f"open {input_file}")
    model = models[0] # Get the opened structure object
    
    # 2. Smartly delete the ligand using ChimeraX's internal logic
    run(session, "delete ligand")
    
    # 3. Rename remaining chains using your sequential Python logic
    # ChimeraX chains are stored in model.chains
    for idx, chain_id in enumerate(model.chains):
        print (idx, chain_id)
        if int(idx) < len(LEGAL_CHAIN_IDS):
            new_id = LEGAL_CHAIN_IDS[idx]
        else:
            new_id = f"C{idx}"
        
        # Change the chain ID natively in ChimeraX
        run(session, f"changechains {chain_id} {new_id}")
        
    
    # 4. Run DockPrep on the modified, cleaned structure
    run(session, "dockprep")
    run(session, "dssp")

    # 5. Extract info for parsing
    run(session, "info residues all attribute amber_name")
    run (session, "info polymers")
    
    # 6. Save the final prepared structure
    run(session, f"save {cleaned_path}")

    run(session, "quit")


_run(session, "$input_file", "$cleaned_path")