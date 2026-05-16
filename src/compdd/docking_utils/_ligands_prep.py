from pathlib import Path
import csv
import re
from compdd.executors.gnu_parallel import gnu_parallel
from compdd.utils.main_tracker import main_tracker


def _sanitize_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    sanitized = sanitized.strip("._-")
    if not sanitized:
        raise ValueError(f"Invalid ligand name {name!r}")
    return sanitized


def _ligands_prep(cfg, program):
    @main_tracker(cfg, "Prepare ligands")
    def _run():
        def parse_ligs():
            csv_path = Path(cfg.common.ligands_csv)
            if not csv_path.exists():   
                raise FileNotFoundError(f"Ligand CSV not found: {csv_path}")

            seen_smiles = set()
            seen_names = set()

            with open(csv_path, newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames != ["smiles", "name"]:
                    raise ValueError("Ligand CSV must have exactly this header: smiles,name")

                for row_number, row in enumerate(reader, start=2):
                    smiles = (row.get("smiles") or "").strip()
                    raw_name = (row.get("name") or "").strip()
                    if not smiles or not raw_name:
                        raise ValueError(f"Ligand CSV row {row_number} must include smiles and name")

                    name = _sanitize_name(raw_name)

                    if smiles in seen_smiles:
                        raise ValueError(f"Duplicate smiles: {smiles!r}")
                    seen_smiles.add(smiles)

                    if name in seen_names:
                        raise ValueError(f"Duplicate ligand name after sanitization: {raw_name!r}")
                    seen_names.add(name)

            if not seen_smiles or not seen_names:
                raise ValueError(f"Ligand CSV contains no ligands: {csv_path}")

            if len(seen_smiles) != len(seen_names):
                raise ValueError("Number of smiles is not equal to number of names")

            return seen_smiles, seen_names
        smiles_list, lig_names = parse_ligs()
        

        @gnu_parallel(cfg, "charge_ligs_obabel()")
        def charge_ligs_obabel():
            obabel = cfg.libs.obabel

            cmds = []
            for smiles, lig_name in zip(smiles_list, lig_names):
                cmds.append([
                    obabel,
                    f"-:'{smiles}'",
                    "-O", f"{lig_name}_prepped.mol2",
                    "--gen3d", "--partialcharge", "gasteiger"
                ])

            return cmds
        charge_ligs_obabel()

        prepped_ligs = []

        @gnu_parallel(cfg, "charge_rec_mgltools()")
        def charge_rec_mgltools():
            mgltools = cfg.libs.mgltools

            cmds = []
            for lig_name in lig_names:
                cmds.append([
                    mgltools/"bin"/"pythonsh",
                    mgltools/"MGLToolsPckgs"/"AutoDockTools"/"Utilities24"/"prepare_ligand4.py",
                    "-l", f"{lig_name}_prepped.mol2",
                    "-o", f"{lig_name}_prepped.pdbqt",
                    ])
                prepped_ligs.append(f"{lig_name}_prepped.pdbqt")

            return cmds

        # For Vina we need pdbqt ligand files (prepare_ligand4 -> pdbqt).
        # For DOCK6 we use the prepped .mol2 files produced by obabel.
        if program == "vina":
            charge_rec_mgltools()
        else:
            # return the .mol2 files created by obabel
            prepped_ligs = [f"{lig_name}_prepped.mol2" for lig_name in lig_names]

        return prepped_ligs
    
    return _run()