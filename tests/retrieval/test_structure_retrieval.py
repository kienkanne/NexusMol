import sys
from pathlib import Path

import pytest

if sys.version_info < (3, 10):
    pytest.skip(
        "nexus.fetch.fetch_config uses Python 3.10+ union type syntax",
        allow_module_level=True,
    )

from nexus.fetch.fetch_config import FetchConfig
from nexus.fetch.fetch_pipeline import FetchPipeline
import nexus.fetch.fetch_pipeline as fetch_pipeline
import nexus.fetch.rcsb_fetch as rcsb_fetch


class FakeDataQuery:
    def __init__(self, input_type, input_ids, return_data_list):
        self.input_type = input_type
        self.input_ids = input_ids
        self.return_data_list = return_data_list

    def exec(self):
        return None

    def get_response(self):
        return {
            "data": {
                "entries": [
                    {
                        "nonpolymer_entities": [
                            {"pdbx_entity_nonpoly": {"comp_id": "LIG"}},
                            {"pdbx_entity_nonpoly": {"comp_id": "HOH"}},
                            {"pdbx_entity_nonpoly": {"comp_id": "ZN"}},
                            {"pdbx_entity_nonpoly": {"comp_id": "ABC"}},
                        ]
                    }
                ]
            }
        }


class FakeModelQuery:
    def __init__(self, download, file_directory):
        self.download = download
        self.file_directory = Path(file_directory)

    def get_ligand(self, entry_id, label_comp_id, encoding, filename):
        assert encoding == "sdf"
        (self.file_directory / filename).write_text(f"{entry_id}:{label_comp_id}")

    def get_assembly(self, entry_id, encoding, filename):
        assert encoding == "cif"
        (self.file_directory / filename).write_text(f"{entry_id} assembly")


def test_get_ligands_in_structure_filters_ignored_entities(monkeypatch):
    monkeypatch.setattr(rcsb_fetch, "DataQuery", FakeDataQuery)

    assert rcsb_fetch.get_ligands_in_structure("1ABC") == ["LIG", "ABC"]


def test_rcsb_fetch_writes_ligands_and_assembly_to_output_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(rcsb_fetch, "DataQuery", FakeDataQuery)
    monkeypatch.setattr(rcsb_fetch, "ModelQuery", FakeModelQuery)

    rcsb_fetch.rcsb_fetch(FetchConfig(input=["1ABC"], output_dir=tmp_path))

    assert (tmp_path / "1ABC.cif").read_text() == "1ABC assembly"
    assert (tmp_path / "1ABC_LIG.sdf").read_text() == "1ABC:LIG"
    assert (tmp_path / "1ABC_ABC.sdf").read_text() == "1ABC:ABC"
    assert not (tmp_path / "1ABC_HOH.sdf").exists()


def test_fetch_pipeline_reads_ids_from_text_file(tmp_path, monkeypatch):
    ids = tmp_path / "ids.txt"
    ids.write_text("6W63\n7K40\n")
    seen = {}

    def fake_rcsb_fetch(fcfg):
        seen["input"] = fcfg.input
        seen["output_dir"] = fcfg.output_dir

    monkeypatch.setattr(fetch_pipeline, "rcsb_fetch", fake_rcsb_fetch)

    FetchPipeline(FetchConfig(input=[str(ids)], output_dir=tmp_path))._run()

    assert seen == {"input": ["6W63", "7K40"], "output_dir": tmp_path}
