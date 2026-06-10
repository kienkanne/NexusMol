from pathlib import Path
from nexus.core.executors.shell import shell
import os


def _run_mmpbsa_cmd(mmgbsa_input: str, prmtop: Path, trajin: Path, output_dir: Path, mask: str, name: str= "", n_cores: int=1, logger=None):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cwd = os.getcwd()
    try:
        os.chdir(output_dir)

        system = str(prmtop)
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
        mask
        ]

        with shell(ante_mmpbsa_cmd):
            pass

        mmgbsa_in = output_dir / f"mmpbsa_{name}.in"
        mmgbsa_in.write_text(mmgbsa_input)


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
            f"energy_{name}.csv",
            "-do",
            f"decomp_{name}.csv"
        ]

        with shell(mmpbsa_py_mpi_cmd):
            pass

    except Exception as e:
        raise RuntimeError(f"Failed to change working directory to {output_dir}: {e}")
    
    finally:
        os.chdir(cwd)
        