import shutil
from pathlib import Path
from compdd.executors.base import base
from compdd.utils.main_tracker import main_tracker


def _copy_to_results(cfg, prepped_rec, out_files):
    @main_tracker(cfg, "Copy to results")
    @base(cfg)
    def _run():
        working_dir = cfg.common.working_dir
        results_dir = cfg.common.results_dir

        results_dir.mkdir(parents=True, exist_ok=True)
        Path(results_dir / "poses").mkdir(parents=True, exist_ok=True)   
        for file in out_files:
            src = working_dir / file
            dst = results_dir / "poses" / file
            shutil.copy2(src, dst)

            selected_copy = [
                prepped_rec,
                "rec_box.pdb",
                "run.log",
                "manifest.json",
                "state.json"
            ]

            for file in selected_copy:
                src = working_dir / file
                dst = results_dir / file
                shutil.copy2(src, dst)
    _run()