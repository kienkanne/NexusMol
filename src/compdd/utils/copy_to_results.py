import shutil
from pathlib import Path
from compdd.executors.base import base


def _to_path(item):
    if hasattr(item, "receptor"):
        return Path(item.receptor)
    if isinstance(item, (list, tuple)) and item:
        return Path(item[0])
    return Path(item)


def copy_to_results(cfg, prepped_rec, docking_summary, out_files, others=None):
    @base(cfg, "copy_to_results()")
    def _run():

        logger = cfg.common.logger
        manifest = cfg.common.manifest
        manifest.finalize(success=True)
        logger.info("Pipeline completed")

        working_dir = cfg.common.working_dir
        results_dir = cfg.common.results_dir

        results_dir.mkdir(parents=True, exist_ok=True)
        Path(results_dir / "poses").mkdir(parents=True, exist_ok=True)

        for file in out_files:
            src = working_dir / file
            dst = results_dir / "poses" / file
            shutil.copy2(src, dst)

        selected_copy = []
        if isinstance(prepped_rec, (list, tuple)):
            for item in prepped_rec:
                selected_copy.append(str(_to_path(item)))
        else:
            selected_copy.append(str(_to_path(prepped_rec)))

        selected_copy.extend([
            docking_summary,
            "run.log",
            "manifest.json",
            "state.json",
        ])

        if others is not None:
            for f in others:
                selected_copy.append(str(f))

        for file in selected_copy:
            src = working_dir / file
            dst = results_dir / file
            shutil.copy2(src, dst)
    _run()