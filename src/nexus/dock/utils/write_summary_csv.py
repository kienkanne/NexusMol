import csv
import math
from pathlib import Path
from nexus.core.executors.base import base
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


def write_summary_csv(dcfg, out_files, rec_bundles):

    @main_tracker(dcfg, "Write summary csv")
    @base(dcfg)
    def _run():
        project_name = dcfg.common.project_name
        max_poses = dcfg.common.max_poses
        working_dir = dcfg.common.working_dir

        # Determine mode: mix -> per-receptor CSVs, match -> single CSV
        mode = getattr(dcfg.common, "mode", "mix")

        written = []

        if mode == "mix":
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
                rows = []
                for out in files:
                    lig_name = Path(out).stem.replace(f"{rec}_", "").replace("_scored", "")
                    scores = parse_scores(out, max_poses, dcfg.common.program)
                    rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

                def pose1_sort(row):
                    score = row[1] if len(row) > 1 else ""
                    return float(score) if score != "" else math.inf

                rows = sorted(rows, key=pose1_sort)
                csv_name = working_dir / f"{project_name}_{rec}_docking_summary.csv"
                with open(csv_name, "w", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(headers)
                    writer.writerows(rows)
                written.append(csv_name)

        else:  # match mode -> single CSV with all outputs
            rows = []
            headers = ["name"] + [f"pose{i}" for i in range(1, max_poses + 1)]

            for out in out_files:
                # name should be the bundle/ligand name
                lig_name = Path(out).stem.replace("_scored", "")
                scores = parse_scores(out, max_poses, dcfg.common.program)
                rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

            def pose1_sort(row):
                score = row[1] if len(row) > 1 else ""
                return float(score) if score != "" else math.inf

            rows = sorted(rows, key=pose1_sort)
            csv_name = working_dir / f"{project_name}_docking_summary.csv"
            with open(csv_name, "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)
            written.append(csv_name)

        return written
    return _run()
