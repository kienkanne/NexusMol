from pydantic import BaseModel
import os
from nexus.md.buildpep.buildpep_config import BuildPepConfig
from pathlib import Path

aa_map = {
 'A': 'ALA',
 'G': 'GLY',
 'V': 'VAL',
 'L': 'LEU',
 'I': 'ILE',
 'M': 'MET',
 'F': 'PHE',
 'W': 'TRP',
 'P': 'PRO',
 'S': 'SER',
 'T': 'THR',
 'C': 'CYS',
 'Y': 'TYR',
 'N': 'ASN',
 'Q': 'GLN',
 'D': 'ASP',
 'E': 'GLU',
 'K': 'LYS',
 'R': 'ARG',
 'H': 'HIS'}

class BuildPepPipeline(BaseModel):
    cfg: BuildPepConfig

    def _run(self):
        AMBERHOME = os.environ.get("AMBERHOME")
        if not AMBERHOME:
            raise RuntimeError("AMBERHOME environment variable not set")
        
        cfg = self.cfg
        output_dir = f"{cfg.common.output_dir}/{cfg.common.job_name}"
        Path(output_dir).mkdir(exist_ok=True, parents=True)

        seq_file = cfg.common.seq_file

        with open(seq_file) as f:
            for i, line in enumerate(f, start=1):
                seq = line.strip().upper()
                if not seq:
                    continue

                ones = [c for c in seq]
                threes_list = [aa_map[c] for c in ones]
                threes = " ".join(threes_list)

                name = f"{i}_{seq}"

                tleap_input = f"""
        source leaprc.protein.{cfg.system.force_field}
        source leaprc.water.{cfg.system.water_model}

        PEP = sequence {{ ACE {threes} NME }}

        solvate{cfg.system.box_type} PEP {cfg.system.water_model.upper()}BOX {str(cfg.system.box_size)}
        addIonsRand PEP Na+ 0
        addIonsRand PEP Cl- 0

        saveamberparm PEP {output_dir}/{name}.prmtop {output_dir}/{name}.inpcrd

        quit
        """

                with open(f"{output_dir}/tleap_{name}.in", "w") as f_in:
                    f_in.write(tleap_input)

                os.system(f"tleap -f {output_dir}/tleap_{name}.in > {output_dir}/tleap_{name}.log 2>&1")

                print(f"Generated {name}")
