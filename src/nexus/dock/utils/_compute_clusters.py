from pathlib import Path
import subprocess
import re

# Converts either pdbqt or mol2 docked poses to individual mol2 files, making it easy for RDKIT to read
def extract_poses(docked_poses_path: Path):
    docked_poses_path = Path(docked_poses_path)
    working_dir = docked_poses_path.parent
    ligand_name = docked_poses_path.stem    
    
    output_prefix = working_dir / f"{ligand_name}_pose_.mol2"

    cmd = ["obabel", str(docked_poses_path), "-O", str(output_prefix), "-m"]

    result = subprocess.run(cmd, text=True, capture_output=True, check=True)

    match = re.search(r"(\d+)\s+files\s+output", result.stderr)
    if match:
        num_poses = int(match.group(1))
    
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
            mol = Chem.MolFromMol2Block(block, sanitize=False, removeHs=False)
            if mol:
                try:
                    Chem.SanitizeMol(mol)
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
from rdkit.Chem import rdMolAlign


def generate_rmsd_matrix(poses: list[Path]) -> np.ndarray:
    """Parses all poses into memory and builds a symmetric RMSD matrix."""
    n_poses = len(poses)
    
    # 1. Parse all molecules ONCE into a list
    mols = []
    for path in poses:
        if not path.exists():
            raise FileNotFoundError(f"Pose file not found: {path}")
        # Assuming _parse_mol2 is your custom parsing function
        parsed_mols = _parse_mol2(path)
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


from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage, fcluster


def calculate_cluster_metrics(rmsd_matrix: np.ndarray, threshold: float = 2.0) -> dict:
    """
    Clusters an RMSD matrix using hierarchical clustering.
    Returns a dictionary grouping the indices of poses into clusters.
    """
    # 1. Scipy requires a "condensed" 1D distance matrix (upper triangle only)
    # Ensure the diagonal is exactly 0.0 to avoid floating point errors
    np.fill_diagonal(rmsd_matrix, 0.0) 
    condensed_dist = squareform(rmsd_matrix)
    
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
        print (pose_indices)
        n_members = len(pose_indices)

        # Case 1: Single-element cluster (singleton)
        if n_members == 1:
            clusters[cluster_id] = {
                "representative_idx": pose_indices[0],
                "mean_internal_distance": 0.0,
                "cluster_diameter": 0.0,
                "pose_indices": [0]
            }
            continue
            
        # Case 2: Multi-element cluster
        # Extract the submatrix containing only the distances between members of this cluster
        submatrix = rmsd_matrix[np.ix_(pose_indices, pose_indices)]
        
        # Calculate the average distance from each pose to all other poses in the cluster
        # We divide by (n_members - 1) to exclude the 0.0 distance to itself
        cluster_pairwise_means = np.sum(submatrix, axis=1) / (n_members - 1)
        
        # The medoid (representative) is the pose with the minimum average distance to others
        relative_medoid_idx = np.argmin(cluster_pairwise_means)
        representative_idx = pose_indices[relative_medoid_idx]
        
        # Get the distances from this specific representative to all other members
        rep_distances = submatrix[relative_medoid_idx]
        mean_dist_to_rep = np.sum(rep_distances) / (n_members - 1)
        
        # The maximum distance between any two poses in the cluster (diameter)
        cluster_diameter = np.max(submatrix)
        
        clusters[cluster_id] = {
            "representative_idx": representative_idx,
            "mean_internal_distance": float(mean_dist_to_rep),
            "cluster_diameter": float(cluster_diameter),
            "pose_indices": pose_indices
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
        print (metrics)
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
