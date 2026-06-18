from pathlib import Path
import subprocess
import re
import warnings

# Converts either pdbqt or mol2 docked poses to individual mol2 files, making it easy for RDKIT to read
def extract_poses(docked_poses_path: Path):
    docked_poses_path = Path(docked_poses_path)
    scratch_dir = docked_poses_path.parent
    ligand_name = docked_poses_path.stem    
    
    output_prefix = scratch_dir / f"{ligand_name}_pose_.mol2"

    cmd = ["obabel", str(docked_poses_path), "-O", str(output_prefix), "-m"]

    result = subprocess.run(cmd, text=True, capture_output=True, check=True)

    num_poses = None
    for text in (result.stderr, result.stdout):
        if not text:
            continue
        match = re.search(r"(\d+)\s+molecules\s+converted", text)
        if match:
            num_poses = int(match.group(1))
            break

    if num_poses is None:
        raise ValueError(
            f"Unable to determine number of extracted poses from OpenBabel output:\n"
            f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
        )

    poses_paths = []
    for i in range(num_poses):
        file_path = output_prefix.with_name(f"{ligand_name}_pose_{i+1}.mol2")
        poses_paths.append(file_path)
    return poses_paths


def _parse_mol2(file_path: Path):
    text = file_path.read_text()
    parts = text.split("@<TRIPOS>MOLECULE")
    if len(parts) < 2:
        return []

    mols = []
    for part in parts[1:]:
        block = "@<TRIPOS>MOLECULE" + part
        try:
            from rdkit import Chem
            mol = Chem.MolFromMol2Block(block, sanitize=False, removeHs=True)
            if mol:
                try:
                    Chem.SanitizeMol(mol, 
                                    Chem.SanitizeFlags.SANITIZE_ALL ^ 
                                    Chem.SanitizeFlags.SANITIZE_KEKULIZE)
                except Exception:
                    mol.SetProp("Sanitization_Failed", "True")
                mols.append(mol)
        except Exception:
            continue

    return mols


def parse_mol2_pose_rmsds(pose1_path: Path, pose2_path: Path):
    from rdkit.Chem import rdMolAlign

    if not pose1_path.exists():
        raise FileNotFoundError(f"Pose not found: {pose1_path}")
    if not pose2_path.exists():
        raise FileNotFoundError(f"Pose not found: {pose2_path}")

    pose1_mols = _parse_mol2(pose1_path)
    pose1_mol = pose1_mols[0]

    pose2_mols = _parse_mol2(pose2_path)
    pose2_mol = pose2_mols[0]

    try:
        rmsd = rdMolAlign.AlignMol(pose1_mol, pose2_mol, maxIters=0)
        return f"{rmsd:.3f}"
    except Exception:
        raise ValueError(f"Can't align two poses: {pose1_path} and {pose2_path}")


import numpy as np
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage, fcluster


def generate_rmsd_matrix(poses: list[Path]) -> np.ndarray:
    """Parses all poses into memory and builds a symmetric RMSD matrix."""
    from rdkit.Chem import rdMolAlign

    n_poses = len(poses)
    
    # 1. Parse all molecules ONCE into a list
    mols = []
    for path in poses:
        if not path.exists():
            raise FileNotFoundError(f"Pose file not found: {path}")
        # Assuming _parse_mol2 is your custom parsing function
        parsed_mols = _parse_mol2(path)
        if not parsed_mols:
            raise ValueError(f"Could not parse any molecule from {path}")
        mols.append(parsed_mols[0])
        
    # 2. Initialize an empty N x N matrix
    rmsd_matrix = np.zeros((n_poses, n_poses), dtype=float)
    
    # 3. Calculate pairwise RMSD (only need to compute half, it's symmetric)
    for i in range(n_poses):
        for j in range(i + 1, n_poses):
            try:
                # maxIters=0 ensures in-place RMSD without altering coordinates
                rmsd = rdMolAlign.AlignMol(mols[i], mols[j], maxIters=0)
                
                # Fill both sides of the symmetric matrix
                rmsd_matrix[i, j] = rmsd
                rmsd_matrix[j, i] = rmsd
            except Exception as e:
                print(f"Warning: Could not align pose {i} and {j}. Assigning NaN. Error: {e}")
                rmsd_matrix[i, j] = np.nan
                rmsd_matrix[j, i] = np.nan
                
    return rmsd_matrix


def _sanitize_distance_matrix(rmsd_matrix: np.ndarray, threshold: float = 2.0) -> np.ndarray:
    if rmsd_matrix.ndim != 2 or rmsd_matrix.shape[0] != rmsd_matrix.shape[1]:
        raise ValueError("RMSD matrix must be square")

    matrix = np.array(rmsd_matrix, dtype=float, copy=True)
    np.fill_diagonal(matrix, 0.0)

    if not np.allclose(matrix, matrix.T, equal_nan=True):
        matrix = 0.5 * (matrix + matrix.T)

    if np.isnan(matrix).any():
        finite_values = matrix[np.isfinite(matrix)]
        if finite_values.size > 0:
            fill_value = float(np.nanmax(finite_values)) * 10.0
        else:
            fill_value = float(threshold) * 10.0

        warnings.warn(
            "NaN values found in RMSD distance matrix. "
            f"Replacing NaN with {fill_value:.3f} to enable clustering.",
            UserWarning,
        )
        matrix = np.where(np.isnan(matrix), fill_value, matrix)

    return matrix


