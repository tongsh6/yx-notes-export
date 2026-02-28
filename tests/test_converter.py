from src.converter import enml_to_markdown


def test_enml_to_markdown_todo_and_crypt():
    enml = """
    <en-note>
      <p>Task list:</p>
      <en-todo checked="true"/> Done
      <en-todo checked="false"/> Pending
      <en-crypt>secret</en-crypt>
    </en-note>
    """
    md = enml_to_markdown(enml)
    assert "Task list" in md
    assert "Done" in md
    assert "Pending" in md
    assert "加密内容" in md


def test_enml_to_markdown_media_mapping():
    enml = """
    <en-note>
      <en-media type="image/png" hash="abcd" />
      <en-media type="application/pdf" hash="efgh" />
    </en-note>
    """
    resource_map = {
        "abcd": ("image/png", "assets/img.png"),
        "efgh": ("application/pdf", "assets/doc.pdf"),
    }
    md = enml_to_markdown(enml, resource_map)
    assert "assets/img.png" in md
    assert "assets/doc.pdf" in md
