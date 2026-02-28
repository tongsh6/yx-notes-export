from src.utils import safe_filename, ts_to_iso, unique_filename


def test_safe_filename_basic():
    name = '  a/b:c*"<>|  '
    assert safe_filename(name) == "a-b-c"


def test_safe_filename_empty():
    assert safe_filename("***") == "untitled"


def test_unique_filename():
    existing = {"note.md", "note-2.md"}
    assert unique_filename("note", ".md", existing) == "note-3.md"


def test_ts_to_iso():
    assert ts_to_iso(0) == "1970-01-01T00:00:00Z"
