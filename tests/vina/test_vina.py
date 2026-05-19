from compdd.ligands._ligands_common import _strip_prepared_suffix


def test_strip_prepared_suffix_for_vina_names():
    assert _strip_prepared_suffix("6W63_ready.pdbqt", "ready") == "6W63"
    assert _strip_prepared_suffix("mol16_ready.pdbqt", "ready") == "mol16"
