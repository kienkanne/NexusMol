import subprocess
from pathlib import Path
import re
from typing import List
from nexus.prep.prep_config import PrepConfig
from nexus.core.trackers.logging_utils import CustomLogger

def chimerax_mutate(cfg: PrepConfig):
    input: List[Path] = cfg.common.input
    output_dir = cfg.common.output_dir
    suffix = cfg.common.suffix
    chimerax = cfg._global.software.chimerax
    mutations = cfg.mutate.mutations

    ## 1. Parse and Validate Selections

    for input_path in input:
        output_path = output_dir / f"{input_path.stem}{suffix}"
        logger = CustomLogger(output_path.with_suffix(".log"), time_verbose=False)

        user_requested_states = {}
        setattr_commands = []
        for sel_res in mutations:
            sel = sel_res[0]
            new_res = sel_res[1]
            
            user_requested_states[sel] = new_res
            setattr_commands.extend([
                f"select {sel}",
                "delete H&sel",
                f"setattr sel residue name {new_res}",
                "addh sel",
                "addcharge sel",
                "info residues sel attribute name",
                "select clear"
                                    ])

        ## 2. Dynamically Build the ChimeraX Script
        script_lines = [
            f"open {input_path}"
        ]

        script_lines.extend(setattr_commands)

        script_lines.extend([
            f"save {output_path}",
            "exit"
        ])
        
        stdin = "\n".join(script_lines)

        ## 3. Execute Subprocess 
        result = subprocess.run(
            [chimerax, "--nogui"], 
            input=stdin, 
            text=True, 
            capture_output=True, 
            check=True
        )

        # PDBQT can't read AMBER residue names, so we must revert the naming
        # This only standardize naming, while maintaining the changed protonation state
        overwrite_pdb_residues(output_path)

        ## 4. Output Results
    ## 4. Parse the Log for Selection Failures
        log_lines = result.stdout.splitlines()
        failed_selections = []

        for i, line in enumerate(log_lines):
            # Check if ChimeraX reported an empty selection
            if "Nothing selected" in line or "Selection is empty" in line:
                # Look backwards up to 3 lines to find the command that caused it
                command_context = "Unknown command"
                for lookback in range(1, 4):
                    if i - lookback >= 0 and "Executing: select" in log_lines[i - lookback]:
                        command_context = log_lines[i - lookback].strip()
                        break
                
                failed_selections.append((command_context, line.strip()))

        mutated_residues = []
        for line in result.stdout.splitlines():
            if "name" in line and "residue id" in line:
                # Matches strings like: "residue id /B:145 name CYM index 144"
                match = re.search(r"residue id (\S+) name (\S+)", line)
                if match:
                    res_id, amber_name = match.groups()
                    mutated_residues.append((res_id, amber_name))

        # Report clean, uncluttered errors if any occurred
        if failed_selections:
            logger.info("\n⚠️  Warning: ChimeraX reported empty selections during execution!")
            for cmd, failure in failed_selections:
                logger.info(f"  ❌ {failure}")
                logger.info(f"     Triggered by: {cmd}")

        else:
            logger.info("\n✅ Requested mutations completed: ")
            for res_id, name in mutated_residues:
                logger.info(f"   - {res_id} was assigned {name}")

        logger.info(f"✅ Saved mutated receptor to -> {output_path}")

    return None


def overwrite_pdb_residues(filename):
    # Mapping Amber protonation states to standard residue names
    res_mapping = {
        "HID": "HIS", "HIE": "HIS", "HIP": "HIS",
        "CYX": "CYS", "CYM": "CYS",
        "LYN": "LYS", "ASH": "ASP", "GLH": "GLU",
    }
    
    with open(filename, 'r') as infile:
        lines = infile.readlines()
        
    with open(filename, 'w') as outfile:
        for line in lines:
            # 1. Handle coordinate and termination lines with strict column slicing
            if line.startswith(("ATOM", "HETATM", "TER")):
                res_name = line[17:20].strip()
                if res_name in res_mapping:
                    standard_name = res_mapping[res_name]
                    line = line[:17] + f"{standard_name:<3}" + line[20:]
            
            # 2. Handle metadata lines (SEQRES, HELIX, SHEET, SSBOND, LINK, etc.)
            else:
                for amber_res, std_res in res_mapping.items():
                    if amber_res in line:
                        # Direct replacement works safely for metadata because standard 
                        # and AMBER residue names are both exactly 3 characters long.
                        line = line.replace(amber_res, std_res)
                        
            outfile.write(line)