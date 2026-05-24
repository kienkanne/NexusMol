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


def _prep_rec(dcfg: DockConfig, receptor_bundle: Dock6ReceptorBundle):
    # receptor_bundle may be either a Path (legacy) or a ReceptorConfigBundle-like object
    if hasattr(receptor_bundle, "receptor"):
        receptor = receptor_bundle.receptor
        bundle = receptor_bundle
    else:
        receptor = receptor_bundle
        bundle = None
    name = Path(receptor).stem
    dock_home = dcfg.libs.dock_home
    suffix = "prepared"
    working_dir = dcfg.common.working_dir

    prepped_receptor_mol2 = working_dir / f"{name}_{suffix}.mol2"
    prepped_receptor_noH_mol2 = working_dir / f"{name}_{suffix}_noH.mol2"
    pocket = working_dir / f"{name}_pocket.mol2"

    @shell(dcfg.common.logger)
    def generate_site():
        chimerax = dcfg.libs.chimerax
  
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

        return ([chimerax, "--nogui"], stdin)
    generate_site()

    if not os.path.exists(pocket):
        raise FileNotFoundError(f"{pocket} was not created. Check selection string or reference.")

    if os.path.getsize(pocket) == 0:
        raise IOError(f"{pocket} is empty. Check selection string or reference.")

    @shell(dcfg.common.logger)
    def writedms():
        chimera = dcfg.libs.chimera
        with open(Path(__file__).resolve().parents[0] / "templates" / "write_dms_template.py") as f:
            write_dms_template = f.read()

        input_file = Template(write_dms_template).substitute(prepped_receptor_noH_mol2=prepped_receptor_noH_mol2,
                                                                name=name)
        
        write_dms_path = working_dir / f"{name}_write_dms.py"
        
        with open(write_dms_path, "w") as file:
            file.write(input_file)

        return (["env", 
                "LD_PRELOAD=/usr/lib64/libz.so.1:/usr/lib64/libfreetype.so.6", 
                "LD_LIBRARY_PATH=/usr/local/chem.sw/chimera/chimera-1.8/lib",
                chimera,
                "--nogui", write_dms_path], None)
    writedms()
    
    ### Patch behavior of sphgen and sphere_selector having hardcoded outputs
    def spheres():
        dcfg.common.logger.info("Running sphgen and sphere_selector")
        import subprocess
        import shutil
        with open(Path(__file__).resolve().parents[0] / "templates" / "INSPH_template.txt") as f:
            INSPH_template = f.read()

        wd = dcfg.common.working_dir
        cwd = Path(wd / f"tmp_ss_{name}")
        cwd.mkdir(parents=True, exist_ok=True)

        input_file = Template(INSPH_template).substitute(name=name)
        with open(cwd/"INSPH", "w") as file:
            file.write(input_file)

        shutil.copy2(wd/f"{name}_rec.dms",cwd/f"{name}_rec.dms")
        cmd = [dock_home/"bin"/"sphgen", "-i", "INSPH", "-o", "OUTSPH"]
        subprocess.run(cmd, cwd=cwd, text=True, check=True)

        radius = str(dcfg.dock6.radius)
        shutil.copy2(wd/f"{name}_pocket.mol2",cwd/f"{name}_pocket.mol2")
        cmd = [dock_home/"bin"/"sphere_selector", f"{name}_rec.sph", f"{name}_pocket.mol2", radius]
        subprocess.run(cmd, cwd=cwd, text=True, check=True)

        ss = cwd / "selected_spheres.sph"
        named_ss_path = wd / f"{name}_ss.sph"

        if ss.exists():
            ss.rename(named_ss_path)
        shutil.rmtree(cwd)

        return named_ss_path
    selected_spheres = spheres()

    rec_box = working_dir / f"{name}_rec_box.pdb"   
    @shell(dcfg.common.logger)
    def showbox():
        padding = dcfg.common.padding
        stdin = f"Y\n{padding}\n{selected_spheres}\n1\n{rec_box}\n"
        return ([dock_home/"bin"/"showbox"], stdin)
    showbox()


    grid_prefix = working_dir / f"{name}_grid"
    @shell(dcfg.common.logger)
    def grid():
        with open(Path(__file__).resolve().parents[0] / "templates" / "grid_template.txt") as f:
            grid_template = f.read()

        input_file = Template(grid_template).substitute(prepped_receptor=prepped_receptor_mol2, 
                                                        dock_home=dock_home,
                                                        rec_box=rec_box,
                                                        grid_prefix=grid_prefix,
                                                        name=name)
        
        with open(f"{grid_prefix}.in", "w") as file:
            file.write(input_file)

        return ([dock_home/"bin"/"grid", "-i", f"{grid_prefix}.in", "-o", f"{grid_prefix}.out"], None)
    grid()

    return Dock6ReceptorBundle(
        receptor=Path(prepped_receptor_mol2),
        selected_spheres=selected_spheres,
        grid_prefix=grid_prefix,
        pocket=pocket,
        name=name,
    )


from nexus.core.executors.python_parallel import python_parallel
from nexus.core.trackers.main_tracker import main_tracker
from functools import partial
from typing import List



def dock6_prep_rec(dcfg) -> List[Dock6ReceptorBundle]:
    @main_tracker(dcfg, "Prepare receptor for DOCK6")
    @python_parallel(dcfg.common.n_jobs, title="prep_rec()", skip=True)
    def _run():
        tasks = []
        bundles = getattr(dcfg.receptors, "bundles", None)
        if bundles:
            for b in bundles:
                tasks.append(partial(_prep_rec, dcfg, b))
        else:
            raise ValueError
        return tasks
    return _run()
