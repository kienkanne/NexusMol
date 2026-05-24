from pathlib import Path
from string import Template

from nexus.core.executors.gnu_parallel import gnu_parallel
from nexus.core.trackers.main_tracker import main_tracker


def _build_dock6_docking_commands(dcfg, pairs):
    dock_home = dcfg.libs.dock_home
    max_orientations = dcfg.dock6.max_orientations
    working_dir = dcfg.common.working_dir

    mode = getattr(dcfg.common, "mode", "mix")

    out_files = []
    cmds = []

    for receptor_bundle, prepped_lig in pairs:
        selected_spheres = receptor_bundle.selected_spheres
        grid_prefix = receptor_bundle.grid_prefix
        receptor_name = receptor_bundle.name
        required_files = [f"{grid_prefix}.in", f"{grid_prefix}.bmp", f"{grid_prefix}.nrg", f"{grid_prefix}.out"]
        missing_files = [file_name for file_name in required_files if not Path(file_name).is_file()]

        if missing_files:
            raise FileNotFoundError(f"Missing required files in '{dcfg.common.working_dir}': {', '.join(missing_files)}")

        with open(Path(__file__).resolve().parents[0] / "templates" / "flex_template.txt") as f:
            flex_template = f.read()

        #ligand_name = _strip_prepared_suffix(prepped_lig, suffix)
        ligand_name = prepped_lig.stem
        if mode == "match":
            output_prefix = f"{ligand_name}"
        else:
            output_prefix = f"{receptor_name}_{ligand_name}"

        output_path = working_dir / f"{output_prefix}_scored.mol2"
        out_files.append(output_path)

        input_file = Template(flex_template).substitute(
            prepped_lig=prepped_lig,
            dock_home=dock_home,
            selected_spheres=str(selected_spheres),
            grid_prefix=str(grid_prefix),
            receptor_name=receptor_name,
            max_orientations=max_orientations,
        )

        flex = working_dir / f"flex_{output_prefix}.in"
        with open(flex, "w") as file:
            file.write(input_file)

        cmds.append([dock_home / "bin" / "dock6", "-i", flex, "-o", output_path])

    return out_files, cmds


def dock6_docking(dcfg, pairs):
    out_files = []

    @main_tracker(dcfg, "Batch docking with DOCK6")
    @gnu_parallel(dcfg.common.n_jobs, title="dock6_docking()", skip=True)
    def _run():
        nonlocal out_files
        out_files, cmds = _build_dock6_docking_commands(dcfg, pairs)
        return cmds

    _run()
    return out_files
