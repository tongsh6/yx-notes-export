"""
GUI 入口：启动桌面图形界面。

用法：
    python gui_main.py
"""

import ctypes
import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.gui import theme as _theme
from src.gui.main_window import MainWindow

# 应用图标路径（与 src/gui 同目录）
_APP_ICON_PATH = Path(__file__).resolve().parent / "src" / "gui" / "app_icon.svg"


def _install_exception_hook() -> None:
    """将未捕获异常转为弹窗，防止程序无声退出。"""

    def _hook(exc_type, exc_value, exc_tb):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(tb, file=sys.stderr, flush=True)
        dlg = QMessageBox()
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.setWindowTitle("未捕获异常")
        dlg.setText(str(exc_value))
        dlg.setDetailedText(tb)
        dlg.exec()

    sys.excepthook = _hook

def _set_windows_taskbar_app_id() -> None:
    """设置 Windows 任务栏应用 ID，使任务栏显示本程序图标而非 Python 图标。须在创建任何窗口前调用。"""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("yx-notes-export.gui.1")
    except Exception:
        pass


def main() -> None:
    _install_exception_hook()
    _set_windows_taskbar_app_id()
    # 高 DPI 支持（Windows 缩放场景）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("印象笔记导出工具")
    app.setOrganizationName("yx-notes-export")
    if _APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_APP_ICON_PATH)))

    # 默认深色主题
    _theme.apply_dark(app)

    window = MainWindow(app)
    if _APP_ICON_PATH.exists():
        window.setWindowIcon(QIcon(str(_APP_ICON_PATH)))
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
