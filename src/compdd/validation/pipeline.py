from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import csv

from compdd.configs.docking_config import RootConfig
from compdd.configs.ligands_config import LigandsConfig
from compdd.dock6._dock6_docking import _dock6_docking
from compdd.dock6._dock6_prep_rec import _dock6_prep_rec
from compdd.docking_utils._ligands_prep import _ligands_prep
from compdd.docking_utils._write_summary_csv import parse_scores
from compdd.utils.logging_utils import setup_logger
from compdd.utils.manifest import Manifest
from compdd.utils.runstate import State
from compdd.validation.analysis import calculate_pose_rmsds, ligand_features, summarize_values
from compdd.validation.casf import UnsupportedLigandError, discover_casf_entries, parse_mol2_ligand_id
from compdd.validation.rcsb import RCSBClient
from compdd.vina._vina_docking import _vina_docking
from compdd.vina._vina_prep_rec import _vina_prep_rec


@dataclass(frozen=True)
class EntryTask:
    entry_id: str
    receptor_pdb: str
    pocket_pdb: str
    crystal_ligand_mol2: str
    crystal_ligand_sdf: str | None
    program: str
    config: object


class ValidationPipeline:
    def __init__(self, cfg, program):
        self.cfg = cfg
        self.program = program
        self.output_dir = Path(cfg.common.results_dir)
        self.cache_dir = Path(cfg.common.working_dir) / "rcsb_cache"

    def run(self):
        entries = discover_casf_entries(self.cfg.common.validation_data)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        Path(self.cfg.common.working_dir).mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        tasks = [EntryTask(
            entry_id=entry.entry_id,
            receptor_pdb=str(entry.receptor_pdb),
            pocket_pdb=str(entry.pocket_pdb),
            crystal_ligand_mol2=str(entry.crystal_ligand_mol2),
            crystal_ligand_sdf=str(entry.crystal_ligand_sdf) if entry.crystal_ligand_sdf else None,
            program=self.program,
            config=self.cfg,
        ) for entry in entries]

        results = []
        failures = []
        max_workers = self.cfg.common.n_jobs
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_run_entry_task, task): task for task in tasks}
            for future in as_completed(future_map):
                task = future_map[future]
                try:
                    outcome = future.result()
                except Exception as exc:
                    failures.append(_failure_row(task.entry_id, "unexpected", str(exc)))
                    continue

                if outcome["status"] == "success":
                    results.append(outcome["row"])
                else:
                    failures.append(outcome["row"])

        results = sorted(results, key=lambda row: row["entry_id"])
        failures = sorted(failures, key=lambda row: row["entry_id"])
        _write_results_csv(self.output_dir / "validation_results.csv", results, self.cfg.common.num_analysis)
        _write_failures_csv(self.output_dir / "validation_failures.csv", failures)
        return {
            "results": self.output_dir / "validation_results.csv",
            "failures": self.output_dir / "validation_failures.csv",
            "n_success": len(results),
            "n_failure": len(failures),
        }


def _run_entry_task(task):
    cfg = task.config
    entry_id = task.entry_id

    try:
        ligand_id = parse_mol2_ligand_id(task.crystal_ligand_mol2)
        client = RCSBClient(Path(cfg.common.working_dir) / "rcsb_cache")
        metadata = client.ligand_metadata(entry_id, ligand_id)
        smiles = metadata["smiles"]
        features = ligand_features(smiles)

        entry_work_dir = Path(cfg.common.working_dir) / "entries" / entry_id
        entry_results_dir = Path(cfg.common.results_dir) / "entries" / entry_id
        entry_work_dir.mkdir(parents=True, exist_ok=True)
        entry_results_dir.mkdir(parents=True, exist_ok=True)

        docking_cfg = _build_entry_docking_config(cfg, task, entry_work_dir, entry_results_dir)
        ligands_cfg = _build_entry_ligands_config(cfg, docking_cfg, entry_id, ligand_id, smiles, entry_work_dir)

        lig_files = _ligands_prep(docking_cfg, ligands_cfg)
        if task.program == "vina":
            prepped_rec, vina_config = _vina_prep_rec(docking_cfg)
            out_files = _vina_docking(docking_cfg, lig_files, prepped_rec, vina_config)
        else:
            _, selected_spheres = _dock6_prep_rec(docking_cfg)
            out_files = _dock6_docking(docking_cfg, lig_files, selected_spheres)

        if len(out_files) != 1:
            raise RuntimeError(f"Expected one docking output for {entry_id}, got {len(out_files)}")

        docked_file = entry_work_dir / out_files[0]
        scores = [float(score) for score in parse_scores(docked_file, cfg.common.max_poses, task.program)]
        rmsds = calculate_pose_rmsds(
            smiles=smiles,
            crystal_mol2=task.crystal_ligand_mol2,
            crystal_sdf=task.crystal_ligand_sdf,
            docked_file=docked_file,
            obabel=docking_cfg.libs.obabel,
            work_dir=entry_work_dir / "analysis",
        )

        row = _result_row(
            entry_id=entry_id,
            ligand_id=metadata["ligand_id"],
            smiles=smiles,
            features=features,
            scores=scores,
            rmsds=rmsds,
            num_analysis=cfg.common.num_analysis,
        )
        return {"status": "success", "row": row}

    except UnsupportedLigandError as exc:
        return {"status": "failure", "row": _failure_row(entry_id, "unsupported_ligand", str(exc))}
    except Exception as exc:
        return {"status": "failure", "row": _failure_row(entry_id, "failed", str(exc))}


