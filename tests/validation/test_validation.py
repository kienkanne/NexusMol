from compdd.validation.casf import UnsupportedLigandError, discover_casf_entries, parse_mol2_ligand_id
from compdd.validation.config import load_validation_config
from compdd.validation.pipeline import _result_headers, _result_row
from compdd.validation.rcsb import RCSBClient


def _write_minimal_mol2(path, residue="ABC"):
    path.write_text(
        "@<TRIPOS>MOLECULE\n"
        "lig\n"
        " 1 0 1 0 0\n"
        "SMALL\n"
        "NO_CHARGES\n"
        "@<TRIPOS>ATOM\n"
        f"      1 C1 0.0 0.0 0.0 C.3 1 {residue} 0.0\n"
        "@<TRIPOS>BOND\n"
    )


def test_discover_casf_entries(tmp_path):
    entry = tmp_path / "1abc"
    entry.mkdir()
    (entry / "1abc_protein.pdb").write_text("protein")
    (entry / "1abc_pocket.pdb").write_text("pocket")
    _write_minimal_mol2(entry / "1abc_ligand.mol2", residue="LIG")
    (entry / "1abc_ligand_opt.mol2").write_text("ignored")

    entries = discover_casf_entries(tmp_path)

    assert len(entries) == 1
    assert entries[0].entry_id == "1abc"
    assert entries[0].crystal_ligand_mol2.name == "1abc_ligand.mol2"


def test_parse_mol2_ligand_id_rejects_mol(tmp_path):
    ligand = tmp_path / "ligand.mol2"
    _write_minimal_mol2(ligand, residue="MOL")

    try:
        parse_mol2_ligand_id(ligand)
    except UnsupportedLigandError as exc:
        assert "no clear CCD" in str(exc)
    else:
        raise AssertionError("Expected UnsupportedLigandError")


def test_parse_mol2_ligand_id_reads_clear_residue(tmp_path):
    ligand = tmp_path / "ligand.mol2"
    _write_minimal_mol2(ligand, residue="prl")

    assert parse_mol2_ligand_id(ligand) == "PRL"


def test_rcsb_client_uses_cache_and_extracts_smiles(tmp_path):
    calls = []

    def fetch_json(url):
        calls.append(url)
        if url.endswith("/entry/1abc"):
            return {"rcsb_entry_container_identifiers": {"non_polymer_entity_ids": ["1"]}}
        if url.endswith("/nonpolymer_entity/1abc/1"):
            return {
                "pdbx_entity_nonpoly": {"comp_id": "LIG", "name": "Example ligand"},
                "rcsb_nonpolymer_entity_container_identifiers": {"nonpolymer_comp_id": "LIG"},
            }
        return {
            "chem_comp": {"id": "LIG", "name": "Example ligand"},
            "pdbx_chem_comp_descriptor": [
                {"type": "SMILES_CANONICAL", "program": "OpenEye OEToolkits", "descriptor": "CCO"}
            ],
        }

    client = RCSBClient(tmp_path, fetch_json=fetch_json)

    assert client.ligand_metadata("1abc", "LIG")["smiles"] == "CCO"
    assert client.ligand_metadata("1abc", "LIG")["smiles"] == "CCO"
    assert len(calls) == 3


def test_validation_config_defaults_and_paths(tmp_path):
    config = tmp_path / "validation.yaml"
    config.write_text(
        "libs:\n"
        "  chimerax: chimerax\n"
        "  chimera: chimera\n"
        "  mgltools: mgltools\n"
        "  dock_home: dock6\n"
        "  obabel: obabel\n"
        "  parallel: parallel\n"
        "  vina: vina\n"
        "common:\n"
        "  project_name: validation\n"
        f"  working_dir: {tmp_path / 'work'}\n"
        f"  results_dir: {tmp_path / 'results'}\n"
        f"  validation_data: {tmp_path / 'coreset'}\n"
        "vina: {}\n"
        "dock6: {}\n"
    )

    cfg = load_validation_config(config)

    assert cfg.common.pocket_option == "reference"
    assert cfg.common.prepared_suffix == "prepped"
    assert cfg.vina.cpu == 1
    assert cfg.common.working_dir == tmp_path / "work" / "validation"


def test_dynamic_result_headers_and_row():
    headers = _result_headers(2)
    row = _result_row(
        entry_id="1abc",
        ligand_id="LIG",
        smiles="CCO",
        features={"hb_acceptors": 1, "hb_donors": 1, "mw": 46.069},
        scores=[-9.0, -8.0, -7.0],
        rmsds=[2.5, 1.5, 0.9],
        num_analysis=2,
    )

    assert headers == [
        "entry_id", "ligand_id", "smiles", "hb_acceptors", "hb_donors", "mw",
        "score1", "score2", "avg_score", "std_score",
        "rmsd1", "rmsd2", "avg_rmsd", "std_rmsd", "min_rmsd_all",
    ]
    assert row["avg_score"] == -8.5
    assert row["min_rmsd_all"] == 0.9


def test_calculate_pose_rmsds_with_mocked_conversion(tmp_path, monkeypatch):
    from rdkit import Chem
    from rdkit.Chem import AllChem
    from compdd.validation import analysis

    smiles = "CCO"
    mol = Chem.AddHs(Chem.MolFromSmiles(smiles))
    AllChem.EmbedMolecule(mol, randomSeed=7)
    crystal_sdf = tmp_path / "crystal.sdf"
    docked_sdf_source = tmp_path / "source_poses.sdf"
    docked_placeholder = tmp_path / "docked.pdbqt"
    docked_placeholder.write_text("placeholder")

    writer = Chem.SDWriter(str(crystal_sdf))
    writer.write(mol)
    writer.close()
    writer = Chem.SDWriter(str(docked_sdf_source))
    writer.write(mol)
    writer.close()

    def fake_convert(obabel, docked_file, output_sdf):
        output_sdf.write_text(docked_sdf_source.read_text())

    monkeypatch.setattr(analysis, "convert_docked_poses_to_sdf", fake_convert)

    rmsds = analysis.calculate_pose_rmsds(
        smiles=smiles,
        crystal_mol2=tmp_path / "unused.mol2",
        crystal_sdf=crystal_sdf,
        docked_file=docked_placeholder,
        obabel="obabel",
        work_dir=tmp_path / "analysis",
    )

    assert rmsds[0] < 0.001
