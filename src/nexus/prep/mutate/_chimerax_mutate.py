import subprocess
from pathlib import Path
import re
from typing import List
from nexus.prep.prep_config import PrepConfig
from nexus.core.trackers.logging_utils import setup_logger

def chimerax_mutate(pcfg: PrepConfig):
    input: List[Path] = pcfg.common.input
    output_dir = pcfg.common.output_dir
    suffix = pcfg.common.suffix
    chimerax = pcfg.common.chimerax
    mutations = pcfg.mutate.mutations

    ## 1. Parse and Validate Selections

    for input_path in input:
        output_path = output_dir / f"{input_path.stem}{suffix}"
        log_path = setup_logger(output_path.with_suffix(".log"), time_verbose=False)

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
            log_path.info("\n⚠️  Warning: ChimeraX reported empty selections during execution!")
            for cmd, failure in failed_selections:
                log_path.info(f"  ❌ {failure}")
                log_path.info(f"     Triggered by: {cmd}")

        else:
            log_path.info("\n✅ Requested mutations completed: ")
            for res_id, name in mutated_residues:
                log_path.info(f"   - {res_id} was assigned {name}")

        log_path.info(f"✅ Saved mutated receptor to -> {output_path}")

    return None