import os
import subprocess
from pathlib import Path
import re
from nexus.fetch.fetch_config import FetchConfig

def chimerax_fix(fcfg: FetchConfig, stripped_path: Path, id: str) -> Path:
    chimerax = fcfg.chimerax
    fixed_suffix = fcfg.fixed_suffix
    output_dir = fcfg.output_dir
    format = fcfg.format
    
    # Safely retrieve the mutations/protonation changes, defaulting to an empty list
    mutations = getattr(fcfg, 'mutations_csv', {}) 

    # ChimeraX have problem writing cif output from gemmi
    # If the requested format is cif, then pdb is written first, then is converted to cif
    if fixed_suffix == "":
        fixed_path = os.path.join(output_dir, f"{id}.pdb")
    else:
        fixed_path = os.path.join(output_dir, f"{id}_{fixed_suffix}.pdb")

    ## 1. Parse and Validate Selections
    user_requested_states = {}
    setattr_commands = []
    
    for sel, new_name in mutations.items():
        # Enforce the strict {something}&:{RES} syntax
        # match.group(1) will capture the base ID (e.g., /A:41)
        # match.group(2) captures the old residue name (e.g., HIS)
        match = re.match(r"^(.*)&:([A-Za-z0-9]{3})$", sel)
        if not match:
            raise ValueError(f"Invalid selection syntax: '{sel}'. Must match '{{specifier}}&:{{RES}}'")
        
        base_id = match.group(1)
        user_requested_states[base_id] = new_name
        setattr_commands.append(f"run (session, 'setattr {sel} residue name {new_name}')")

    ## 2. Dynamically Build the ChimeraX Script

    template_path = Path(__file__).resolve().parent / "_chimerax_script.py"
    template_str  = template_path.read_text()

    prep_list = [
        "run (session, 'delete ligand')",
        "run (session, 'delete solvent')",
        "run (session, 'delete H')"
        ]

    prep_list.extend(setattr_commands)

    prep_list.extend([
        "run (session, 'dockprep')",
        "run (session, 'info residues all attribute amber_name')",
        "run (session, 'dssp')",
        f"run (session, 'save {fixed_path}')"
    ])


    # If the requested format is cif, then pdb is written first, then is converted to cif
    if format == "cif":
        cif_fixed_path = fixed_path.with_suffix(".cif")
        prep_list.extend([
            f"run (session, 'open {fixed_path}')"
            f"run (session, 'save {cif_fixed_path}')"
        ])
        Path(fixed_path).unlink(missing_ok=True)
    
    prep_str = "\n".join(prep_list)
    stdin = template_str + "\n" + prep_str

    with open("/localscratch/kbui/NexusMol/src/nexus/fetch/script.py", "w") as f:
        f.write(stdin)

    ## 3. Execute Subprocess 
    # Notice `capture_output=True` is required to read result.stdout
    result = subprocess.run(
        [chimerax, "--nogui", "script.py"], 
        input=stdin, 
        text=True, 
        capture_output=False, 
        check=True
    )

    ## 4. Parse the Log for Unwanted Special States
    special_residues = {'HIE', 'HID', 'HIP', 'GLH', 'ASH', 'LYN', 'CYM'}
    requested_residues = []
    flagged_residues = []

    # Iterate through the ChimeraX output line by line
    for line in result.stdout.splitlines():
        if "amber_name" in line and "residue id" in line:
            # Matches strings like: "residue id /A:8 amber_name HID index 7"
            match = re.search(r"residue id (\S+) amber_name (\S+)", line)
            if match:
                res_id, amber_name = match.groups()
                # If the residue is special, verify if the user explicitly asked for it
                if amber_name in special_residues:
                    # We check `res_id` against the `base_id` we stored earlier
                    
                    if user_requested_states.get(res_id) != amber_name:
                        flagged_residues.append((res_id, amber_name))

    ## 5. Output Results
    print(f"✅ Saved fixed biological assembly receptor to {format.upper()} -> {fixed_path}")
    
    print("\n✅ User requested mutations completed: ")
    for res_id, name in user_requested_states.items():
        print(f"   - {res_id} was assigned {name}")

    if flagged_residues:
        print("\n⚠️  ChimeraX assigned non-standard protonation states that were NOT explicitly requested:")
        for res_id, name in flagged_residues:
            print(f"   - {res_id} was assigned {name}")
            
    return fixed_path