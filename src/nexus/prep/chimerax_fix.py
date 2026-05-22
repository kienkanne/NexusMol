import subprocess
from pathlib import Path
import re
from nexus.prep.prep_config import PrepConfig
from string import Template


def chimerax_fix(pcfg: PrepConfig):
    input_file = pcfg.input_file
    chimerax = pcfg.chimerax
    cleaned_suffix = pcfg.cleaned_suffix
    output_dir = pcfg.output_dir
    output_format = pcfg.output_format
    log_file = pcfg.log_file

    with open(Path(__file__).resolve().parents[0] / "_chimerax_fix_template.py") as f:
        chimerax_fix_template = f.read()     

    if cleaned_suffix == "":
        cleaned_path = output_dir / f"{input_file.stem}.{output_format}"
    else:
        cleaned_path = output_dir / f"{input_file.stem}_{cleaned_suffix}.{output_format}"

    input = Template(chimerax_fix_template).substitute(
        input_file=input_file      ,
        cleaned_path=cleaned_path,
    )

    clean_file = output_dir / f"{input_file.stem}_cleaner.py"

    with open(clean_file, "w") as f:
        f.write(input)

    result = subprocess.run([chimerax, "--nogui", clean_file], 
                            text=True, 
                            check=True,
                            capture_output=True)
    
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
    log_file.info(f"✅ Saved cleaned biological assembly receptor to {output_format.upper()} -> {cleaned_path}")
    
    if chains_info:
        log_file.info(f"ℹ️  Chains information:")
        for first_res, last_res in chains_info:
            log_file.info(f"   - Start: {first_res}     End: {last_res}")

    if flagged_residues:
        log_file.info("\n⚠️  ChimeraX assigned non-standard protonation states:")
        for res_id, name in flagged_residues:
            log_file.info(f"   - {res_id} was assigned {name}")

    return cleaned_path
