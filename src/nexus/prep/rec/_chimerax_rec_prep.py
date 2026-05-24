import subprocess
from pathlib import Path
import re
from string import Template
from nexus.prep.prep_config import PrepConfig
from nexus.core.trackers.logging_utils import setup_logger

def chimerax_rec_prep(pcfg: PrepConfig):
    input = pcfg.common.input
    output_dir = pcfg.common.output_dir
    suffix = pcfg.common.suffix
    chimerax = pcfg.common.chimerax

    dry = pcfg.rec.dry

    for input_path in input:
        output_path = output_dir / f"{input_path.stem}{suffix}"
        log_path = setup_logger(output_dir / f"{input_path.stem}.log", time_verbose=False)

        with open(Path(__file__).resolve().parents[0] / "_clean_template.py") as f:
            clean_template = f.read()     

        clean_input = Template(clean_template).substitute(
            input_path=input_path,
            output_path=output_path,
            dry=str(dry)
        )

        clean_file = output_path.parent / f"cleaner_{input_path.stem}.py"

        with open(clean_file, "w") as f:
            f.write(clean_input)

        result = subprocess.run([chimerax, "--nogui", clean_file], 
                                text=True, 
                                check=True,
                                capture_output=True)
        
        clean_file.unlink(missing_ok=True)

        special_residues = {'HIE', 'HID', 'HIP', 'GLH', 'ASH', 'LYN', 'CYM'}
        chains_info = []
        flagged_residues = []

        # Iterate through the ChimeraX output line by line
        for line in result.stdout.splitlines():
            if "physical chain" in line:
                # Matches strings like : "physical chain /A:1 /A:306":
                match = re.search(r"physical chain (\S+) (\S+)", line)
                if match:
                    first_res, last_res = match.groups()
                    chains_info.append((first_res, last_res))

            if "amber_name" in line and "residue id" in line:
                # Matches strings like: "residue id /A:8 amber_name HID index 7"
                match = re.search(r"residue id (\S+) amber_name (\S+)", line)
                if match:
                    res_id, amber_name = match.groups()
                    # If the residue is special, verify if the user explicitly asked for it
                    if amber_name in special_residues:
                        flagged_residues.append((res_id, amber_name))

        ## 5. Output Results
        log_path.info(f"✅ Saved cleaned biological assembly receptor to -> {output_path}")
        
        if chains_info:
            log_path.info(f"ℹ️  Chains information:")
            for first_res, last_res in chains_info:
                log_path.info(f"   - Start: {first_res}     End: {last_res}")

        if flagged_residues:
            log_path.info("\n⚠️  ChimeraX assigned non-standard protonation states:")
            for res_id, name in flagged_residues:
                log_path.info(f"   - {res_id} was assigned {name}")

    return None
