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


def write_summary_csv(cfg, out_files):

    @main_tracker(cfg, "Write summary csv")
    @base(cfg)
    def _run():
        project_name = cfg.common.project_name
        receptor_name = Path(cfg.receptors.pdb).stem
        max_poses = cfg.common.max_poses

        rows = []
        
        # outfiles = ["..._scored.mol2/pdbqt", ...]
        lig_names = [Path(outfile).stem.replace("_scored", "") for outfile in out_files]

        for out_file, lig_name in zip(out_files, lig_names):
            scores = parse_scores(out_file, max_poses, cfg.common.program)
            rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

        headers = ["name"] + [f"pose{i}" for i in range(1, max_poses + 1)]

        def pose1_sort(row):
            score = row[1] if len(row) > 1 else ""
            return float(score) if score != "" else math.inf

        rows = sorted(rows, key=pose1_sort)
        with open(f"{project_name}_{receptor_name}_docking_summary.csv", "w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(rows)

        return f"{project_name}_{receptor_name}_docking_summary.csv"
    return _run()
