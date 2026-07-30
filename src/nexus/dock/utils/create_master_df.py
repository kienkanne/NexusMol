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


from nexus.dock.dock_config import DockConfig

@main_tracker("Write summary csv")
def write_summary_csv(cfg: DockConfig, out_files, rec_bundles):
    """
    Depreciated from version 2.5.0
    """
    job_name = cfg.common.job_name
    max_poses = cfg.common.max_poses
    scratch_dir = cfg._global.path.scratch_dir

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
            scores = parse_scores(out, max_poses, cfg.engine.program)
            scores_rows.append([lig_name] + scores + [""] * (max_poses - len(scores)))

            # Compute cluster metrics
            compute_clusters(lig_name, out, cluster_results)

        csv_name = f"{job_name}_{rec}"
        scores_csv_name = scratch_dir / f"Scores_{csv_name}.csv"
        cluster_csv_name = scratch_dir / f"Clusters_{csv_name}.csv"

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


@main_tracker("Create master dataframe")
def create_master_df(cfg: DockConfig, out_files, rec_bundles):
    # Group out_files by receptor name derived from rec_bundles
    if rec_bundles is None:
        raise ValueError("rec_bundles is required for mix mode")

    rec_names = [r.name for r in rec_bundles]
    groups = {name: [] for name in rec_names}

    for out in out_files:
        stem = Path(out).stem
        # expect format '{rec}_{lig}_scored'
        for rec_name in rec_names:
            if stem.startswith(f"{rec_name}_"):
                groups[rec_name].append(out)
                break
    
    dfs_to_combine = []

    for (rec_name, out_files), rec_bundle in zip(groups.items(), rec_bundles):
        for out in out_files:
            # Parse raw scores
            lig_name = Path(out).stem.replace(f"{rec_name}_", "", 1).replace("_scored", "")
            print ("Processing ligand:", lig_name, "for receptor:", rec_name)
            prolif_poses, scores = process_ligand(out, cfg.engine.program)

            # These two dicts have the same length
            plif_df = get_plif_df(prolif_poses, rec_bundle.original_receptor)

            metadata_dict = [{("Metadata", "Engine"): cfg.engine.program,
                                ("Metadata", "Receptor"): rec_name, 
                                ("Metadata", "Ligand"): lig_name, 
                                ("Metadata", "Pose"): i, 
                                ("Metadata", "Score"): score} for i, score in enumerate(scores)]
            
            meta_df = pd.DataFrame(metadata_dict)

            combined_pose_df = pd.concat([meta_df, plif_df], axis=1)
            dfs_to_combine.append(combined_pose_df)

    master_df = pd.concat(dfs_to_combine, ignore_index=True)
    master_df.columns = pd.MultiIndex.from_tuples(master_df.columns)
    
    if "PLIF" in master_df.columns.levels[0]:
        master_df["PLIF"] = master_df["PLIF"].fillna(False)

    new_order = ["Molecule", "Metadata", "PLIF"]
    # We get all unique top-level categories actually present in the df to prevent errors
    existing_order = [cat for cat in new_order if cat in master_df.columns.levels[0]]
    master_df = master_df[existing_order]

    return master_df

import warnings

# Suppress the specific MDAnalysis deprecation warning
warnings.filterwarnings(
    "ignore", 
    category=DeprecationWarning, 
    message=".*MDAnalysis.topology.tables has been moved.*"
)

import prolif as plf
from rdkit import Chem
from meeko import PDBQTMolecule, RDKitMolCreate

def process_ligand(out_file, engine):
    prolif_poses = []
    scores = []

    if engine == "vina":
        pdbqt_mol = PDBQTMolecule.from_file(out_file)

        rdkit_mol = RDKitMolCreate.from_pdbqt_mol(pdbqt_mol)[0]
        # Loop through each conformation ID
        for conf in rdkit_mol.GetConformers():
            conf_id = conf.GetId()

            scores.append(float(pdbqt_mol[conf_id].score))
            single_pose_mol = Chem.Mol(rdkit_mol, False, conf_id)
            
            plf_mol = plf.Molecule(single_pose_mol)
            prolif_poses.append(plf_mol)


    elif engine == "dock6":
        text = Path(out_file).read_text()
        separate_string = "##########                                Name:               *****"
        blocks = text.split(separate_string)

        skipped_count = 0

        for i , block in enumerate(blocks[1:]):  # Skip the first block as it is empty due to the split
            block = separate_string + block  # Add back the header for each block

            # RDKit's default MOL2 substructure cleanup returns None on some SYBYL
            # typings DOCK6 emits -- notably nitro groups typed N.pl3 / O.co2 / O.2,
            # where the carboxylate-oxygen type (O.co2) on a non-carboxyl neighbor
            # trips the cleanup. Retry once with cleanupSubstructures=False before
            # giving up on the pose.
            rdkit_mol = Chem.MolFromMol2Block(block, sanitize=False, removeHs=False)
            if rdkit_mol is None:
                rdkit_mol = Chem.MolFromMol2Block(
                    block, sanitize=False, removeHs=False, cleanupSubstructures=False
                )
            if rdkit_mol is None:
                skipped_count += 1
                continue

            rdkit_mol.UpdatePropertyCache(strict=False)
            Chem.FastFindRings(rdkit_mol)
            try:
                Chem.SanitizeMol(rdkit_mol, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_KEKULIZE)
            except Exception:
                rdkit_mol.SetProp("Sanitization_Failed", "True")
                print (f"Sanitization failed for molecule in {out_file}, pose {i}.")

            for line in block.splitlines():
                if "Grid_Score" in line:
                    score = line.split("Grid_Score:", 1)[1].split()[0]
                    scores.append(float(score))

            # Wrap it safely into a ProLIF Molecule object
            prolif_mol = plf.Molecule.from_rdkit(rdkit_mol)
            prolif_poses.append(prolif_mol)

        if skipped_count > 0:
            print(f"Skipped {skipped_count} DOCK6 molecules due to RDKit parsing errors.")

    return prolif_poses, scores

def get_plif_df(prolif_poses, original_receptor_path):
    receptor_mol = Chem.MolFromPDBFile(str(original_receptor_path), removeHs=False, sanitize=True)

    receptor_mol = plf.Molecule(receptor_mol)

    fp = plf.Fingerprint()
    fp.run_from_iterable(prolif_poses, receptor_mol)

    plif_df = fp.to_dataframe()

    # Handle the empty/no-interaction case safely, but still retain the pose molecules
    if plif_df.empty or not isinstance(plif_df.columns, pd.MultiIndex):
        empty_df = pd.DataFrame(index=range(len(prolif_poses)))
        empty_df[("Molecule", "Ligand_Mol")] = prolif_poses
        return empty_df

    plif_df = plif_df.droplevel('ligand', axis=1)

    # 2. Flatten the 2-level tuple columns into clean single strings
    plif_df.columns = [f"{residue}_{interaction}" for residue, interaction in plif_df.columns]
    plif_df.columns = pd.MultiIndex.from_product([["PLIF"], plif_df.columns])

    plif_df[("Molecule", "Ligand_Mol")] = prolif_poses

    plif_df.index.name = None
    plif_df.reset_index(drop=True, inplace=True)

    return plif_df