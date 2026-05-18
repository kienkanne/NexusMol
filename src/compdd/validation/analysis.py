from pathlib import Path
import math
import shutil
import statistics
import subprocess

from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Lipinski, rdMolAlign


class AnalysisError(RuntimeError):
    pass


def ligand_features(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise AnalysisError(f"Invalid SMILES for feature calculation: {smiles}")
    return {
        "hb_acceptors": Lipinski.NumHAcceptors(mol),
        "hb_donors": Lipinski.NumHDonors(mol),
        "mw": round(Descriptors.MolWt(mol), 4),
    }


def summarize_values(values):
    clean = [float(value) for value in values if value not in (None, "") and not math.isnan(float(value))]
    if not clean:
        return "", ""
    avg = statistics.fmean(clean)
    std = statistics.pstdev(clean) if len(clean) > 1 else 0.0
    return round(avg, 4), round(std, 4)


def convert_docked_poses_to_sdf(obabel, docked_file, output_sdf):
    result = subprocess.run(
        [str(obabel), str(docked_file), "-O", str(output_sdf)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AnalysisError(f"Open Babel failed to convert docked poses: {result.stderr.strip()}")
    if not Path(output_sdf).is_file():
        raise AnalysisError(f"Open Babel did not create converted pose file: {output_sdf}")


def _load_crystal_mol(crystal_mol2, crystal_sdf=None):
    mol = None
    if crystal_sdf and Path(crystal_sdf).is_file():
        supplier = Chem.SDMolSupplier(str(crystal_sdf), removeHs=False)
        mol = supplier[0] if supplier and len(supplier) else None
    if mol is None:
        mol = Chem.MolFromMol2File(str(crystal_mol2), removeHs=False, sanitize=False)
    if mol is None:
        raise AnalysisError(f"Could not load crystal ligand: {crystal_mol2}")
    return mol


def _assign_template_bonds(template, mol):
    try:
        return AllChem.AssignBondOrdersFromTemplate(template, mol)
    except Exception:
        return mol


def calculate_pose_rmsds(smiles, crystal_mol2, docked_file, obabel, work_dir, crystal_sdf=None):
    template = Chem.MolFromSmiles(smiles)
    if template is None:
        raise AnalysisError(f"Invalid SMILES for RMSD analysis: {smiles}")

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    poses_sdf = work_dir / "docked_poses.sdf"
    convert_docked_poses_to_sdf(obabel, docked_file, poses_sdf)

    ref = _load_crystal_mol(crystal_mol2, crystal_sdf=crystal_sdf)
    ref = Chem.RemoveHs(_assign_template_bonds(template, ref), sanitize=False)

    supplier = Chem.SDMolSupplier(str(poses_sdf), removeHs=False)
    rmsds = []
    for pose in supplier:
        if pose is None:
            rmsds.append("")
            continue
        pose = Chem.RemoveHs(_assign_template_bonds(template, pose), sanitize=False)
        match = ref.GetSubstructMatch(pose)
        if not match:
            rmsds.append("")
            continue
        atom_map = [(pose_idx, ref_idx) for pose_idx, ref_idx in enumerate(match)]
        try:
            rmsds.append(round(float(rdMolAlign.AlignMol(pose, ref, atomMap=atom_map)), 4))
        except Exception:
            rmsds.append("")

    if not any(value != "" for value in rmsds):
        raise AnalysisError("No docked poses could be aligned to the crystal ligand")
    return rmsds


def copy_if_exists(src, dst):
    src = Path(src)
    if src.exists():
        dst = Path(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
