import shutil
from pathlib import Path
from nexus.core.trackers.main_tracker import main_tracker, final_copy_trackers
import pickle
import pandas as pd
from nexus.dock.dock_config import DockConfig


@main_tracker("Final copy to results")
def final_copy(cfg: DockConfig, rec_bundles, master_df: pd.DataFrame, out_files):
    scratch_dir = cfg._global.path.scratch_dir
    output_dir = cfg.common.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

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
        rec_dir = output_dir / rec_name
        (rec_dir / "poses").mkdir(parents=True, exist_ok=True)

        # copy outputs
        for out in groups.get(rec_name, []):
            src = scratch_dir / out
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

    final_copy_trackers(output_dir)

    with open(output_dir / f"{cfg.common.job_name}_master_df.pkl", "wb") as f:
        pickle.dump(master_df, f)

    # Drop the molecule object to save a csv version
    master_df = master_df.drop(columns=[("Molecule", "Ligand_Mol")])
    master_df_csv_path = str(output_dir / f"{cfg.common.job_name}_master_df.csv")

    master_df.to_csv(master_df_csv_path, index=False)

    # Finally, dump json meta with csv file paths
    metadata_dict = cfg.metadata.model_dump()
    metadata_dict["master_df_csv"] = master_df_csv_path

    metadata_path = output_dir / f"{cfg.common.job_name}_metadata.json"

    import json
    if metadata_dict is not None:
        # Serialize the dictionary to a pretty-printed JSON file
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=4)
    