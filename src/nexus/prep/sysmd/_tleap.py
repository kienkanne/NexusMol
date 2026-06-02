import re
from pathlib import Path

from nexus.prep.prep_config import PrepConfig
from nexus.core.executors.shell import shell


def parse_volume(tleap_output):
    match = re.search(r"Volume:\s+([\d.]+)\s+A\^3", tleap_output)
    if not match:
        raise ValueError("Volume not found in tleap output")
    return float(match.group(1))


def build_tleap_cmd(input_dict: dict):
    stdin = [
        f"source leaprc.protein.{input_dict['force_field']}",
        f"source leaprc.water.{input_dict['water_model']}",
        "source leaprc.gaff2",
        f"REC = loadpdb {input_dict['receptor_renamed']}"
    ]

    if input_dict['ligand_charged'] is not None and input_dict['ligand_frcmod'] is not None:
        stdin.extend([
            f"loadamberparams {input_dict['ligand_frcmod']}",
            f"LIG = loadmol2 {input_dict['ligand_charged']}",
            "SYS = combine {REC LIG}"
        ])
    else:
        stdin.extend(["SYS = REC"])

    stdin.extend([
        f"{input_dict['box_model_solvate']} SYS {input_dict['water_model_box']} {input_dict['box_size']}",
        # Neutralize the system first,
        "addIonsRand SYS Na+ 0",
        "addIonsRand SYS Cl- 0",
        # Then add additional ions to get desired salt concentration
        # The first run adds 0 to parse the volume first, the second adds the correct concentration
        f"addIonsRand SYS Na+ {input_dict['n_ions']}",
        f"addIonsRand SYS Cl- {input_dict['n_ions']}",
        f"saveamberparm SYS {input_dict['output_suffix']}.prmtop {input_dict['output_suffix']}.inpcrd",
        f"savepdb SYS {input_dict['output_suffix']}.pdb",
        "quit"   
    ])
    
    stdin = "\n".join(stdin)
    cmd = ["tleap", "-f", "-"]

    with shell(cmd, stdin) as stdout:
        pass
    
    return stdout


def run_tleap(pcfg: PrepConfig, receptor_renamed: Path, ligand_charged: Path, ligand_frcmod: Path):
    output_dir = pcfg.common.output_dir
    name = pcfg.sysmd.system_name

    if name is None:
        name = f"{receptor_renamed.stem}_solvated"

    force_field = pcfg.sysmd.force_field
    water_model = pcfg.sysmd.water_model
    box_type = pcfg.sysmd.box_type
    box_size = pcfg.sysmd.box_size
    salt_conc = pcfg.sysmd.salt_conc

    output_suffix = output_dir / name

    n_ions_dummy = 0
    input_dict={
        "force_field": force_field,
        "water_model": water_model,
        "receptor_renamed": str(receptor_renamed),
        "ligand_charged": str(ligand_charged) if ligand_charged is not None else None,
        "ligand_frcmod": str(ligand_frcmod) if ligand_frcmod is not None else None,
        "box_model_solvate": f"solvate{box_type}",
        "water_model_box": f"{water_model.upper()}BOX",
        "box_size":str(box_size),
        "output_suffix": str(output_suffix),
        "n_ions": str(n_ions_dummy)
    }

    stdout = build_tleap_cmd(input_dict)

    # Calculate ions based on volume from tleap output
    volume_A3 = parse_volume(stdout)
    volume_L = volume_A3 * 1e-27
    N_pairs = salt_conc * 6.022e23 * volume_L
    n_ions = round(N_pairs)

    input_dict['n_ions'] = str(n_ions)   

    build_tleap_cmd(input_dict)

    return True
    
