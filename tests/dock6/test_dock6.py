from compdd.ligands._ligands_common import _prepared_filename


def test_prepared_filename_adds_separator_before_suffix():
    assert _prepared_filename("mol16", "ready", ".mol2") == "mol16_ready.mol2"
