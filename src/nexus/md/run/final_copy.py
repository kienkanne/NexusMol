import shutil
from pathlib import Path
from nexus.core.trackers.main_tracker import main_tracker, final_copy_trackers
from nexus.md.run.md_config import MDConfig

@main_tracker("Copying to results")
def final_copy(cfg: MDConfig, outputs):
    prmtop = cfg.common.prmtop

    output_dir = cfg.common.output_dir

    shutil.copy2(prmtop, output_dir)

    for (prod_nc, prod_ncrst, prod_out) in outputs:
        shutil.copy2(prod_nc, output_dir)
        shutil.copy2(prod_ncrst, output_dir)
        shutil.copy2(prod_out, output_dir)
        
        # Safely delete trajectory in artifacts
        if Path(output_dir / Path(prod_nc).name).is_file():
            Path(prod_nc).unlink(missing_ok=True)

    final_copy_trackers(output_dir)

    return True
