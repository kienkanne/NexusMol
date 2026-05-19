from dataclasses import dataclass
from pathlib import Path
from string import Template
from compdd.executors.shell import shell
from compdd.executors.base import base


@dataclass(frozen=True)
class Dock6ReceptorBundle:
    receptor: Path
    selected_spheres: Path
    name: str


def _prep_rec(cfg, receptor):
    name = Path(receptor).stem
    dock_home = cfg.libs.dock_home
    suffix = cfg.common.prepared_suffix
    prepped_receptor_mol2 = f"{name}_{suffix}.mol2"
    prepped_receptor_noH_mol2 = f"{name}_{suffix}_noH.mol2"
    prepped_receptor_noH_pdb = f"{name}_{suffix}_noH.pdb"

    @shell(cfg)
    def charge_rec():
        chimerax = cfg.libs.chimerax

        with open(Path(__file__).resolve().parents[0] / "templates" / "dock6_charge_rec_template.com") as f:
            dock6_charge_rec_template = f.read()     

        stdin = Template(dock6_charge_rec_template).substitute(
            receptor=receptor,
            prepped_receptor_mol2=prepped_receptor_mol2,
            prepped_receptor_noH_mol2=prepped_receptor_noH_mol2,
            prepped_receptor_noH_pdb=prepped_receptor_noH_pdb,
        )

        return ([chimerax, "--nogui"], stdin)
    charge_rec()


    if cfg.receptors.pocket_option == "reference":
        @shell(cfg)
        def generate_site_from_reference():
            if cfg.receptors.reference is None:
                raise ValueError("common.reference is required when pocket_option is 'reference'")
            return ([cfg.libs.obabel, cfg.receptors.reference, "-O", f"{name}_pocket.mol2"], None)
        generate_site_from_reference()
    else:
        @base(cfg, "generate_site()")
        def generate_site():
            pocket_selection = cfg.receptors.pocket_selection
            if pocket_selection is None:
                raise ValueError("common.pocket_selection is required when pocket_option is 'selection'")

            import pymol2
            with pymol2.PyMOL() as pymol:
                pymol.start()
                pymol.cmd.load(prepped_receptor_noH_pdb, "target")
                pymol.cmd.select("to_delete", f"target and not ({pocket_selection})")
                pymol.cmd.remove("to_delete")
                pymol.cmd.save(f"{name}_pocket.mol2", "target")

            return None
        generate_site()


    @shell(cfg)
    def writedms():
        chimera = cfg.libs.chimera
        with open(Path(__file__).resolve().parents[0] / "templates" / "write_dms_template.py") as f:
            write_dms_template = f.read()

        input_file = Template(write_dms_template).substitute(prepped_receptor_noH_mol2=prepped_receptor_noH_mol2,
                                                                name=name)
        with open(f"{name}_write_dms.py", "w") as file:
            file.write(input_file)

        return (["env", 
                "LD_PRELOAD=/usr/lib64/libz.so.1:/usr/lib64/libfreetype.so.6", 
                "LD_LIBRARY_PATH=/usr/local/chem.sw/chimera/chimera-1.8/lib",
                chimera,
                "--nogui", f"{name}_write_dms.py"], None)
    writedms()
    

    def spheres():
        import subprocess
        import shutil
        with open(Path(__file__).resolve().parents[0] / "templates" / "INSPH_template.txt") as f:
            INSPH_template = f.read()

        wd = cfg.common.working_dir
        cwd = Path(wd / f"tmp_ss_{name}")
        cwd.mkdir(parents=True, exist_ok=True)

        input_file = Template(INSPH_template).substitute(name=name)
        with open(cwd/"INSPH", "w") as file:
            file.write(input_file)

        shutil.copy2(wd/f"{name}_rec.dms",cwd/f"{name}_rec.dms")
        cmd = [dock_home/"bin"/"sphgen", "-i", "INSPH", "-o", "OUTSPH"]
        subprocess.run(cmd, cwd=cwd, text=True, check=True)

        radius = str(cfg.dock6.radius)
        shutil.copy2(wd/f"{name}_pocket.mol2",cwd/f"{name}_pocket.mol2")
        cmd = [dock_home/"bin"/"sphere_selector", f"{name}_rec.sph", f"{name}_pocket.mol2", radius]
        subprocess.run(cmd, cwd=cwd, text=True, check=True)

        ss = cwd / "selected_spheres.sph"
        named_ss = wd / f"{name}_selected_spheres.sph"

        if ss.exists():
            ss.rename(named_ss)
        shutil.rmtree(cwd)
    spheres()


    @shell(cfg)
    def showbox():
        padding = cfg.common.padding
        stdin = f"Y\n{padding}\n{name}_selected_spheres.sph\n1\n{name}_rec_box.pdb\n"
        return ([dock_home/"bin"/"showbox"], stdin)
    showbox()


    @shell(cfg)
    def grid():
        with open(Path(__file__).resolve().parents[0] / "templates" / "grid_template.txt") as f:
            grid_template = f.read()

        input_file = Template(grid_template).substitute(prepped_receptor=prepped_receptor_mol2, 
                                                        dock_home=dock_home,
                                                        name=name)
        with open(f"{name}_grid.in", "w") as file:
            file.write(input_file)

        return ([dock_home/"bin"/"grid", "-i", f"{name}_grid.in", "-o", f"{name}_grid.out"], None)
    grid()

    return Dock6ReceptorBundle(
        receptor=Path(prepped_receptor_mol2),
        selected_spheres=Path(f"{name}_selected_spheres.sph"),
        name=name,
    )


from compdd.executors.python_parallel import python_parallel
from compdd.utils.main_tracker import main_tracker
from compdd.utils.extract_files import extract_files
from functools import partial


def dock6_prep_rec(cfg):
    @main_tracker(cfg, "Prepare receptor for DOCK6")
    @python_parallel(cfg, "prep_rec()")
    def _run():
        receptors = extract_files(cfg.receptors.pdbs, ".pdb")
        tasks = []
        for receptor in receptors:
            tasks.append(partial(_prep_rec, cfg, receptor))
        return tasks
    return _run()
