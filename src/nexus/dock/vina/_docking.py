from nexus.core.executors.gnu_parallel import gnu_parallel
from nexus.core.trackers.main_tracker import main_tracker


def _build_vina_docking_commands(dcfg, pairs):
    working_dir = dcfg.common.working_dir
    mode = getattr(dcfg.common, "mode", "mix")

    out_files = []
    cmds = []

    for receptor_bundle, prepped_lig in pairs:
        receptor_path = receptor_bundle.receptor
        vina_config = receptor_bundle.vina_config
        receptor_name = receptor_bundle.name
        ligand_name = prepped_lig.stem
        if mode == "match":
            # receptor and ligand share the same name; produce single-name outputs
            output_prefix = f"{ligand_name}"
        else:
            output_prefix = f"{receptor_name}_{ligand_name}"

        output_path = working_dir / f"{output_prefix}_scored.pdbqt"

        out_files.append(output_path)
        cmds.append([
            "vina",
            "--receptor", str(receptor_path),
            "--ligand", str(prepped_lig),
            "--config", str(vina_config),
            "--out", output_path,
        ])

    return out_files, cmds


def vina_docking(dcfg, prepped_ligs_or_pairs, prepped_rec=None, vina_config=None):
    if prepped_rec is not None:
        pairs = [(prepped_rec, prepped_lig) for prepped_lig in prepped_ligs_or_pairs]
    else:
        pairs = prepped_ligs_or_pairs

    out_files = []

    @main_tracker(dcfg, "Batch docking with Vina")
    @gnu_parallel(dcfg.common.n_jobs, title="vina_docking()")
    def _run():
        nonlocal out_files
        out_files, cmds = _build_vina_docking_commands(dcfg, pairs)
        return cmds

    _run()
    return out_files
