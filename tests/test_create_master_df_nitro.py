"""Regression test for the DOCK6 nitro-group (NO2) MOL2 parsing failure.

DOCK6 writes nitro groups into its ``_scored.mol2`` output with the SYBYL types
``N.pl3 / O.co2 / O.2``. RDKit's default MOL2 substructure cleanup chokes on the
carboxylate-oxygen type (``O.co2``) sitting on a non-carboxyl neighbour and returns
``None``, which used to make ``process_ligand`` silently drop every pose of such a
ligand (e.g. mol8/mol16 in the Mpro run). ``process_ligand`` now retries with
``cleanupSubstructures=False`` so the pose is recovered.
"""

from rdkit import Chem

from nexus.dock.utils.create_master_df import process_ligand


# Minimal nitromethane (CH3-NO2) block mimicking DOCK6 output: the "Name: *****"
# header ``process_ligand`` splits on, a ``Grid_Score:`` line, and the offending
# nitro typed N.pl3 / O.co2 / O.2 (one N-O single, one N-O double bond).
NITRO_MOL2 = """##########                                Name:               *****
##########                         Grid_Score:          -12.345678
@<TRIPOS>MOLECULE
nitromethane
    7     6     1     0     0
SMALL
USER_CHARGES
@<TRIPOS>ATOM
      1 C          -0.0000    0.0000    0.0000 C.3     1  UNL1        0.0000
      2 N           0.0000    0.0000    1.5000 N.pl3   1  UNL1        0.0796
      3 O           1.0700    0.0000    2.1000 O.co2   1  UNL1       -0.5760
      4 O          -1.0700    0.0000    2.1000 O.2     1  UNL1        0.0414
      5 H           1.0300    0.0000   -0.3600 H       1  UNL1        0.0000
      6 H          -0.5100    0.8900   -0.3600 H       1  UNL1        0.0000
      7 H          -0.5100   -0.8900   -0.3600 H       1  UNL1        0.0000
@<TRIPOS>BOND
     1    1    2 1
     2    2    3 1
     3    2    4 2
     4    1    5 1
     5    1    6 1
     6    1    7 1
"""


def test_default_cleanup_returns_none_for_nitro():
    """Documents the underlying RDKit behaviour the fix works around."""
    assert Chem.MolFromMol2Block(NITRO_MOL2, sanitize=False, removeHs=False) is None
    assert (
        Chem.MolFromMol2Block(
            NITRO_MOL2, sanitize=False, removeHs=False, cleanupSubstructures=False
        )
        is not None
    )


def test_process_ligand_recovers_nitro_pose(tmp_path):
    """process_ligand must recover the nitro-containing pose, not drop it."""
    mol2_path = tmp_path / "nitro_scored.mol2"
    mol2_path.write_text(NITRO_MOL2)

    prolif_poses, scores = process_ligand(str(mol2_path), "dock6")

    assert len(prolif_poses) == 1
    assert scores == [-12.345678]
