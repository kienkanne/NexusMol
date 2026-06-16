import pytest
from pathlib import Path

from nexus.core.utils.extract_files import extract_files


def test_list_of_files_success(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("a")
    b.write_text("b")

    res = extract_files([str(a), b], patterns=".txt")
    assert set(res) == {a, b}


def test_list_contains_dir_raises(tmp_path):
    d = tmp_path / "d"
    d.mkdir()

    with pytest.raises(TypeError):
        extract_files([d], patterns=".txt")


def test_nonexistent_file_raises(tmp_path):
    missing = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        extract_files([missing], patterns=".txt")


def test_single_file_success(tmp_path):
    f = tmp_path / "f.sdf"
    f.write_text("x")

    res = extract_files(f, patterns=".sdf")
    assert res == [f]


def test_directory_pattern_nonrecursive(tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    (d / "file1.sdf").write_text("a")
    (d / "file2.sdf").write_text("b")
    sub = d / "sub"
    sub.mkdir()
    (sub / "file3.sdf").write_text("c")

    res = extract_files(d, patterns=".sdf", recursive=False)
    assert set(res) == {d / "file1.sdf", d / "file2.sdf"}


def test_directory_pattern_recursive(tmp_path):
    d = tmp_path / "dir2"
    d.mkdir()
    (d / "file1.sdf").write_text("a")
    sub = d / "sub"
    sub.mkdir()
    (sub / "file2.sdf").write_text("b")

    res = extract_files(d, patterns=".sdf", recursive=True)
    assert set(res) == {d / "file1.sdf", sub / "file2.sdf"}


def test_invalid_patterns_type(tmp_path):
    d = tmp_path / "dir3"
    d.mkdir()
    with pytest.raises(TypeError):
        extract_files(d, patterns=123, recursive=False)


def test_invalid_input_type(tmp_path):
    with pytest.raises(TypeError):
        extract_files(123, patterns=".sdf")
