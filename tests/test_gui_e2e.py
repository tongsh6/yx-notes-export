import os

# pyright: reportMissingImports=false, reportOptionalMemberAccess=false

import pytest
from PySide6.QtCore import QObject, QTimer, Signal, Qt

from src.gui import main_window


class FakeConnectWorker(QObject):
    success = Signal(list, str)
    failure = Signal(str)

    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__()

    def start(self) -> None:
        QTimer.singleShot(0, self._emit_success)

    def _emit_success(self) -> None:
        self.success.emit([], "fake-token")


class FakeExportWorker(QObject):
    progress = Signal(int, int, str)
    note_done = Signal(str, str, bool, str)
    finished = Signal(int, int, int)
    error = Signal(str)

    def __init__(self, *_args, **_kwargs) -> None:
        super().__init__()

    def start(self) -> None:
        QTimer.singleShot(0, self._emit_step1)

    def abort(self) -> None:
        return None

    def _emit_step1(self) -> None:
        self.progress.emit(1, 2, "Note A")
        self.note_done.emit("g1", "Note A", True, "跳过")
        QTimer.singleShot(50, self._emit_step2)

    def _emit_step2(self) -> None:
        self.progress.emit(2, 2, "Note B")
        self.note_done.emit("g2", "Note B", False, "fail")
        QTimer.singleShot(50, self._emit_done)

    def _emit_done(self) -> None:
        self.finished.emit(0, 1, 1)


@pytest.mark.parametrize("mode", ["token", "password"])
def test_gui_flow_no_api(qapp, qtbot, tmp_path, monkeypatch, mode, screenshot_dir):
    # Use temp config path to avoid touching real config.yaml
    cfg_path = tmp_path / "config.yaml"
    monkeypatch.setattr(main_window, "_CONFIG_PATH", str(cfg_path))

    # Patch workers to avoid real API calls
    monkeypatch.setattr(main_window, "ConnectWorker", FakeConnectWorker)
    monkeypatch.setattr(main_window, "ExportWorker", FakeExportWorker)

    win = main_window.MainWindow(qapp)
    qtbot.addWidget(win)
    win.show()

    if mode == "token":
        win._radio_token.setChecked(True)
        win._edit_token.setText("fake")
    else:
        win._radio_password.setChecked(True)
        win._edit_username.setText("u")
        win._edit_password.setText("p")
        win._edit_ck.setText("ck")
        win._edit_cs.setText("cs")

    # Before connect: export panel disabled, connect button enabled
    assert not win._grp_export.isEnabled()
    assert win._btn_connect.isEnabled()

    # Use temp output for failure log
    win._edit_output.setText(str(tmp_path))

    # Connect
    qtbot.mouseClick(win._btn_connect, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: win._grp_export.isEnabled(), timeout=2000)

    # After connect: button text + label
    assert win._btn_connect.text() == "重新连接"
    assert "连接成功" in win._lbl_conn.text()
    assert win._grp_export.isEnabled()

    # Toggle advanced section (password mode only)
    if mode == "password":
        win._advanced._on_toggle()
        assert win._advanced._content.isVisible()
        # collapse back
        win._advanced._on_toggle()
        assert not win._advanced._content.isVisible()
    else:
        assert not win._advanced._content.isVisible()

    # Switch export scope: notebook list visible only for notebook mode
    win._radio_nb.setChecked(True)
    assert win._nb_list.isVisible()
    assert win._lbl_nb.isVisible()
    assert win._btn_refresh.isVisible()
    win._radio_note.setChecked(True)
    assert win._edit_guid.isVisible()
    assert win._lbl_guid.isVisible()
    win._radio_all.setChecked(True)
    assert not win._nb_list.isVisible()
    assert not win._edit_guid.isVisible()

    # GUID empty -> warning log
    win._radio_note.setChecked(True)
    win._edit_guid.setText("")
    qtbot.mouseClick(win._btn_export, Qt.MouseButton.LeftButton)
    assert "请输入笔记 GUID" in win._log_text.toPlainText()

    # Provide GUID and start
    win._edit_guid.setText("guid")
    qtbot.mouseClick(win._btn_export, Qt.MouseButton.LeftButton)
    assert not win._btn_export.isEnabled()
    assert win._btn_stop.isEnabled()

    qtbot.waitUntil(lambda: "/" in win._progress.format(), timeout=2000)
    assert "正在导出" in win._lbl_status.text()

    qtbot.waitUntil(lambda: win._progress.value() == 100, timeout=2000)
    qtbot.waitUntil(lambda: win._btn_export.isEnabled(), timeout=2000)
    qtbot.waitUntil(lambda: "导出完成" in win._log_text.toPlainText(), timeout=2000)
    log = win._log_text.toPlainText()
    assert "认证成功" in log
    assert "导出完成" in log
    assert "Note A" in log
    assert "Note B" in log
    assert "失败" in log
    assert "跳过" in log
    assert "完成" in win._progress.format()
    assert "完成" in win._lbl_status.text()
    assert "跳过" in win._lbl_status.text()
    assert win._btn_export.isEnabled()
    assert not win._btn_stop.isEnabled()

    fail_log = tmp_path / "export-failures.txt"
    assert fail_log.exists()
    content = fail_log.read_text(encoding="utf-8")
    assert "Note B" in content

    # Screenshot on demand: use env var to avoid noisy output
    if os.environ.get("YX_SCREENSHOT"):
        path = screenshot_dir / f"gui_{mode}.png"
        win.grab().save(str(path))
