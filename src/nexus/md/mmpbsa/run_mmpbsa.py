from nexus.core.executors.shell import shell
import os
import shutil

from nexus.md.mmpbsa.mmpbsa_config import MMPBSAConfig


def run_mmpbsa(cfg: MMPBSAConfig, mmpbsa_input):
    scratch_dir = cfg._global.path.scratch_dir
    name = cfg.common.job_name
    receptor_mask = cfg.common.receptor_mask
    trajin = cfg.common.trajin
    n_cores = cfg.common.n_cores

    cwd = os.getcwd()
    try:
        os.chdir(scratch_dir)

        system = str(cfg.common.prmtop)
        complex = f"complex_{name}.prmtop"
        receptor = f"receptor_{name}.prmtop"
        ligand = f"ligand_{name}.prmtop"

        ante_mmpbsa_cmd = [
        "ante-MMPBSA.py",
        "-p",
        system,
        "-c",
        complex,
        "-r",
        receptor,
        "-l",
        ligand,
        "-s",
        ":WAT,Na+,Cl-",
        "-m",
        receptor_mask
        ]

        with shell(ante_mmpbsa_cmd):
            pass

        mmgbsa_in = scratch_dir / f"mmpbsa_{name}.in"
        mmgbsa_in.write_text(mmpbsa_input)

        outputs = {}
        energy = f"energy_{name}.csv"
        outputs["energy"] = scratch_dir / energy

        decomp = f"decomp_{name}.csv"
        if cfg.decomp.run:
            outputs["decomp"] = scratch_dir / decomp

        mmpbsa_py_mpi_cmd = [
            "mpirun",
            "-np",
            str(n_cores),
            "MMPBSA.py.MPI",
            "-O",
            "-i",
            str(mmgbsa_in),
            "-o",
            f"mmpbsa_{name}.out",
            "-sp",
            system,
            "-cp",
            complex,
            "-rp",
            receptor,
            "-lp",
            ligand,
            "-y",
            str(trajin),
            "-eo",
            energy,
        ]

        if cfg.decomp.run:
            mmpbsa_py_mpi_cmd.extend([
                "-do",
                decomp
            ])

        with shell(mmpbsa_py_mpi_cmd):
            pass
        
        output_dir = cfg.common.output_dir
        files_to_copy = [f"mmpbsa_{name}.out", energy]
        if cfg.decomp.run:
            files_to_copy.append(decomp)
        for file_name in files_to_copy:
            shutil.copy2(scratch_dir / file_name, output_dir / file_name)

    except Exception as e:
        raise RuntimeError(f"Failed to change working directory to {scratch_dir}: {e}")
    
    finally:
        os.chdir(cwd)
        
    return outputs