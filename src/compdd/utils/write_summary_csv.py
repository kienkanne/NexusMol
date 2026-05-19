import csv
import math
from pathlib import Path
from compdd.executors.base import base
from compdd.utils.main_tracker import main_tracker


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


def write_summary_csv(cfg, out_files, prepped_recs=None):

    @main_tracker(cfg, "Write summary csv")
    @base(cfg)
    def _run():
        project_name = cfg.common.project_name
        max_poses = cfg.common.max_poses

        # Determine mode: mix -> per-receptor CSVs, match -> single CSV
        mode = getattr(cfg.common, "mode", "mix")

        def _receptor_name_from_item(item):
            from compdd.ligands._ligands_common import _strip_prepared_suffix
            if hasattr(item, "name"):
                return item.name
            # item might be a path or tuple(bundle, config)
            path = Path(item.receptor) if hasattr(item, "receptor") else (Path(item[0]) if isinstance(item, (list, tuple)) else Path(item))
            return _strip_prepared_suffix(path, cfg.common.prepared_suffix)

        written = []

        if mode == "mix":
            # Group out_files by receptor name derived from prepped_recs
            if prepped_recs is None:
                raise ValueError("prepped_recs is required for mix mode")

            rec_names = [_receptor_name_from_item(r) for r in prepped_recs]
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
                    scores = parse_scores(out, max_poses, cfg.common.program)
                    rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

                def pose1_sort(row):
                    score = row[1] if len(row) > 1 else ""
                    return float(score) if score != "" else math.inf

                rows = sorted(rows, key=pose1_sort)
                csv_name = f"{project_name}_{rec}_docking_summary.csv"
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
                scores = parse_scores(out, max_poses, cfg.common.program)
                rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

            def pose1_sort(row):
                score = row[1] if len(row) > 1 else ""
                return float(score) if score != "" else math.inf

            rows = sorted(rows, key=pose1_sort)
            csv_name = f"{project_name}_docking_summary.csv"
            with open(csv_name, "w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)
            written.append(csv_name)

        return written
    return _run()
