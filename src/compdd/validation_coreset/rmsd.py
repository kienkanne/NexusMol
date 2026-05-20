from pathlib import Path
import csv


def _split_pdbqt_poses(text):
    parts = text.split("MODEL")
    if len(parts) > 1:
        poses = [f"MODEL{p}" for p in parts if "ENDMDL" in p]
    else:
        poses = [text]
    return poses


def _parse_pose_rmsds(prep_path: Path, scored_path: Path, max_poses: int):
    # Compute RMSDs between a prepared crystal (pdbqt) and poses in a scored pdbqt file.
    # Returns list of rmsd values (strings) up to max_poses.
    try:
        from meeko import PDBQTMolecule, RDKitMolCreate
        from rdkit.Chem import rdMolAlign
    except Exception as e:
        raise RuntimeError("Meeko/RDKit are required for RMSD calculation") from e

    if not prep_path.exists():
        raise FileNotFoundError(f"Prepared crystal not found: {prep_path}")
    if not scored_path.exists():
        raise FileNotFoundError(f"Scored file not found: {scored_path}")

    # load crystal
    crystal = PDBQTMolecule.from_file(str(prep_path), skip_typing=True)
    rdkit_crystals = RDKitMolCreate.from_pdbqt_mol(crystal)
    rdkit_crystal = rdkit_crystals[0]

    text = scored_path.read_text()
    poses = _split_pdbqt_poses(text)

    rmsds = []
    for pose_text in poses[:max_poses]:
        try:
            pdbqt_docked = PDBQTMolecule(pose_text, skip_typing=True)
            rdkit_dockeds = RDKitMolCreate.from_pdbqt_mol(pdbqt_docked)
            if rdkit_dockeds and rdkit_dockeds[0] is not None:
                rdkit_docked = rdkit_dockeds[0]
                rmsd = rdMolAlign.AlignMol(rdkit_crystal, rdkit_docked, maxIters=0)
                rmsds.append(f"{rmsd:.3f}")
            else:
                rmsds.append("")
        except Exception:
            rmsds.append("")

    # pad to max_poses
    while len(rmsds) < max_poses:
        rmsds.append("")

    return rmsds


def _parse_dock6_mol2(file_path: Path):
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


def _parse_dock6_pose_rmsds(prep_path: Path, scored_path: Path, max_poses: int):
    try:
        from rdkit.Chem import rdMolAlign
    except Exception as e:
        raise RuntimeError("RDKit is required for DOCK6 RMSD calculation") from e

    if not prep_path.exists():
        raise FileNotFoundError(f"Prepared crystal not found: {prep_path}")
    if not scored_path.exists():
        raise FileNotFoundError(f"Scored file not found: {scored_path}")

    crystals = _parse_dock6_mol2(prep_path)
    if not crystals:
        raise ValueError(f"Unable to parse prepared DOCK6 crystal from {prep_path}")
    rdkit_crystal = crystals[0]

    poses = _parse_dock6_mol2(scored_path)
    rmsds = []
    for pose in poses[:max_poses]:
        try:
            rmsd = rdMolAlign.AlignMol(rdkit_crystal, pose, maxIters=0)
            rmsds.append(f"{rmsd:.3f}")
        except Exception:
            rmsds.append("")

    while len(rmsds) < max_poses:
        rmsds.append("")

    return rmsds


def compute_validation_rmsds(cfg):
    """Compute RMSDs for prepared crystal vs scored outputs and write per-receptor CSVs.

    Writes files named `<project>_<receptor>_rmsd.csv` into the results directory.
    """
    max_poses = cfg.common.max_poses
    wd = Path(cfg.common.working_dir)
    rd = Path(cfg.common.results_dir)
    project = cfg.common.project_name
    suffix = cfg.common.prepared_suffix
    program = getattr(cfg.common, "program", "vina")

    bundles = getattr(cfg.receptors, "bundles", None)
    if not bundles:
        raise ValueError("No receptor bundles found on cfg.receptors.bundles")

    for b in bundles:
        name = b.name
        if program == "dock6":
            prep_path = wd / f"{name}_{suffix}.mol2"
            scored_pattern = f"{name}*_scored.mol2"
        else:
            prep_path = wd / f"{name}_{suffix}.pdbqt"
            scored_pattern = f"{name}*_scored.pdbqt"

        scored_candidates = list(wd.glob(scored_pattern))
        if not scored_candidates:
            # fallback: any scored file that contains the receptor/ligand name
            scored_ext = "mol2" if program == "dock6" else "pdbqt"
            scored_candidates = [p for p in wd.glob(f"*_{scored_ext}") if name in p.stem and p.stem.endswith("_scored")]

        if not scored_candidates:
            continue

        rows = []
        for scored in scored_candidates:
            ligand_name = scored.stem.replace("_scored", "")
            try:
                if program == "dock6":
                    rmsds = _parse_dock6_pose_rmsds(prep_path, scored, max_poses)
                else:
                    rmsds = _parse_pose_rmsds(prep_path, scored, max_poses)
            except Exception:
                rmsds = [""] * max_poses
            rows.append([ligand_name] + rmsds)

        csv_name = rd / f"{project}_{name}_rmsd.csv"
        headers = ["name"] + [f"rmsd{i}" for i in range(1, max_poses + 1)]
        with open(csv_name, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
            writer.writerows(rows)

    return True
