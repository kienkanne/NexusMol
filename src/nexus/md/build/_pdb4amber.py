from nexus.prep.prep_config import PrepConfig
from nexus.core.executors.shell import shell


def _run_pdb4amber(receptor, scratch_dir):
    receptor_renamed = scratch_dir / (f"{receptor.stem}_renamed.pdb")
    cmd = ["pdb4amber", "-i", str(receptor), "-o", str(receptor_renamed)]

    with shell(cmd):
        pass

    return receptor_renamed
