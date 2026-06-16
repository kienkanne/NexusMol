from nexus.core.executors.shell import shell
from nexus.md.build.build_config import BuildConfig


def _run_pdb4amber(cfg: BuildConfig):
    receptor = cfg.common.receptor
    scratch_dir = cfg._global.path.scratch_dir
    
    receptor_renamed = scratch_dir / (f"{receptor.stem}_renamed.pdb")
    cmd = ["pdb4amber", "-i", str(receptor), "-o", str(receptor_renamed)]

    with shell(cmd):
        pass

    return receptor_renamed
