from dataclasses import dataclass
from pathlib import Path
import os
from nexus.core.executors.shell import shell
from nexus.core.trackers.main_tracker import main_tracker
from nexus.dock.dock_config import DockConfig


@dataclass(frozen=True)
class VinaReceptorBundle:
    receptor: Path
    vina_config: Path
    pocket: Path
    name: str


def _prep_rec(cfg: DockConfig, receptor_bundle: VinaReceptorBundle):
    if hasattr(receptor_bundle, "receptor"):
        receptor = receptor_bundle.receptor
        bundle = receptor_bundle
    else:
        receptor = receptor_bundle
        bundle = None

    name = Path(receptor).stem
    suffix = "prepared"

    scratch_dir = cfg._global.path.scratch_dir
    prepped_receptor_pdbqt = scratch_dir / f"{name}_{suffix}.pdbqt"
    pocket = scratch_dir / f"{name}_pocket.pdb"
    vina_config = scratch_dir / f"{name}_vina_config.txt"

    ###### ================ ######
    ###### 1. generate_site 
    ###### ================ ######

    chimerax = cfg._global.software.chimerax
    if chimerax is None:
        raise ValueError("ChimeraX path not configured in global nexus config")

    if bundle is not None and bundle.reference_path is not None:
        input_file = bundle.reference_path
        delete_selection = "clear"

    elif bundle is not None and bundle.selection_string is not None:
        input_file = receptor
        delete_selection = f"~{bundle.selection_string}"

    stdin = [
        f"open {input_file}",
        f"select {delete_selection}",
        "delete sel",
        f"save {pocket}"
    ]

    stdin = "\n".join(stdin)
    cmd = [chimerax, "--nogui"]

    with shell(cmd, stdin, f"generate_site for {name}"):
        pass

    if not os.path.exists(pocket):
        raise FileNotFoundError(f"{pocket} was not created. Check selection string or reference.")

    if os.path.getsize(pocket) == 0:
        raise IOError(f"{pocket} is empty. Check selection string or reference.")

    ###### ================ ######
    ###### 2. meeko_prep_rec 
    ###### ================ ######

    padding = cfg.common.padding

    cmd = [
            "mk_prepare_receptor.py",
            "-i",
            receptor,
            "-o",
            prepped_receptor_pdbqt.with_suffix(""),
            "-a",  # Allow bad res
            "-p",  # Generate receptor PDBQT
            "-v",
            vina_config,  # Generate Vina config file
            "--box_enveloping",
            pocket,  # Wrap around this molecule
            "--padding",
            str(padding),  # Padding buffer in Angstroms
        ]
    
    with shell(cmd, title=f"meeko_prep_rec for {name}"):
        pass

    ###### ================ ######
    ###### 2'. add_configs 
    ###### ================ ######
    
    exhaustiveness = cfg.engine.exhaustiveness
    num_modes = cfg.engine.num_modes
    extra_configs = {
                "exhaustiveness": exhaustiveness,
                "num_modes": num_modes,
                "cpu": 1
            }
    with open(vina_config, "a") as config_file:
        config_file.write("\n")
        for key, value in extra_configs.items():
            config_file.write(f"{key} = {value}\n")


    return VinaReceptorBundle(
        receptor=prepped_receptor_pdbqt,
        vina_config=vina_config,
        pocket=pocket, # For copy back only
        name=name,
    )


from nexus.core.executors.python_parallel import python_parallel
from nexus.core.trackers.main_tracker import main_tracker
from functools import partial
from typing import List


@main_tracker("Prepare receptor for Vina")
def vina_parallel_prep_rec(cfg: DockConfig) -> List[VinaReceptorBundle]:
    tasks = []
    bundles = getattr(cfg.receptors, "bundles", None)
    if bundles:
        for b in bundles:
            tasks.append(partial(_prep_rec, cfg, b))
    else:
        raise ValueError
    
    with python_parallel(tasks, cfg.common.n_jobs, title="vina_parallel_prep_rec()", skip=True) as output_bundles:
        pass

    return output_bundles