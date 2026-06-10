import pytest

from nexus.core.utils.extract_files import extract_files


def test_extract_files_returns_matching_directory_children(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "a.sdf").write_text("a")
    (data_dir / "b.sdf").write_text("b")
    (data_dir / "ignore.txt").write_text("x")

    result = extract_files(data_dir, ".sdf")

    assert [path.name for path in result] == ["a.sdf", "b.sdf"]


def test_extract_files_supports_recursive_search_and_pattern_lists(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "root.pdb").write_text("root")
    (nested / "child.cif").write_text("child")

    result = extract_files(tmp_path, [".pdb", ".cif"], recursive=True)

    assert [path.name for path in result] == ["child.cif", "root.pdb"]


def test_extract_files_single_file_ignores_pattern_and_returns_file(tmp_path):
    file_path = tmp_path / "ligand.mol2"
    file_path.write_text("mol2")

    assert extract_files(file_path, ".sdf") == [file_path]


def test_extract_files_rejects_missing_paths_and_directories_in_lists(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_files(tmp_path / "missing.sdf", ".sdf")

    folder = tmp_path / "folder"
    folder.mkdir()
    with pytest.raises(TypeError):
        extract_files([folder], ".sdf")
