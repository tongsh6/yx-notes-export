import os

# pyright: reportMissingImports=false

from src.exporter import Exporter
from src.fetcher import NoteContent, NoteMetadata, NotebookInfo


class FakeFetcher:
    def __init__(self, content: NoteContent) -> None:
        self._content = content

    def get_note_content(self, guid: str) -> NoteContent:
        return self._content

    def get_resource_data(self, resource_guid: str) -> bytes:
        return b""


def test_export_note_writes_file(tmp_path):
    note = NoteContent(
        guid="g1",
        title="Hello World",
        content="<en-note><p>Hi</p></en-note>",
        created=0,
        updated=None,
        tags=["t1"],
        source_url="https://example.com",
        resources=[],
    )
    fetcher = FakeFetcher(note)
    exporter = Exporter(fetcher, str(tmp_path))
    meta = NoteMetadata(guid="g1", title="Hello World", notebook_guid="nb1", updated=0)
    nb = NotebookInfo(guid="nb1", name="Notebook", stack="Stack")
    used = {}
    path, skipped = exporter.export_note(meta, nb, used)
    assert not skipped

    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "title: Hello World" in content
    assert "# Hello World" in content
    assert "Hi" in content

    # Resume: export again should be skipped
    path2, skipped2 = exporter.export_note(meta, nb, used)
    assert skipped2
    assert path2 == path
