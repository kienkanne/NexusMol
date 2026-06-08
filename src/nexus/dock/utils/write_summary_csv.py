import csv
import numpy as np
from pathlib import Path
import pandas as pd

from nexus.dock.utils._compute_clusters import compute_clusters
from nexus.core.trackers.main_tracker import main_tracker


def parse_scores(output, max_poses, program):
    scores = []

    with open(output) as handle:
        for line in handle:

            if program == "dock6" and "Grid_Score" in line:
                score = line.split("Grid_Score:", 1)[1].split()[0]
                scores.append(score)

            elif program == "vina" and "REMARK VINA RESULT" in line:
                score = line.split(":", 1)[1].split()[0]
                scores.append(score)

            if len(scores) == max_poses:
                break

        if not scores:
            raise ValueError("Invalid program or no out_files")
        
    return scores


def pose1_sort(row):
    score = row[1] if len(row) > 1 else ""
    return float(score) if score != "" else np.inf


@main_tracker("Write summary csv")
def write_summary_csv(dcfg, out_files, rec_bundles):

    project_name = dcfg.common.project_name
    max_poses = dcfg.common.max_poses
    working_dir = dcfg.common.working_dir

    # Initialize list of written scores csv and clusters csv for each receptor
    written_scores = []
    written_clusters = []

    # Group out_files by receptor name derived from rec_bundles
    if rec_bundles is None:
        raise ValueError("rec_bundles is required for mix mode")

    rec_names = [r.name for r in rec_bundles]
    groups = {name: [] for name in rec_names}

    for out in out_files:
        stem = Path(out).stem
        # expect format '{rec}_{lig}_scored'
        for rec in rec_names:
            if stem.startswith(f"{rec}_"):
                groups[rec].append(out)
                break

    headers = ["name"] + [f"pose{i}" for i in range(1, max_poses + 1)]

    for rec, files in groups.items():
        scores_rows = []
        cluster_results = []

        for out in files:
            # Parse raw scores
            lig_name = Path(out).stem.replace(f"{rec}_", "").replace("_scored", "")
            scores = parse_scores(out, max_poses, dcfg.common.program)
            scores_rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

            # Compute cluster metrics
            compute_clusters(lig_name, out, cluster_results)

        csv_name = f"{project_name}_{rec}"
        scores_csv_name = working_dir / f"Scores_{csv_name}.csv"
        cluster_csv_name = working_dir / f"Clusters_{csv_name}.csv"

        # Write scores csv
        scores_rows = sorted(scores_rows, key=pose1_sort)
        
        with open(scores_csv_name, "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(scores_rows)
        written_scores.append(scores_csv_name)

        # Write clusters csv
        df = pd.DataFrame(cluster_results)

        # Sort by ligand name, then by cluster size (largest clusters at the top)
        df = df.sort_values(by=["ligand_name", "cluster_size"], ascending=[True, False])
        df.to_csv(cluster_csv_name, index=False)

        written_clusters.append(cluster_csv_name)

    return written_scores, written_clusters
