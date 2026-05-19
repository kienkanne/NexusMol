from pathlib import Path

from compdd.ligands._ligands_common import _strip_prepared_suffix
from compdd.executors.gnu_parallel import gnu_parallel
from compdd.utils.main_tracker import main_tracker


def _to_path(item):
    if hasattr(item, "receptor"):
        return Path(item.receptor)
    if isinstance(item, (list, tuple)) and item:
        return Path(item[0])
    return Path(item)


def _vina_config_path(item):
    if hasattr(item, "vina_config"):
        return Path(item.vina_config)
    if isinstance(item, (list, tuple)) and len(item) > 1:
        return Path(item[1])
    raise ValueError("Unable to extract Vina config path from receptor bundle")


def _build_vina_docking_commands(cfg, pairs):
    vina = cfg.libs.vina
    suffix = cfg.common.prepared_suffix

    out_files = []
    cmds = []

    for prepped_rec, prepped_lig in pairs:
        receptor_path = _to_path(prepped_rec)
        vina_config = _vina_config_path(prepped_rec)
        receptor_name = _strip_prepared_suffix(str(receptor_path), suffix)
        ligand_name = _strip_prepared_suffix(prepped_lig, suffix)
        output_name = f"{receptor_name}_{ligand_name}_scored.pdbqt"

        out_files.append(output_name)
        cmds.append([
            vina,
            "--receptor", str(receptor_path),
            "--ligand", str(prepped_lig),
            "--config", str(vina_config),
            "--out", output_name,
        ])

    return out_files, cmds


def vina_docking(cfg, prepped_ligs_or_pairs, prepped_rec=None, vina_config=None):
    if prepped_rec is not None:
        pairs = [(prepped_rec, prepped_lig) for prepped_lig in prepped_ligs_or_pairs]
    else:
        pairs = prepped_ligs_or_pairs

    out_files = []

    @main_tracker(cfg, "Batch docking with Vina")
    @gnu_parallel(cfg, "vina_docking()")
    def _run():
        nonlocal out_files
        out_files, cmds = _build_vina_docking_commands(cfg, pairs)
        return cmds

    _run()
    return out_files
