import shutil
from pathlib import Path
from nexus.core.trackers.main_tracker import main_tracker, final_copy_trackers
from nexus.md.md_config import MDConfig

@main_tracker("Copying to results")
def final_copy(mcfg: MDConfig, outputs):
    prmtop = mcfg.common.prmtop

    results_dir = mcfg.common.results_dir

    shutil.copy2(prmtop, results_dir)

    for (prod_nc, prod_ncrst, prod_out) in outputs:
        shutil.copy2(prod_nc, results_dir)
        shutil.copy2(prod_ncrst, results_dir)
        shutil.copy2(prod_out, results_dir)
        
        # Safely delete trajectory in artifacts
        if Path(results_dir / Path(prod_nc).name).is_file():
            Path(prod_nc).unlink(missing_ok=True)

    final_copy_trackers(results_dir)

    return True
