from pathlib import Path
from string import Template
from compdd.executors.shell import shell
from compdd.executors.base import base
from compdd.vina._write_box import _write_box
from compdd.utils.main_tracker import main_tracker


def _vina_prep_rec(cfg):

    @main_tracker(cfg, "Prepare receptor for Vina")
    def _run():
        receptor = cfg.common.receptor
        name = Path(receptor).stem

        @shell(cfg)
        def charge_rec_chimerax():
            chimerax = cfg.libs.chimerax

            with open(Path(__file__).resolve().parents[0] / "templates" / "vina_charge_rec_template.com") as f:
                vina_charge_rec_template = f.read()     

            stdin = Template(vina_charge_rec_template).substitute(receptor=receptor,name=name)

            return ([chimerax, "--nogui"], stdin)
        charge_rec_chimerax()


        @shell(cfg)
        def charge_rec_mgltools():
            mgltools = cfg.libs.mgltools

            return ([mgltools/"bin"/"pythonsh",
                    mgltools/"MGLToolsPckgs"/"AutoDockTools"/"Utilities24"/"prepare_receptor4.py",
                    "-r", f"{name}_prepped.pdb",
                    "-o", f"{name}_prepped.pdbqt",
                    ], None)
        charge_rec_mgltools()


        @base(cfg, "generate_box()")
        def generate_box():
            padding = cfg.common.padding
            pocket_selection = cfg.common.pocket_selection
            cpu = cfg.vina.cpu
            exhaustiveness = cfg.vina.exhaustiveness
            num_modes = cfg.vina.num_modes

            with open(Path(__file__).resolve().parents[0] / "templates" / "vina_config_template.txt") as f:
                vina_config_template = f.read()

            import pymol2
            import numpy as np
            with pymol2.PyMOL() as pymol:
                pymol.start()
                pymol.cmd.load(f"{name}_prepped.pdbqt", "receptor")
                stored = {"xyz": []}
                pymol.cmd.iterate_state(
                    1,
                    f"({pocket_selection}) and not hydro",
                    "xyz.append([x,y,z])",
                    space=stored
                )

                coords = np.array(stored["xyz"])
                minv = coords.min(axis=0)
                maxv = coords.max(axis=0)
                size = (maxv - minv) + padding
                center = (minv + maxv) / 2

                if len(coords) == 0:
                    raise ValueError(f"No atoms matched selection:\n{pocket_selection}")

                vina_config = Template(vina_config_template).substitute(
                    center_x=center[0],center_y=center[1],center_z=center[2],
                    size_x=size[0],size_y=size[1],size_z=size[2],
                    cpu=cpu,
                    exhaustiveness=exhaustiveness,
                    num_modes=num_modes
                )
                with open("vina_config.txt", "w") as file:
                    file.write(vina_config)

                if cfg.vina.write_box:
                    _write_box(center, size)
        generate_box()

        return f"{name}_prepped.pdbqt", "vina_config.txt"

    return _run()