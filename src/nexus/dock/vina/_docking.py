from nexus.core.executors.shell import shell
from nexus.core.executors.python_parallel import python_parallel
from functools import partial
from nexus.core.trackers.main_tracker import main_tracker

# Typing hints only
from nexus.dock.dock_config import DockConfig
from nexus.dock.vina._prep_rec import VinaReceptorBundle


def _run_vina(cfg: DockConfig, receptor_bundle: VinaReceptorBundle, prepped_lig):
    scratch_dir = cfg._global.path.scratch_dir

    receptor_path = receptor_bundle.receptor
    vina_config = receptor_bundle.vina_config
    receptor_name = receptor_bundle.name
    ligand_name = prepped_lig.stem

    output_prefix = f"{receptor_name}_{ligand_name}"

    output_path = scratch_dir / f"{output_prefix}_scored.pdbqt"

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
def vina_parallel_docking(cfg, pairs):
    tasks = []
    for receptor_bundle, prepped_lig in pairs:
        tasks.append(partial(_run_vina, cfg, receptor_bundle, prepped_lig))

    with python_parallel(tasks, cfg.common.n_jobs, "vina_parallel_docking()", skip=True) as out_paths:
        pass

    return out_paths
