import shutil
from pathlib import Path
from nexus.core.trackers.main_tracker import main_tracker, final_copy_trackers


@main_tracker("Final copy to results")
def final_copy(dcfg, rec_bundles, written_scores, written_clusters, out_files):
    working_dir = dcfg.common.working_dir
    results_dir = dcfg.common.results_dir

    results_dir.mkdir(parents=True, exist_ok=True)

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

    # Copy csv files to respective receptor dirs or to root
    csv_paths_dict = {} # Used to add to metadata

    if isinstance(written_scores, (list, tuple)):
        for csv in written_scores:
            for rec in rec_names:
                if rec in str(csv.stem):
                    src = working_dir / csv
                    dst = results_dir / rec / Path(csv).name
                    if src.exists():
                        shutil.copy2(src, dst)
                        
                    csv_paths_dict[f"{rec}_scores"] = dst
                    break

    if isinstance(written_clusters, (list, tuple)):
        for csv in written_clusters:
            for rec in rec_names:
                if rec in str(csv.stem):
                    src = working_dir / csv
                    dst = results_dir / rec / Path(csv).name
                    if src.exists():
                        shutil.copy2(src, dst)
                        
                    csv_paths_dict[f"{rec}_clusters"] = dst
                    break                

    for name, csv_path in csv_paths_dict.items():
        setattr(dcfg.metadata, name, str(csv_path))

    final_copy_trackers(results_dir)

    # Finally, dump json meta with csv file paths
    metadata_dict = dcfg.metadata.model_dump() 
    metadata_path = results_dir / f"{dcfg.common.project_name}_metadata.json"

    import json
    if metadata_dict is not None:
        # Serialize the dictionary to a pretty-printed JSON file
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=4)
    
