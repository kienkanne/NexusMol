from pathlib import Path
from string import Template
from compdd.executors.shell import shell
from compdd.executors.base import base
from compdd.utils.main_tracker import main_tracker


def _dock6_prep_rec(cfg):
    @main_tracker(cfg, "Prepare receptor for DOCK 6")
    def _run():
        dock_home = cfg.libs.dock_home
        receptor = cfg.common.receptor
        name = Path(receptor).stem

        @shell(cfg)
        def charge_rec():
            chimerax = cfg.libs.chimerax

            with open(Path(__file__).resolve().parents[0] / "templates" / "dock6_charge_rec_template.com") as f:
                dock6_charge_rec_template = f.read()     

            stdin = Template(dock6_charge_rec_template).substitute(receptor=receptor,name=name)

            return ([chimerax, "--nogui"], stdin)
        charge_rec()


        @base(cfg, "generate_site()")
        def generate_site():
            pocket_selection = cfg.common.pocket_selection

            import pymol2
            with pymol2.PyMOL() as pymol:
                pymol.start()
                pymol.cmd.load(f"{name}_prepped_noH.pdb", "target")
                pymol.cmd.select("to_delete", f"target and not ({pocket_selection})")
                pymol.cmd.remove("to_delete")
                pymol.cmd.save("binding_site.mol2", "target")

            return None
        generate_site()


        @shell(cfg)
        def writedms():
            chimera = cfg.libs.chimera
            with open(Path(__file__).resolve().parents[0] / "templates" / "write_dms_template.py") as f:
                write_dms_template = f.read()

            input_file = Template(write_dms_template).substitute(name=f"{name}_prepped_noH.mol2")
            with open("write_dms.py", "w") as file:
                file.write(input_file)

            return (["env", 
                    "LD_PRELOAD=/usr/lib64/libz.so.1:/usr/lib64/libfreetype.so.6", 
                    "LD_LIBRARY_PATH=/usr/local/chem.sw/chimera/chimera-1.8/lib",
                    chimera,
                    "--nogui", "write_dms.py"], None)
        writedms()
        

        @shell(cfg)
        def sphgen():
            with open(Path(__file__).resolve().parents[0] / "templates" / "INSPH_template.txt") as f:
                INSPH_template = f.read()

            input_file = Template(INSPH_template).substitute()
            with open("INSPH", "w") as file:
                file.write(input_file)

            return ([dock_home/"bin"/"sphgen", "-i", "INSPH", "-o", "OUTSPH"], None)
        sphgen()


        @shell(cfg)
        def sphere_selector():
            radius = str(cfg.dock6.radius)
            return ([dock_home/"bin"/"sphere_selector", "rec.sph", "binding_site.mol2", radius], None)
        sphere_selector()


        @shell(cfg)
        def showbox():
            padding = cfg.common.padding
            stdin = f"Y\n{padding}\nselected_spheres.sph\n1\nrec_box.pdb\n"
            return ([dock_home/"bin"/"showbox"], stdin)
        showbox()


        @shell(cfg)
        def grid():
            with open(Path(__file__).resolve().parents[0] / "templates" / "grid_template.txt") as f:
                grid_template = f.read()

            input_file = Template(grid_template).substitute(prepped_receptor=f"{name}_prepped.mol2", dock_home=dock_home)
            with open("grid.in", "w") as file:
                file.write(input_file)

            return ([dock_home/"bin"/"grid", "-i", "grid.in", "-o", "grid.out"], None)
        grid()

        return f"{name}_prepped.mol2" "selected_spheres.sph"

    return _run()