from nexus.core.executors.shell import shell
from nexus.core.executors.python_parallel import python_parallel
from functools import partial
from nexus.core.trackers.main_tracker import main_tracker


def _run_vina(dcfg, receptor_bundle, prepped_lig):
    working_dir = dcfg.common.working_dir

    receptor_path = receptor_bundle.receptor
    vina_config = receptor_bundle.vina_config
    receptor_name = receptor_bundle.name
    ligand_name = prepped_lig.stem

    output_prefix = f"{receptor_name}_{ligand_name}"

    output_path = working_dir / f"{output_prefix}_scored.pdbqt"

    cmd = [
        "vina",
        "--receptor", str(receptor_path),
        "--ligand", str(prepped_lig),
        "--config", str(vina_config),
        "--out", output_path,
    ]

    with shell(cmd, title=f"vina docking for {output_prefix}"):
        pass

    return output_path


@main_tracker("Batch docking with Vina")
def vina_parallel_docking(dcfg, pairs):
    tasks = []
    for receptor_bundle, prepped_lig in pairs:
        tasks.append(partial(_run_vina, dcfg, receptor_bundle, prepped_lig))

    with python_parallel(tasks, dcfg.common.n_jobs, "dock6_parallel_docking()", skip=True) as out_paths:
        pass

    return out_paths
