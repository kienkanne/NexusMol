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

        mode = getattr(cfg.common, "mode", "mix")

        def _receptor_name_from_item(item):
            if hasattr(item, "name"):
                return item.name
            if hasattr(item, "receptor"):
                return Path(item.receptor).stem.replace(f"_{cfg.common.prepared_suffix}", "")
            if isinstance(item, (list, tuple)) and item:
                return Path(item[0]).stem.replace(f"_{cfg.common.prepared_suffix}", "")
            return Path(item).stem.replace(f"_{cfg.common.prepared_suffix}", "")

        if mode == "mix":
            # Group outputs by receptor
            if not isinstance(prepped_rec, (list, tuple)):
                raise ValueError("prepped_rec must be a list of receptor bundles in mix mode")

            rec_names = [_receptor_name_from_item(r) for r in prepped_rec]
            groups = {name: [] for name in rec_names}
            for out in out_files:
                stem = Path(out).stem
                for rec in rec_names:
                    if stem.startswith(f"{rec}_"):
                        groups[rec].append(out)
                        break

            # Copy per-receptor
            for item, rec in zip(prepped_rec, rec_names):
                rec_dir = results_dir / rec
                (rec_dir / "poses").mkdir(parents=True, exist_ok=True)

                # copy outputs
                for out in groups.get(rec, []):
                    src = working_dir / out
                    dst = rec_dir / "poses" / Path(out).name
                    if src.exists():
                        shutil.copy2(src, dst)

                # copy receptor file
                rec_path = _to_path(item)
                if rec_path.exists():
                    shutil.copy2(rec_path, rec_dir / rec_path.name)

                # copy receptor-specific config if present on bundle
                cfg_path = None
                if hasattr(item, "vina_config"):
                    cfg_path = Path(item.vina_config)
                if hasattr(item, "selected_spheres"):
                    cfg_path = Path(item.selected_spheres)
                if cfg_path and cfg_path.exists():
                    shutil.copy2(cfg_path, rec_dir / cfg_path.name)

            # copy docking summary files to respective receptor dirs or to root
            if isinstance(docking_summary, (list, tuple)):
                for csv in docking_summary:
                    for rec in rec_names:
                        if rec in csv:
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
            if isinstance(prepped_rec, (list, tuple)):
                for item in prepped_rec:
                    rec_path = _to_path(item)
                    if rec_path.exists():
                        shutil.copy2(rec_path, details / rec_path.name)
                    # possible config fields
                    if hasattr(item, "vina_config"):
                        cfgp = Path(item.vina_config)
                        if cfgp.exists():
                            shutil.copy2(cfgp, details / cfgp.name)
                    if hasattr(item, "selected_spheres"):
                        sp = Path(item.selected_spheres)
                        if sp.exists():
                            shutil.copy2(sp, details / sp.name)

            # copy others if given
            if others is not None:
                for f in others:
                    src = working_dir / f
                    dst = details / Path(f).name
                    if src.exists():
                        shutil.copy2(src, dst)

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