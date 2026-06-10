def _meeko_charge(mol_with_h, output_path):
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    preparator = MoleculePreparation()
    mol_setups = preparator.prepare(mol_with_h)
    setup = mol_setups[0]

    pdbqt_string, is_valid, error_msg = PDBQTWriterLegacy.write_string(setup)
    if not is_valid:
        raise RuntimeError(f"Meeko failed to generate PDBQT: {error_msg}")

    with open(output_path, "w") as handle:
        handle.write(pdbqt_string)
    return True


from functools import partial
from typing import List
from pathlib import Path
from nexus.core.executors.python_parallel import python_parallel


def _parallel_meeko_charge(mol_with_h_list, output_list, n_jobs) -> List[Path]:
    tasks = []
    for mol_with_h, output_path in zip(mol_with_h_list, output_list):
        tasks.append(partial(
            _meeko_charge,
            mol_with_h,
            output_path
        ))

    with python_parallel(tasks, n_jobs, "parallel_meeko_charge()", skip=True):
        pass

    return output_list