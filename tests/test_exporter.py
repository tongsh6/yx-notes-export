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


def test_should_export_and_filter_notes_to_export(tmp_path):
    """增量导出：should_export 与 filter_notes_to_export 依赖本地索引."""
    note = NoteContent(
        guid="g1",
        title="Note One",
        content="<en-note><p>One</p></en-note>",
        created=100,
        updated=200,
        tags=[],
        source_url=None,
        resources=[],
    )
    fetcher = FakeFetcher(note)
    exporter = Exporter(fetcher, str(tmp_path), resume=True)
    nb = NotebookInfo(guid="nb1", name="Notebook", stack=None)

    meta1 = NoteMetadata(guid="g1", title="Note One", notebook_guid="nb1", updated=200)
    meta2 = NoteMetadata(guid="g2", title="Note Two", notebook_guid="nb1", updated=300)

    # 未导出前：两条都需导出
    assert exporter.should_export(meta1, nb) is True
    assert exporter.should_export(meta2, nb) is True
    filtered = exporter.filter_notes_to_export([meta1, meta2], nb)
    assert len(filtered) == 2

    # 导出 meta1 后：meta1 不需导出，meta2 仍需
    used = {}
    exporter.export_note(meta1, nb, used)
    assert exporter.should_export(meta1, nb) is False
    assert exporter.should_export(meta2, nb) is True
    filtered = exporter.filter_notes_to_export([meta1, meta2], nb)
    assert len(filtered) == 1
    assert filtered[0].guid == "g2"
