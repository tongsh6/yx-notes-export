"""
GUI 入口：启动桌面图形界面。

用法：
    python gui_main.py
"""

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from src.gui import theme as _theme
from src.gui.main_window import MainWindow


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

def main() -> None:
    _install_exception_hook()
    # 高 DPI 支持（Windows 缩放场景）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("印象笔记导出工具")
    app.setOrganizationName("yx-notes-export")

    # 默认深色主题
    _theme.apply_dark(app)

    window = MainWindow(app)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
