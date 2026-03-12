"""
主题管理：纯 QSS 实现深色/浅色双主题，无第三方库依赖。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

# 勾选框选中态对勾图标路径（绝对路径、正斜杠，供 QSS image: url() 使用；Qt 在 Windows 下对 file:// 支持不稳定）
_CHECK_ICON_PATH = str(Path(__file__).resolve().parent / "check_white.svg").replace("\\", "/")

# ── 深色主题 ──────────────────────────────────────────────────────────────

_DARK_QSS = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #1e1e2e;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    font-weight: 600;
    color: #cdd6f4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 8px;
    color: #cdd6f4;
    min-height: 32px;
}
QLineEdit:focus {
    border: 1px solid #89b4fa;
}
QLineEdit:disabled {
    background-color: #1e1e2e;
    color: #585b70;
}
QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 5px 14px;
    color: #cdd6f4;
    min-height: 32px;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #585b70;
    border-color: #313244;
}
QPushButton[class="primary"] {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    font-weight: 600;
}
QPushButton[class="primary"]:hover {
    background-color: #b4befe;
}
QPushButton[class="primary"]:pressed {
    background-color: #74c7ec;
}
QPushButton[class="primary"]:disabled {
    background-color: #45475a;
    color: #585b70;
}
QPushButton[class="danger"] {
    background-color: #f38ba8;
    color: #1e1e2e;
    border: none;
    font-weight: 600;
}
QPushButton[class="danger"]:hover {
    background-color: #fab387;
}
QPushButton[class="danger"]:disabled {
    background-color: #45475a;
    color: #585b70;
}
QRadioButton {
    spacing: 6px;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
}
QRadioButton::indicator:unchecked {
    border: 1px solid #585b70;
    background-color: #1e1e2e;
    border-radius: 7px;
}
QRadioButton::indicator:checked {
    border: 1px solid #89b4fa;
    background-color: #89b4fa;
    border-radius: 7px;
}
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
}
QCheckBox::indicator:unchecked {
    border: 1px solid #6c7086;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-image: url(%s);
    background-color: #89b4fa;
    border: 1px solid #89b4fa;
}
QListWidget {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 4px;
}
QListWidget::item {
    padding: 4px 8px;
    border-radius: 2px;
}
QListWidget::item:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QListWidget::item:hover:!selected {
    background-color: #45475a;
}
QPlainTextEdit {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 4px;
    color: #cdd6f4;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 12px;
}
QProgressBar {
    border: 1px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
    height: 16px;
    text-align: center;
    color: #cdd6f4;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 3px;
}
QScrollBar:vertical {
    background: #313244;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #585b70;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLabel { background: transparent; }
QSplitter::handle { background: #45475a; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:horizontal:hover { background: #585b70; }
""" % (_CHECK_ICON_PATH,)

# ── 浅色主题 ──────────────────────────────────────────────────────────────

_LIGHT_QSS = """
QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
    font-size: 13px;
}
QMainWindow, QDialog {
    background-color: #eff1f5;
}
QGroupBox {
    border: 1px solid #bcc0cc;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 18px;
    font-weight: 600;
    color: #4c4f69;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    padding: 5px 8px;
    color: #4c4f69;
    min-height: 32px;
}
QLineEdit:focus {
    border: 1px solid #1e66f5;
}
QLineEdit:disabled {
    background-color: #eff1f5;
    color: #9ca0b0;
}
QPushButton {
    background-color: #e6e9ef;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    padding: 5px 14px;
    color: #4c4f69;
    min-height: 32px;
}
QPushButton:hover {
    background-color: #dce0e8;
}
QPushButton:pressed {
    background-color: #ccd0da;
}
QPushButton:disabled {
    background-color: #eff1f5;
    color: #9ca0b0;
}
QPushButton[class="primary"] {
    background-color: #1e66f5;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton[class="primary"]:hover {
    background-color: #04a5e5;
}
QPushButton[class="primary"]:pressed {
    background-color: #209fb5;
}
QPushButton[class="primary"]:disabled {
    background-color: #ccd0da;
    color: #9ca0b0;
}
QPushButton[class="danger"] {
    background-color: #d20f39;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton[class="danger"]:hover {
    background-color: #e64553;
}
QPushButton[class="danger"]:disabled {
    background-color: #ccd0da;
    color: #9ca0b0;
}
QRadioButton { spacing: 6px; }
QRadioButton::indicator:unchecked {
    border: 1px solid #9ca0b0;
    background-color: #eff1f5;
    border-radius: 7px;
}
QRadioButton::indicator:checked {
    border: 1px solid #1e66f5;
    background-color: #1e66f5;
    border-radius: 7px;
}
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 3px;
}
QCheckBox::indicator:unchecked {
    border: 1px solid #9ca0b0;
    background-color: #e6e9ef;
}
QCheckBox::indicator:checked {
    background-image: url(%s);
    background-color: #1e66f5;
    border: 1px solid #1e66f5;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
}
QListWidget::item {
    padding: 4px 8px;
    border-radius: 2px;
}
QListWidget::item:selected {
    background-color: #1e66f5;
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: #dce0e8;
}
QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    color: #4c4f69;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 12px;
}
QProgressBar {
    border: 1px solid #bcc0cc;
    border-radius: 4px;
    background-color: #e6e9ef;
    height: 16px;
    text-align: center;
    color: #4c4f69;
}
QProgressBar::chunk {
    background-color: #1e66f5;
    border-radius: 3px;
}
QScrollBar:vertical {
    background: #e6e9ef;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #bcc0cc;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLabel { background: transparent; }
QSplitter::handle { background: #bcc0cc; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:horizontal:hover { background: #a6adc8; }
""" % (_CHECK_ICON_PATH,)


def apply_dark(app: QApplication) -> None:
    app.setStyleSheet(_DARK_QSS)


def apply_light(app: QApplication) -> None:
    app.setStyleSheet(_LIGHT_QSS)


def toggle(app: QApplication, current: str) -> str:
    """切换主题，返回新主题名称 ('dark' | 'light')。"""
    if current == "dark":
        apply_light(app)
        return "light"
    else:
        apply_dark(app)
        return "dark"
