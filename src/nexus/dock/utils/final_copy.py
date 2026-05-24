import shutil
from pathlib import Path
from nexus.core.executors.base import base


def final_copy(dcfg, rec_bundles, docking_summary, out_files):
    @base(dcfg.common.logger, title="final_copy()")
    def _run():

        logger = dcfg.common.logger
        manifest = dcfg.common.manifest
        manifest.finalize(success=True)
        logger.info("Pipeline completed")

        working_dir = dcfg.common.working_dir
        results_dir = dcfg.common.results_dir

        results_dir.mkdir(parents=True, exist_ok=True)

        mode = getattr(dcfg.common, "mode", "mix")

        if mode == "mix":
            rec_names = [r.name for r in rec_bundles]
            groups = {name: [] for name in rec_names}
            for out in out_files:
                stem = Path(out).stem
                for rec in rec_names:
                    if stem.startswith(f"{rec}_"):
                        groups[rec].append(out)
                        break

            # Copy per-receptor
            for item, rec_name in zip(rec_bundles, rec_names):
                rec_dir = results_dir / rec_name
                (rec_dir / "poses").mkdir(parents=True, exist_ok=True)

                # copy outputs
                for out in groups.get(rec_name, []):
                    src = working_dir / out
                    dst = rec_dir / "poses" / Path(out).name
                    if src.exists():
                        shutil.copy2(src, dst)

                # copy receptor file
                rec_path = item.receptor
                if rec_path.exists():
                    shutil.copy2(rec_path, rec_dir / rec_path.name)

                # copy receptor-specific config if present on bundle
                pocket = None
                if hasattr(item, "pocket"):
                    pocket = item.pocket
                if pocket and pocket.exists():
                    shutil.copy2(pocket, rec_dir)

            # copy docking summary files to respective receptor dirs or to root
            if isinstance(docking_summary, (list, tuple)):
                for csv in docking_summary:
                    for rec in rec_names:
                        if rec in str(csv.stem):
                            src = working_dir / csv
                            dst = results_dir / rec / Path(csv).name
                            if src.exists():
                                shutil.copy2(src, dst)
                            break

            # copy run artifacts to root
            root_files = ["run.log", "manifest.json", "state.json"]
            for f in root_files:
                src = working_dir / f
                dst = results_dir / f
                if src.exists():
                    shutil.copy2(src, dst)

        else:  # match mode -> single csv and a 'details' folder with everything
            details = results_dir / "details"
            details.mkdir(parents=True, exist_ok=True)
            (details / "poses").mkdir(parents=True, exist_ok=True)

            # copy all outputs into details/poses
            for out in out_files:
                src = working_dir / out
                dst = details / "poses" / Path(out).name
                if src.exists():
                    shutil.copy2(src, dst)

            # copy all receptors and configs into details
            for item in rec_bundles:
                rec_path = rec_bundles.receptor
                if rec_path.exists():
                    shutil.copy2(rec_path, details / rec_path.name)
                # possible config fields
                if hasattr(item, "pocket"):
                    pocket = item.pocket
                    if pocket.exists():
                        shutil.copy2(pocket, details)
                if hasattr(item, "selected_spheres"):
                    sp = Path(item.selected_spheres)
                    if sp.exists():
                        shutil.copy2(sp, details / sp.name)

            # copy single csv to root as summary
            if isinstance(docking_summary, (list, tuple)):
                # pick first
                csv = docking_summary[0] if docking_summary else None
            else:
                csv = docking_summary
            if csv:
                src = working_dir / csv
                dst = results_dir / Path(csv).name
                if src.exists():
                    shutil.copy2(src, dst)

            # also copy run artifacts into root
            for f in ["run.log", "manifest.json", "state.json"]:
                src = working_dir / f
                dst = results_dir / f
                if src.exists():
                    shutil.copy2(src, dst)
    _run()