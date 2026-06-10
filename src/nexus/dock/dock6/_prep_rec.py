from dataclasses import dataclass
from pathlib import Path
import os
from string import Template
from nexus.core.executors.shell import shell
from nexus.dock.dock_config import DockConfig


@dataclass(frozen=True)
class Dock6ReceptorBundle:
    receptor: Path
    selected_spheres: Path
    grid_prefix: Path
    pocket: Path
    name: str


def _prep_rec(cfg: DockConfig, receptor_bundle: Dock6ReceptorBundle):
    if hasattr(receptor_bundle, "receptor"):
        receptor = receptor_bundle.receptor
        bundle = receptor_bundle
    else:
        raise AttributeError("Receptor bundle does not have 'receptor' attribute")
    
    name = Path(receptor).stem
    suffix = "prepared"

    scratch_dir = cfg._global.path.scratch_dir
    prepped_receptor_mol2 = scratch_dir / f"{name}_{suffix}.mol2"
    prepped_receptor_noH_mol2 = scratch_dir / f"{name}_{suffix}_noH.mol2"
    pocket = scratch_dir / f"{name}_pocket.mol2"

    # Check DOCK6 software requirements
    chimerax = cfg._global.software.chimerax
    if chimerax is None or not Path(chimerax).exists():
        raise ValueError("ChimeraX path not configured or not exists in global nexus config")
    
    chimera = cfg._global.software.chimera
    if chimera is None or not Path(chimera).exists():
        raise ValueError("Chimera (legacy) path not configured or not exists in global nexus config")
    
    dock_home = cfg._global.software.dock6
    if dock_home is None or not Path(dock_home).exists():
        raise ValueError("DOCK6 path not configured or not exists in global nexus config")

    ###### ================ ######
    ###### 1. generate_site 
    ###### ================ ######

    stdin = [
        f"open {receptor}",
        f"save {prepped_receptor_mol2}",
        f"delete H",
        f"save {prepped_receptor_noH_mol2}",
        "close"
    ]

    if bundle is not None and bundle.reference_path is not None:
        input_file = bundle.reference_path
        delete_selection = "clear"

    elif bundle is not None and bundle.selection_string is not None:
        input_file = prepped_receptor_noH_mol2
        delete_selection = f"~{bundle.selection_string}"

    stdin.extend([
        f"open {input_file}",
        f"select {delete_selection}",
        "delete sel",
        f"save {pocket}"
    ])

    stdin = "\n".join(stdin)
    cmd = [chimerax, "--nogui"]

    with shell(cmd, stdin, f"generate_site for {name}"):
        pass

    if not os.path.exists(pocket):
        raise FileNotFoundError(f"{pocket} was not created. Check selection string or reference.")

    if os.path.getsize(pocket) == 0:
        raise IOError(f"{pocket} is empty. Check selection string or reference.")

    ###### ================ ######
    ###### 2. write_dms 
    ###### ================ ######

    with open(Path(__file__).resolve().parents[0] / "templates" / "write_dms_template.py") as f:
        write_dms_template = f.read()

    input_file = Template(write_dms_template).substitute(prepped_receptor_noH_mol2=prepped_receptor_noH_mol2,
                                                            name=name)
    
    write_dms_path = scratch_dir / f"{name}_write_dms.py"
    
    with open(write_dms_path, "w") as file:
        file.write(input_file)

    cmd = ["env", 
            "LD_PRELOAD=/usr/lib64/libz.so.1:/usr/lib64/libfreetype.so.6", 
            "LD_LIBRARY_PATH=/usr/local/chem.sw/chimera/chimera-1.8/lib",
            chimera,
            "--nogui", write_dms_path]

    with shell(cmd, title=f"write_dms for {name}"):
        pass

    ###### ================ ######
    ###### 3. sphgen_&_sphere_selector 
    ###### ================ ######
    
    ### Patch behavior of sphgen and sphere_selector having hardcoded outputs
    import subprocess
    import shutil
    from nexus.core.trackers.main_tracker import TrackerContext
    logger = TrackerContext.get_ctx().logger
    logger.info(f"Running: sphgen_&_sphere_selector for {name}")

    with open(Path(__file__).resolve().parents[0] / "templates" / "INSPH_template.txt") as f:
        INSPH_template = f.read()

    wd = scratch_dir
    cwd = Path(wd / f"tmp_ss_{name}")
    cwd.mkdir(parents=True, exist_ok=True)

    input_file = Template(INSPH_template).substitute(name=name)
    with open(cwd/"INSPH", "w") as file:
        file.write(input_file)

    shutil.copy2(wd/f"{name}_rec.dms",cwd/f"{name}_rec.dms")
    cmd = [dock_home/"bin"/"sphgen", "-i", "INSPH", "-o", "OUTSPH"]
    subprocess.run(cmd, cwd=cwd, text=True, check=True)

    radius = str(cfg.engine.radius)
    shutil.copy2(wd/f"{name}_pocket.mol2",cwd/f"{name}_pocket.mol2")
    cmd = [dock_home/"bin"/"sphere_selector", f"{name}_rec.sph", f"{name}_pocket.mol2", radius]
    subprocess.run(cmd, cwd=cwd, text=True, check=True)

    ss = cwd / "selected_spheres.sph"
    new_selected_spheres = wd / f"{name}_ss.sph"

    if ss.exists():
        ss.rename(new_selected_spheres)
    shutil.rmtree(cwd)

    ###### ================ ######
    ###### 4. showbox 
    ###### ================ ######
    
    rec_box = scratch_dir / f"{name}_rec_box.pdb"   
    padding = cfg.common.padding

    stdin = f"Y\n{padding}\n{new_selected_spheres}\n1\n{rec_box}\n"
    cmd = [dock_home/"bin"/"showbox"]
    with shell(cmd, stdin, f"showbox for {name}"):
        pass

    ###### ================ ######
    ###### 5. grid 
    ###### ================ ######

    grid_prefix = scratch_dir / f"{name}_grid"
    with open(Path(__file__).resolve().parents[0] / "templates" / "grid_template.txt") as f:
        grid_template = f.read()

    input_file = Template(grid_template).substitute(prepped_receptor=prepped_receptor_mol2, 
                                                    dock_home=dock_home,
                                                    rec_box=rec_box,
                                                    grid_prefix=grid_prefix,
                                                    name=name)
    
    with open(f"{grid_prefix}.in", "w") as file:
        file.write(input_file)

    cmd = [dock_home/"bin"/"grid", "-i", f"{grid_prefix}.in", "-o", f"{grid_prefix}.out"]
    with shell(cmd, title=f"grid for {name}"):
        pass


    return Dock6ReceptorBundle(
        receptor=Path(prepped_receptor_mol2),
        selected_spheres=new_selected_spheres,
        grid_prefix=grid_prefix,
        pocket=pocket,
        name=name,
    )


from nexus.core.executors.python_parallel import python_parallel
from nexus.core.trackers.main_tracker import main_tracker
from functools import partial
from typing import List


@main_tracker("Prepare receptor for DOCK6")
def dock6_parallel_prep_rec(cfg) -> List[Dock6ReceptorBundle]:
    tasks = []
    bundles = getattr(cfg.receptors, "bundles", None)
    if bundles:
        for b in bundles:
            tasks.append(partial(_prep_rec, cfg, b))
    else:
        raise ValueError
    
    with python_parallel(tasks, cfg.common.n_jobs, title="dock6_parallel_prep_rec()", skip=True) as output_bundles:
        pass

    return output_bundles

