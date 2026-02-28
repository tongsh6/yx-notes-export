import os

import pytest
from PySide6.QtCore import Qt

from src.auth import AuthConfig, build_client
from src.fetcher import Fetcher
from src.gui import main_window


@pytest.mark.skipif(
    not os.environ.get("YX_TOKEN"),
    reason="Requires YX_TOKEN environment variable",
)
def test_gui_flow_real_api(qapp, qtbot, tmp_path):
    token = os.environ.get("YX_TOKEN")
    client = build_client(AuthConfig(mode="token", token=token))
    fetcher = Fetcher(client)

    notebooks = fetcher.list_notebooks()
    if not notebooks:
        pytest.skip("No notebooks available")
    nb = notebooks[0]
    metas = list(fetcher.iter_notes(notebook_guid=nb.guid))
    if not metas:
        pytest.skip("No notes in first notebook")

    note_guid = metas[0].guid

    win = main_window.MainWindow(qapp)
    qtbot.addWidget(win)
    win.show()

    win._radio_token.setChecked(True)
    win._edit_token.setText(token)
    win._edit_output.setText(str(tmp_path))

    qtbot.mouseClick(win._btn_connect, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._grp_export.isEnabled(), timeout=60000)

    win._radio_note.setChecked(True)
    win._edit_guid.setText(note_guid)
    qtbot.mouseClick(win._btn_export, Qt.MouseButton.LeftButton)

    qtbot.waitUntil(lambda: win._progress.value() == 100, timeout=60000)
    assert "导出完成" in win._log_text.toPlainText()

    exported = list(tmp_path.rglob("*.md"))
    assert exported
