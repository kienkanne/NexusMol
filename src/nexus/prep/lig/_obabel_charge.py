
from pathlib import Path
from nexus.core.executors.python_parallel import python_parallel
from nexus.core.executors.shell import shell
from rdkit import Chem
from functools import partial

def _obabel_charge(mol_with_h, output: Path):
    tmp_sdf_path = output.parent / f"{output.stem}_tmp.sdf"
    
    with Chem.SDWriter(str(tmp_sdf_path)) as writer:
        writer.write(mol_with_h)

    cmd = [
        "obabel",
        tmp_sdf_path,
        "-O", output,
        "--ff", "mmff94"
        ]
    with shell(cmd, title=f"obabel charge for {output.stem}"):
        pass

    Path(tmp_sdf_path).unlink(missing_ok=False)

    return True


def _parallel_obabel_charge(mol_with_h_list, output_list, n_jobs):
    tasks = []
    for mol_with_h, output in zip(mol_with_h_list, output_list):
        tasks.append(partial(_obabel_charge, mol_with_h, output))

    with python_parallel(tasks, n_jobs, "parallel_obabel_charge()", skip=True):
        pass

    return output_list
