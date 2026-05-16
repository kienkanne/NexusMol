from pathlib import Path
from compdd.executors.gnu_parallel import gnu_parallel
from compdd.utils.main_tracker import main_tracker


def _vina_docking(cfg, lig_files, prepped_rec, vina_config):

    lig_names = []
    out_files = []

    @main_tracker(cfg, "Batch docking with Vina")
    @gnu_parallel(cfg, "vina_docking()")
    def _run():
        vina = cfg.libs.vina

        cmds = []
        for prepped_lig in lig_files:
            receptor_name = Path(prepped_rec).stem.replace("_prepped", "")
            ligand_name = Path(prepped_lig).stem.replace("_prepped", "")
            output_name = f"{receptor_name}_{ligand_name}_scored.pdbqt"

            lig_names.append(ligand_name)
            out_files.append(output_name)

            cmds.append([vina, 
                              "--receptor", prepped_rec, 
                              "--ligand", prepped_lig, 
                              "--config", vina_config,
                              "--out", output_name])

        return cmds
    _run()

    return out_files, lig_names