def _build_entry_docking_config(validation_cfg, task, entry_work_dir, entry_results_dir):
    data = {
        "libs": {field: getattr(validation_cfg.libs, field) for field in validation_cfg.libs.model_fields},
        "common": {
            "project_name": task.entry_id,
            "working_dir": entry_work_dir,
            "results_dir": entry_results_dir,
            "receptor": task.receptor_pdb,
            "prepared_suffix": validation_cfg.common.prepared_suffix,
            "padding": validation_cfg.common.padding,
            "n_jobs": 1,
            "max_poses": validation_cfg.common.max_poses,
            "pocket_option": "reference",
            "reference": task.pocket_pdb,
            "program": task.program,
        },
        "vina": validation_cfg.vina.model_dump(),
        "dock6": validation_cfg.dock6.model_dump(),
    }
    if task.program == "vina":
        data["vina"]["cpu"] = 1

    cfg = RootConfig.model_validate(data)
    cfg.common.working_dir = Path(entry_work_dir)
    cfg.common.results_dir = Path(entry_results_dir)
    cfg.common.receptor = Path(task.receptor_pdb)
    cfg.common.reference = Path(task.pocket_pdb)
    cfg.common.logger = setup_logger(Path(entry_work_dir) / "run.log")
    cfg.common.manifest = Manifest(Path(entry_work_dir) / "manifest.json")
    cfg.common.runstate = State(Path(entry_work_dir) / "state.json")
    return cfg


def _build_entry_ligands_config(validation_cfg, docking_cfg, entry_id, ligand_id, smiles, entry_work_dir):
    ligand_csv = Path(entry_work_dir) / f"{entry_id}_ligand.csv"
    with open(ligand_csv, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["smiles", "name"])
        writer.writerow([smiles, ligand_id])

    return LigandsConfig(
        source="smiles",
        prepared_suffix=validation_cfg.common.prepared_suffix,
        smiles_csv=ligand_csv,
        results_dir=Path(entry_work_dir) / "ligands",
        prepare_tool=validation_cfg.common.prepare_tool,
        program=docking_cfg.common.program,
    )


def _result_row(entry_id, ligand_id, smiles, features, scores, rmsds, num_analysis):
    top_scores = _pad(scores[:num_analysis], num_analysis)
    top_rmsds = _pad(rmsds[:num_analysis], num_analysis)
    avg_score, std_score = summarize_values(top_scores)
    avg_rmsd, std_rmsd = summarize_values(top_rmsds)
    all_rmsds = [value for value in rmsds if value != ""]
    min_rmsd_all = round(min(all_rmsds), 4) if all_rmsds else ""

    row = {
        "entry_id": entry_id,
        "ligand_id": ligand_id,
        "smiles": smiles,
        "hb_acceptors": features["hb_acceptors"],
        "hb_donors": features["hb_donors"],
        "mw": features["mw"],
    }
    for index, score in enumerate(top_scores, start=1):
        row[f"score{index}"] = score
    row["avg_score"] = avg_score
    row["std_score"] = std_score
    for index, rmsd in enumerate(top_rmsds, start=1):
        row[f"rmsd{index}"] = rmsd
    row["avg_rmsd"] = avg_rmsd
    row["std_rmsd"] = std_rmsd
    row["min_rmsd_all"] = min_rmsd_all
    return row


def _failure_row(entry_id, stage, error):
    return {"entry_id": entry_id, "stage": stage, "error": error}


def _pad(values, length):
    values = list(values)
    return values + [""] * (length - len(values))


def _result_headers(num_analysis):
    return (
        ["entry_id", "ligand_id", "smiles", "hb_acceptors", "hb_donors", "mw"]
        + [f"score{i}" for i in range(1, num_analysis + 1)]
        + ["avg_score", "std_score"]
        + [f"rmsd{i}" for i in range(1, num_analysis + 1)]
        + ["avg_rmsd", "std_rmsd", "min_rmsd_all"]
    )


def _write_results_csv(path, rows, num_analysis):
    headers = _result_headers(num_analysis)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _write_failures_csv(path, rows):
    headers = ["entry_id", "stage", "error"]
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