def calculate_cluster_metrics(rmsd_matrix: np.ndarray, threshold: float = 2.0) -> dict:
    """
    Clusters an RMSD matrix using hierarchical clustering.
    Returns a dictionary grouping the indices of poses into clusters.
    """
    n = rmsd_matrix.shape[0]
    if n == 0:
        return {}
    if n == 1:
        return {
            1: {
                "representative_idx": 0,
                "mean_internal_distance": 0.0,
                "cluster_diameter": 0.0,
                "pose_indices": [0],
                "mean_dist_to_others": 0.0,
            }
        }

    matrix = _sanitize_distance_matrix(rmsd_matrix, threshold=threshold)
    condensed_dist = squareform(matrix)

    # 2. Perform hierarchical clustering 
    # 'average' linkage is robust for grouping distinct structural families
    Z = linkage(condensed_dist, method='average')

    # 3. Extract flat clusters based on your RMSD threshold
    # The output is an array of cluster IDs corresponding to your poses
    cluster_labels = fcluster(Z, t=threshold, criterion='distance')
    
    # 4. Organize results into an intermediate dictionary {cluster_id: [pose_indices]}
    cluster_indices_dict = {}
    for pose_idx, cluster_id in enumerate(cluster_labels):
        if cluster_id not in cluster_indices_dict:
            cluster_indices_dict[cluster_id] = []
        cluster_indices_dict[cluster_id].append(pose_idx)
    
    # Final dictionary to store data
    clusters = {}

    for cluster_id, pose_indices in cluster_indices_dict.items():
        n_members = len(pose_indices)

        # Case 1: Single-element cluster (singleton)
        if n_members == 1:
            clusters[cluster_id] = {
                "representative_idx": pose_indices[0],
                "mean_internal_distance": 0.0,
                "cluster_diameter": 0.0,
                "pose_indices": pose_indices,
                "mean_dist_to_others": 0.0,
            }
            continue
            
        # Case 2: Multi-element cluster
        # Extract the submatrix containing only the distances between members of this cluster
        submatrix = np.array(rmsd_matrix[np.ix_(pose_indices, pose_indices)], dtype=float, copy=True)
        np.fill_diagonal(submatrix, np.nan)
        
        # Calculate the average distance from each pose to all other poses in the cluster
        cluster_pairwise_means = np.nanmean(submatrix, axis=1)
        
        # The medoid (representative) is the pose with the minimum average distance to others
        relative_medoid_idx = int(np.nanargmin(cluster_pairwise_means))
        representative_idx = pose_indices[relative_medoid_idx]
        
        # Get the distances from this specific representative to all other members
        rep_distances = np.nan_to_num(submatrix[relative_medoid_idx], nan=0.0)
        mean_dist_to_rep = float(np.sum(rep_distances) / (n_members - 1))
        
        # The maximum distance between any two poses in the cluster (diameter)
        cluster_diameter = float(np.nanmax(submatrix))
        
        clusters[cluster_id] = {
            "representative_idx": representative_idx,
            "mean_internal_distance": float(np.nanmean(submatrix[relative_medoid_idx])),
            "cluster_diameter": cluster_diameter,
            "pose_indices": pose_indices,
            "mean_dist_to_others": 0.0,
        }

    cluster_ids = list(clusters.keys())
    
    # --- Pass 2: Calculate distances to OTHER clusters ---
    for current_id in cluster_ids:
        current_rep = clusters[current_id]["representative_idx"]
        distances_to_other_reps = []
        
        for other_id in cluster_ids:
            if current_id != other_id:
                other_rep = clusters[other_id]["representative_idx"]
                # Look up the RMSD between the two representatives in the main matrix
                dist = rmsd_matrix[current_rep, other_rep]
                distances_to_other_reps.append(dist)
                
        # Average distance to other representatives (or 0 if only 1 cluster exists)
        avg_dist_to_others = np.mean(distances_to_other_reps) if distances_to_other_reps else 0.0
        
        clusters[current_id]["mean_dist_to_others"] = float(avg_dist_to_others)

    return clusters


def compute_clusters(
    ligand_name: str, 
    output_path: Path, 
    results_list: list[dict]
):
    """
    Formats the cluster data for a single ligand and appends it to a master list.
    """
    pose_paths = extract_poses(output_path)
    matrix = generate_rmsd_matrix(pose_paths)
    clusters = calculate_cluster_metrics(matrix, threshold=2.0)

    for cluster_id, metrics in clusters.items():
        results_list.append({
            "ligand_name": ligand_name,
            "cluster_id": cluster_id,
            "cluster_size": len(metrics["pose_indices"]),
            "rep_pose_idx": metrics["representative_idx"],
            "mean_internal_dist": round(metrics["mean_internal_distance"], 3),
            "mean_dist_to_others": round(metrics["mean_dist_to_others"], 3),
            "cluster_diameter": round(metrics["cluster_diameter"], 3),
            "pose_indices": str(metrics["pose_indices"]) 
        })
