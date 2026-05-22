from pathlib import Path
from rcsbapi.data import DataQuery
from rcsbapi.model import ModelQuery

from nexus.fetch.fetch_config import FetchConfig

# Expanded common crystallization agents and ions
IGNORED_LIGANDS = {"HOH", "DOD", "SO4", "PO4", "GOL", "EDO", "NA", "CL", "MG", "ZN", "CA", "DMS", "ACT"}


def get_ligands_in_structure(id):
    """
    Only retrieve non-covalent ligands
    """
    query = DataQuery(
        input_type="entries",
        input_ids=[id],
        return_data_list=[
            "nonpolymer_entities.pdbx_entity_nonpoly.comp_id",
            "nonpolymer_entities.pdbx_entity_nonpoly.name"
        ]
    )
    query.exec()
    response = query.get_response()
    
    ligand_ids = []
    entries = response.get("data", {}).get("entries", []) or []
    if not entries:
        return ligand_ids
        
    for entry in entries:
        # Safe fallback if nonpolymer_entities is explicitly Null/None
        nonpoly_entities = entry.get("nonpolymer_entities") or []
        for entity in nonpoly_entities:
            comp = entity.get("pdbx_entity_nonpoly", {}) or {}
            comp_id = comp.get("comp_id")
            if comp_id and comp_id not in IGNORED_LIGANDS:
                ligand_ids.append(comp_id)
                
    return ligand_ids


def rcsb_fetch(fcfg: FetchConfig, id: str):
    raw_suffix = fcfg.raw_assembly_suffix
    ligand_suffix = fcfg.ligand_suffix
    output_dir = fcfg.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n--- Processing {id} ---")
    ligands = get_ligands_in_structure(id)
    
    model_api = ModelQuery(download=True, file_directory=output_dir)
    
    # Download Ligands as SDF
    for lig_id in ligands:
        if ligand_suffix is None:
            ligand_file = f"{id}_{lig_id}.sdf"
        elif isinstance(ligand_suffix, str):
            ligand_file = f"{id}_{ligand_suffix}.sdf"

        try:
            model_api.get_ligand(
                entry_id=id,
                label_comp_id=lig_id,
                encoding="sdf",
                filename=ligand_file
            )
            print(f"✅ Saved ligand -> {ligand_file}")
        except Exception as e:
            print(f"❌ Failed to download {lig_id}: {e}")

    # Download Biological Assembly in CIF format
    raw_file = f"{id}_{raw_suffix}.cif"
    model_api.get_assembly(
        entry_id=id, 
        encoding="cif",
        filename=raw_file,
    )

    raw_path = Path(output_dir / raw_file)

    if raw_path.is_file():
        if raw_path.stat().st_size == 0:
            raise IOError(f"Assembly download failed for {id}: empty file.")
    else:
        raise FileNotFoundError(f"Assembly download failed for {id}: file was not created.")

    print (f"✅ Saved raw biological assembly receptor: {raw_path}")

    return raw_path
