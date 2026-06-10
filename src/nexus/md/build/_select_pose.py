from pathlib import Path
from nexus.md.build.build_config import BuildConfig
from nexus.core.executors.shell import shell


def _select_pose(cfg: BuildConfig):
    ligand = cfg.ligand.ligand
    pose_num = cfg.ligand.pose_num
    scratch_dir = cfg._global.path.scratch_dir

    ligand_name = scratch_dir / ligand.stem

    m_cmd = ["obabel", str(ligand), "-O", f"{ligand_name}_pose_.mol2", "-m"]
    
    with shell(m_cmd):
        pass
    
    ligand_pose = f"{ligand_name}_pose_{pose_num}.mol2"
    with_h = f"{ligand_name}_pose_{pose_num}_with_H.mol2"

    h_cmd = ["obabel", ligand_pose, "-O", with_h, "-h"]

    with shell(h_cmd):
        pass

    return Path(with_h)
