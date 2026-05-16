from pathlib import Path
from string import Template
from compdd.executors.gnu_parallel import gnu_parallel
from compdd.utils.main_tracker import main_tracker


def _dock6_docking(cfg, lig_files, selected_spheres="selected_spheres.sph"):

    lig_names = []
    out_files = []
    
    @main_tracker(cfg, "Batch docking with DOCK 6")
    @gnu_parallel(cfg, "dock6_docking()")
    def _run():
        receptor = cfg.common.receptor
        dock_home = cfg.libs.dock_home
        max_orientations = cfg.dock6.max_orientations

        required_files = ["grid.in", "grid.bmp", "grid.nrg", "grid.out"]
        missing_files = []

        for file_name in required_files:
            if not Path(file_name).is_file():
                missing_files.append(file_name)

        if missing_files:
            raise FileNotFoundError(f"Missing required files in '{cfg.common.working_dir}': {', '.join(missing_files)}")

        cmds = []
        for prepped_lig in lig_files:

            with open(Path(__file__).resolve().parents[0] / "templates" / "flex_template.txt") as f:
                flex_template = f.read()

            receptor_name = Path(receptor).stem
            ligand_name = Path(prepped_lig).stem.replace("_prepped", "")
            output_prefix = f"{receptor_name}_{ligand_name}"

            lig_names.append(ligand_name)
            out_files.append(f"{output_prefix}_scored.mol2")

            input_file = Template(flex_template).substitute(prepped_lig=prepped_lig, 
                                                            dock_home=dock_home,
                                                            selected_spheres=selected_spheres,
                                                            output_prefix=output_prefix, 
                                                            max_orientations=max_orientations)
            with open(f"flex_{ligand_name}.in", "w") as file:
                file.write(input_file)
            
            
            cmds.append([dock_home/"bin"/"dock6", "-i", f"flex_{ligand_name}.in"])

        return cmds
    _run()

    return out_files, lig_names
