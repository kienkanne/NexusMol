from pathlib import Path
from string import Template
from compdd.ligands._ligands_common import _strip_prepared_suffix
from compdd.executors.gnu_parallel import gnu_parallel
from compdd.utils.main_tracker import main_tracker


def _to_path(item):
    if hasattr(item, "receptor"):
        return Path(item.receptor)
    if isinstance(item, (list, tuple)) and item:
        return Path(item[0])
    return Path(item)


def _selected_spheres_path(item):
    if hasattr(item, "selected_spheres"):
        return Path(item.selected_spheres)
    if isinstance(item, (list, tuple)) and len(item) > 1:
        return Path(item[1])
    return Path(item)


def _build_dock6_docking_commands(cfg, pairs):
    dock_home = cfg.libs.dock_home
    max_orientations = cfg.dock6.max_orientations
    suffix = cfg.common.prepared_suffix
    mode = getattr(cfg.common, "mode", "mix")

    out_files = []
    cmds = []

    for receptor_bundle, prepped_lig in pairs:
        selected_spheres = _selected_spheres_path(receptor_bundle)
        receptor_name = Path(selected_spheres).stem
        if receptor_name.endswith("_selected_spheres"):
            receptor_name = receptor_name[: -len("_selected_spheres")]
        grid_prefix = f"{receptor_name}_grid"
        required_files = [f"{grid_prefix}.in", f"{grid_prefix}.bmp", f"{grid_prefix}.nrg", f"{grid_prefix}.out"]
        missing_files = [file_name for file_name in required_files if not Path(file_name).is_file()]

        if missing_files:
            raise FileNotFoundError(f"Missing required files in '{cfg.common.working_dir}': {', '.join(missing_files)}")

        with open(Path(__file__).resolve().parents[0] / "templates" / "flex_template.txt") as f:
            flex_template = f.read()

        ligand_name = _strip_prepared_suffix(prepped_lig, suffix)
        if mode == "match":
            output_prefix = f"{ligand_name}"
        else:
            output_prefix = f"{receptor_name}_{ligand_name}"

        out_files.append(f"{output_prefix}_scored.mol2")

        input_file = Template(flex_template).substitute(
            prepped_lig=prepped_lig,
            dock_home=dock_home,
            selected_spheres=str(selected_spheres),
            output_prefix=output_prefix,
            receptor_name=receptor_name,
            max_orientations=max_orientations,
        )
        with open(f"flex_{output_prefix}.in", "w") as file:
            file.write(input_file)

        cmds.append([dock_home / "bin" / "dock6", "-i", f"flex_{output_prefix}.in"])

    return out_files, cmds


def dock6_docking(cfg, lig_files_or_pairs, selected_spheres=None):
    if selected_spheres is not None:
        pairs = [(selected_spheres, prepped_lig) for prepped_lig in lig_files_or_pairs]
    else:
        pairs = lig_files_or_pairs

    out_files = []

    @main_tracker(cfg, "Batch docking with DOCK6")
    @gnu_parallel(cfg, "dock6_docking()")
    def _run():
        nonlocal out_files
        out_files, cmds = _build_dock6_docking_commands(cfg, pairs)
        return cmds

    _run()
    return out_files
