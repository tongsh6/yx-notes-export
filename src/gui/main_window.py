"""
主窗口：认证面板 + 导出面板 + 进度与日志区域。
"""
# pyright: reportMissingImports=false, reportOptionalMemberAccess=false, reportUninitializedInstanceVariable=false

from __future__ import annotations

import os
from time import monotonic
from typing import Any, List, Optional

import yaml
from PySide6.QtCore import Qt, QSize, QThread, QTimer
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.auth import AuthConfig
from src.error_codes import classify_export_error
from src.event_log import NullEventLogger, create_export_logger
from src.fetcher import NotebookInfo
from src.gui import theme as _theme
from src.gui.worker import ConnectWorker, ExportWorker
from src.summary import write_export_summary

_CONFIG_PATH = "config.yaml"


# ── 自适应高度的 QStackedWidget ─────────────────────────────────────────────


class _AdaptiveStack(QStackedWidget):
    """高度跟随当前页面，不被最高子页撑开。"""

    def sizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.minimumSizeHint()
        return super().minimumSizeHint()

    def on_current_changed(self, _idx: int):
        # 切换页时让布局重新计算尺寸
        self.updateGeometry()


# ── 可折叠分组 ───────────────────────────────────────────────────────────────


class _CollapsibleSection(QWidget):
    """带折叠箭头的轻量级折叠容器。"""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题行（点击展开/收起）
        self._toggle_btn = QPushButton(f"▶  {title}")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._toggle_btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 2px 0; color: #74c0fc; "
            "font-size: 12px; border: none; background: transparent; }"
            "QPushButton:hover { color: #89b4fa; }"
        )
        self._toggle_btn.clicked.connect(self._on_toggle)
        outer.addWidget(self._toggle_btn)

        # 内容容器
        self._content = QWidget()
        self._content.setVisible(False)
        self._content_layout = QFormLayout(self._content)
        self._content_layout.setContentsMargins(0, 6, 0, 0)
        self._content_layout.setSpacing(6)
        self._content_layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        outer.addWidget(self._content)

    def add_row(self, label: str, widget: QWidget) -> None:
        self._content_layout.addRow(label, widget)

    def _on_toggle(self) -> None:
        self._expanded = not self._expanded
        arrow = "▼" if self._expanded else "▶"
        title = self._toggle_btn.text()[2:]  # 去掉前缀箭头+空格
        self._toggle_btn.setText(f"{arrow}  {title}")
        self._content.setVisible(self._expanded)
        self.updateGeometry()
        # 通知父布局刷新
        parent = self.parentWidget()
        if parent is not None:
            parent.adjustSize()


class MainWindow(QMainWindow):
    _btn_theme: QPushButton | None = None
    _btn_clear_log: QPushButton | None = None
    _radio_token: QRadioButton | None = None
    _radio_password: QRadioButton | None = None
    _auth_stack: _AdaptiveStack | None = None
    _btn_connect: QPushButton | None = None
    _lbl_conn: QLabel | None = None
    _edit_token: QLineEdit | None = None
    _edit_username: QLineEdit | None = None
    _edit_password: QLineEdit | None = None
    _advanced: _CollapsibleSection | None = None
    _edit_ck: QLineEdit | None = None
    _edit_cs: QLineEdit | None = None
    _grp_export: QGroupBox | None = None
    _radio_all: QRadioButton | None = None
    _radio_nb: QRadioButton | None = None
    _radio_note: QRadioButton | None = None
    _lbl_nb: QLabel | None = None
    _btn_refresh: QPushButton | None = None
    _nb_list: QListWidget | None = None
    _lbl_guid: QLabel | None = None
    _edit_guid: QLineEdit | None = None
    _chk_resume: QCheckBox | None = None
    _chk_fail_log: QCheckBox | None = None
    _edit_output: QLineEdit | None = None
    _btn_browse: QPushButton | None = None
    _btn_export: QPushButton | None = None
    _btn_stop: QPushButton | None = None
    _btn_skip_note: QPushButton | None = None
    _log_text: QPlainTextEdit | None = None
    _progress: QProgressBar | None = None
    _lbl_status: QLabel | None = None
    _lbl_activity_age: QLabel | None = None

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._theme_name = "dark"
        self._all_notebooks: List[NotebookInfo] = []
        self._connect_worker: Optional[ConnectWorker] = None
        self._export_worker: Optional[ExportWorker] = None
        self._connect_timeout_timer = QTimer(self)
        self._connect_timeout_timer.setSingleShot(True)
        self._connect_timeout_timer.timeout.connect(self._on_connect_timeout)
        self._export_watchdog_timer = QTimer(self)
        self._export_watchdog_timer.setInterval(5000)
        self._export_watchdog_timer.timeout.connect(self._on_export_watchdog_tick)
        self._session_token: Optional[str] = None  # 密码登录后从 API 获取的 token
        self._skipped_titles: List[str] = []
        self._failed_items: List[tuple[str, str, str, str]] = []
        self._stop_requested = False
        self._last_export_activity_at = 0.0
        self._last_export_activity_msg = ""
        self._last_stall_hint_at = 0.0
        self._last_runtime_log_msg = ""
        self._event_logger = NullEventLogger()
        self._defunct_workers: List[object] = []  # 保持 QThread 引用直到线程真正退出

        self.setWindowTitle("印象笔记导出工具")
        self.setMinimumSize(860, 580)
        self.resize(1060, 680)

        self._build_ui()
        self._load_config()

    # ── UI 构建 ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 640])
        root_layout.addWidget(splitter, 1)

        root_layout.addWidget(self._build_statusbar())
        self.setCentralWidget(root)

    # ── 顶部标题栏 ─────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("🗒️  印象笔记导出工具")
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)
        layout.addStretch()

        self._btn_theme = QPushButton("☀ 浅色")
        self._btn_theme.setFixedSize(QSize(80, 30))
        self._btn_theme.clicked.connect(self._toggle_theme)
        self._btn_clear_log = QPushButton("清空")
        self._btn_clear_log.setFixedSize(QSize(80, 30))
        self._btn_clear_log.clicked.connect(lambda: self._log_text.clear())
        layout.addWidget(self._btn_clear_log)
        layout.addWidget(self._btn_theme)
        return bar

    # ── 左侧控制面板 ───────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QWidget:
        # 内容容器（放在 ScrollArea 里，防止内容过多时布局错位）
        inner = QWidget()
        inner.setMinimumWidth(340)
        inner.setMaximumWidth(480)
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(16, 10, 12, 12)
        layout.setSpacing(16)
        layout.addWidget(self._build_auth_group())
        layout.addWidget(self._build_export_group())
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setMinimumWidth(360)
        return scroll

    # ── 认证设置 ───────────────────────────────────────────────────────────────

    def _build_auth_group(self) -> QGroupBox:
        grp = QGroupBox("认证设置")
        layout = QVBoxLayout(grp)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # 认证方式切换
        mode_row = QHBoxLayout()
        self._radio_token = QRadioButton("Developer Token")
        self._radio_password = QRadioButton("用户名 + 密码")
        self._radio_token.setChecked(True)
        self._radio_token.toggled.connect(self._on_auth_mode_changed)
        mode_row.addWidget(self._radio_token)
        mode_row.addWidget(self._radio_password)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # 自适应高度的堆叠表单
        self._auth_stack = _AdaptiveStack()
        self._auth_stack.currentChanged.connect(self._auth_stack.on_current_changed)
        self._auth_stack.addWidget(self._build_token_form())
        self._auth_stack.addWidget(self._build_password_form())
        layout.addWidget(self._auth_stack)

        # 连接按钮行
        btn_row = QHBoxLayout()
        self._btn_connect = QPushButton("连  接")
        self._btn_connect.setProperty("class", "primary")
        self._btn_connect.setMinimumWidth(96)
        self._btn_connect.setFixedHeight(30)
        self._btn_connect.clicked.connect(self._on_connect)
        self._lbl_conn = QLabel("")
        self._lbl_conn.setWordWrap(True)
        btn_row.addWidget(self._btn_connect)
        btn_row.addWidget(self._lbl_conn, 1)
        layout.addLayout(btn_row)
        return grp

    def _build_token_form(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 4, 0, 4)
        form.setSpacing(6)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self._edit_token = QLineEdit()
        self._edit_token.setPlaceholderText("S=s1:U=xxx:E=xxx:C=xxx:...")
        self._edit_token.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Token：", self._edit_token)

        hint = QLabel(
            '<a href="https://app.yinxiang.com/api/DeveloperToken.action">获取 Developer Token ↗</a>'
        )
        hint.setOpenExternalLinks(True)
        hint.setStyleSheet("font-size: 11px;")
        form.addRow("", hint)
        return w

    def _build_password_form(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(0, 4, 0, 4)
        form.setSpacing(6)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self._edit_username = QLineEdit()
        self._edit_username.setPlaceholderText("your@email.com")
        form.addRow("用户名：", self._edit_username)

        self._edit_password = QLineEdit()
        self._edit_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_password.setPlaceholderText("••••••••")
        form.addRow("密码：", self._edit_password)

        # Consumer Key/Secret 折叠为高级选项
        self._advanced = _CollapsibleSection("高级选项（Consumer Key/Secret）")
        self._edit_ck = QLineEdit()
        self._edit_ck.setPlaceholderText("来自印象笔记开发者平台")
        self._advanced.add_row("Consumer Key：", self._edit_ck)
        self._edit_cs = QLineEdit()
        self._edit_cs.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit_cs.setPlaceholderText("来自印象笔记开发者平台")
        self._advanced.add_row("Consumer Secret：", self._edit_cs)

        # 把 _CollapsibleSection 当整行插入（跨越两列）
        form.addRow(self._advanced)

        hint = QLabel(
            '<a href="https://dev.yinxiang.com/">开发者平台 → 申请 API Key ↗</a>'
        )
        hint.setOpenExternalLinks(True)
        hint.setStyleSheet("font-size: 11px;")
        form.addRow("", hint)
        return w

    def _on_auth_mode_changed(self) -> None:
        idx = 0 if self._radio_token.isChecked() else 1
        self._auth_stack.setCurrentIndex(idx)
        self._auth_stack.updateGeometry()

    # ── 导出设置 ───────────────────────────────────────────────────────────────

    def _build_export_group(self) -> QGroupBox:
        self._grp_export = QGroupBox("导出设置")
        self._grp_export.setEnabled(False)
        layout = QVBoxLayout(self._grp_export)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # 导出范围
        scope_row = QHBoxLayout()
        self._radio_all = QRadioButton("全量")
        self._radio_nb = QRadioButton("指定笔记本")
        self._radio_note = QRadioButton("指定笔记 GUID")
        self._radio_all.setChecked(True)
        for rb in (self._radio_all, self._radio_nb, self._radio_note):
            rb.toggled.connect(self._on_scope_changed)
            scope_row.addWidget(rb)
        scope_row.addStretch()
        layout.addLayout(scope_row)

        # 笔记本列表（仅"指定笔记本"时显示）
        nb_hdr = QHBoxLayout()
        self._lbl_nb = QLabel("选择笔记本（可多选）：")
        self._btn_refresh = QPushButton("刷新笔记本列表")
        self._btn_refresh.setFixedSize(128, 20)
        self._btn_refresh.setToolTip("刷新笔记本列表")
        self._btn_refresh.clicked.connect(self._on_connect)
        nb_hdr.addWidget(self._lbl_nb)
        nb_hdr.addStretch()
        nb_hdr.addWidget(self._btn_refresh)
        layout.addLayout(nb_hdr)

        self._nb_list = QListWidget()
        self._nb_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._nb_list.setMinimumHeight(180)
        self._nb_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._nb_list)

        # 笔记 GUID 输入（仅"指定笔记"时显示）
        self._lbl_guid = QLabel("笔记 GUID：")
        self._edit_guid = QLineEdit()
        self._edit_guid.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        layout.addWidget(self._lbl_guid)
        layout.addWidget(self._edit_guid)

        for w in (
            self._lbl_nb,
            self._btn_refresh,
            self._nb_list,
            self._lbl_guid,
            self._edit_guid,
        ):
            w.setVisible(False)

        # 断点续传 + 失败记录
        self._chk_resume = QCheckBox("断点续传（跳过已导出且未更新的笔记）")
        self._chk_resume.setChecked(True)
        self._chk_fail_log = QCheckBox("保存失败记录")
        self._chk_fail_log.setChecked(True)
        opts_row = QHBoxLayout()
        opts_row.addWidget(self._chk_resume)
        opts_row.addWidget(self._chk_fail_log)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        lbl_output = QLabel("保存至：")
        self._edit_output = QLineEdit()
        self._edit_output.setPlaceholderText("输出目录（默认 下载 文件夹）")
        self._edit_output.setFixedHeight(32)
        self._btn_browse = QPushButton("浏览…")
        self._btn_browse.setMinimumWidth(80)
        self._btn_browse.setFixedHeight(32)
        self._btn_browse.setToolTip("选择输出目录")
        self._btn_browse.clicked.connect(self._on_browse)
        self._btn_export = QPushButton("开始导出")
        self._btn_export.setProperty("class", "primary")
        self._btn_export.setMinimumWidth(96)
        self._btn_export.setFixedHeight(34)
        self._btn_export.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_export.clicked.connect(self._on_export)
        self._btn_export_failed = QPushButton("仅重导失败")
        self._btn_export_failed.setMinimumWidth(96)
        self._btn_export_failed.setFixedHeight(34)
        self._btn_export_failed.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_export_failed.clicked.connect(self._on_export_failed_only)
        self._btn_stop = QPushButton("停止")
        self._btn_stop.setProperty("class", "danger")
        self._btn_stop.setMinimumWidth(88)
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_skip_note = QPushButton("跳过当前")
        self._btn_skip_note.setMinimumWidth(96)
        self._btn_skip_note.setFixedHeight(34)
        self._btn_skip_note.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._btn_skip_note.setEnabled(False)
        self._btn_skip_note.clicked.connect(self._on_skip_current_note)
        layout.addSpacing(10)
        output_row.addWidget(lbl_output)
        output_row.addWidget(self._edit_output, 1)
        output_row.addWidget(self._btn_browse)
        layout.addLayout(output_row)

        actions_grid = QGridLayout()
        actions_grid.setContentsMargins(0, 10, 0, 0)
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(12)
        actions_grid.addWidget(self._btn_export, 0, 0)
        actions_grid.addWidget(self._btn_export_failed, 0, 1)
        actions_grid.addWidget(self._btn_skip_note, 1, 0)
        actions_grid.addWidget(self._btn_stop, 1, 1)
        actions_grid.setColumnStretch(0, 1)
        actions_grid.setColumnStretch(1, 1)
        layout.addLayout(actions_grid)

        return self._grp_export

    # ── 右侧日志 ───────────────────────────────────────────────────────────────

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 16, 12)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("运行日志"))
        hdr.addStretch()
        layout.addLayout(hdr)

        self._log_text = QPlainTextEdit()
        self._log_text.setObjectName("logArea")
        self._log_text.setReadOnly(True)
        layout.addWidget(self._log_text, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(18)
        layout.addWidget(self._progress)
        return panel

    # ── 底部状态栏 ─────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(36)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)
        self._lbl_status = QLabel("就绪")
        layout.addWidget(self._lbl_status)
        layout.addStretch()
        self._lbl_activity_age = QLabel("最近活动：--")
        layout.addWidget(self._lbl_activity_age)
        return bar

    # ── 事件处理 ───────────────────────────────────────────────────────────────

    def _on_scope_changed(self) -> None:
        show_nb = self._radio_nb.isChecked()
        show_note = self._radio_note.isChecked()
        for w in (self._lbl_nb, self._btn_refresh, self._nb_list):
            w.setVisible(show_nb)
        for w in (self._lbl_guid, self._edit_guid):
            w.setVisible(show_note)

    def _on_browse(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "选择导出目录", self._edit_output.text()
        )
        if d:
            self._edit_output.setText(d)

    def _toggle_theme(self) -> None:
        self._theme_name = _theme.toggle(self._app, self._theme_name)
        self._btn_theme.setText("☀ 浅色" if self._theme_name == "dark" else "🌙 深色")
        # 折叠区按钮颜色跟随主题
        color = "#74c0fc" if self._theme_name == "dark" else "#1e66f5"
        hover = "#89b4fa" if self._theme_name == "dark" else "#04a5e5"
        self._advanced._toggle_btn.setStyleSheet(
            f"QPushButton {{ text-align: left; padding: 2px 0; color: {color}; "
            f"font-size: 12px; border: none; background: transparent; }}"
            f"QPushButton:hover {{ color: {hover}; }}"
        )

    # ── 连接 ───────────────────────────────────────────────────────────────────

    def _on_connect(self) -> None:
        existing = self._connect_worker
        if existing and getattr(existing, "isRunning", lambda: False)():
            self._append_log("[警告] 正在连接中，请稍候…")
            return

        cfg = self._collect_auth()
        if cfg is None:
            return
        self._btn_connect.setEnabled(False)
        self._btn_connect.setText("连接中…")
        self._set_conn_label("正在认证，请稍候…", "info")
        self._append_log("正在连接印象笔记服务器…")

        worker: Any = ConnectWorker(cfg)
        self._connect_worker = worker
        if isinstance(worker, QThread):
            self._defunct_workers.append(worker)
            worker.finished.connect(self._reap_defunct_workers)
        getattr(worker, "success").connect(self._on_conn_ok)
        getattr(worker, "failure").connect(self._on_conn_fail)
        worker.start()
        self._connect_timeout_timer.start(30000)

    def _on_connect_timeout(self) -> None:
        worker = self._connect_worker
        if worker and getattr(worker, "isRunning", lambda: False)():
            worker.abort()
            worker.requestInterruption()
            # ⚠️  严禁调用 terminate() + wait()：
            # terminate() 在 Windows 上调用 TerminateThread()，
            # 若线程正在 socket 阻塞调用中（CPython 已释放 GIL），
            # GIL 内部计数无法归还，主线程下次调度时状态损坏 → 连程 crash。
            # 正确做法：断开信号，让线程随 socket 超时自然退出。
            try:
                getattr(worker, "success").disconnect()
                getattr(worker, "failure").disconnect()
            except RuntimeError:
                pass  # 信号已断开时 disconnect() 会抛出，忽略即可
            self._connect_worker = None
        self._btn_connect.setEnabled(True)
        self._btn_connect.setText("重新连接")
        self._set_conn_label("✗ 连接超时，请重试", "err")
        self._append_log("[错误] 连接超时（30s）")

    def _on_conn_ok(self, notebooks: list[NotebookInfo], session_token: str) -> None:
        self._connect_timeout_timer.stop()
        self._connect_worker = None
        self._all_notebooks = notebooks
        self._session_token = session_token  # 缓存 API 返回的 token，后续不再需要密码
        self._btn_connect.setEnabled(True)
        self._btn_connect.setText("重新连接")
        n = len(notebooks)
        self._set_conn_label(f"✓ 连接成功，共 {n} 个笔记本", "ok")
        self._grp_export.setEnabled(True)
        self._populate_nb_list(notebooks)
        self._save_config()  # 此时以 token 模式保存，不落盘密码
        self._append_log(f"认证成功 — {n} 个笔记本")

    def _on_conn_fail(self, msg: str) -> None:
        self._connect_timeout_timer.stop()
        self._connect_worker = None
        self._btn_connect.setEnabled(True)
        self._btn_connect.setText("重新连接")
        self._set_conn_label(f"✗ {msg}", "err")
        self._append_log(f"[错误] 连接失败：{msg}")

    def _populate_nb_list(self, notebooks: List[NotebookInfo]) -> None:
        self._nb_list.clear()
        for nb in sorted(notebooks, key=lambda n: (n.stack or "", n.name)):
            label = f"[{nb.stack}]  {nb.name}" if nb.stack else nb.name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, nb)
            self._nb_list.addItem(item)

    # ── 导出 ───────────────────────────────────────────────────────────────────

    def _on_export(self) -> None:
        cfg = self._collect_auth()
        if cfg is None:
            return
        output_dir = self._edit_output.text().strip() or _default_output_dir()

        target_nbs: List[NotebookInfo] = []
        note_guid: Optional[str] = None

        if self._radio_nb.isChecked():
            selected = self._nb_list.selectedItems()
            if not selected:
                self._append_log("[警告] 请在列表中选择至少一个笔记本")
                return
            target_nbs = [it.data(Qt.ItemDataRole.UserRole) for it in selected]
        elif self._radio_note.isChecked():
            note_guid = self._edit_guid.text().strip()
            if not note_guid:
                self._append_log("[警告] 请输入笔记 GUID")
                return

        self._start_export(
            cfg=cfg,
            output_dir=output_dir,
            notebooks=target_nbs,
            note_guid=note_guid,
            failed_guids=None,
        )

    def _on_export_failed_only(self) -> None:
        cfg = self._collect_auth()
        if cfg is None:
            return
        output_dir = self._edit_output.text().strip() or _default_output_dir()
        fail_log = os.path.join(output_dir, "export-failures.txt")
        if not os.path.exists(fail_log):
            self._append_log(f"[警告] 未找到失败记录文件：{fail_log}")
            return

        failed_guids: List[str] = []
        try:
            with open(fail_log, encoding="utf-8") as f:
                for line in f:
                    cols = line.rstrip("\n").split("\t")
                    if not cols:
                        continue
                    guid = cols[0].strip()
                    if guid:
                        failed_guids.append(guid)
        except Exception as e:
            self._append_log(f"[错误] 读取失败记录失败：{e}")
            return

        # 去重保序
        uniq: List[str] = []
        seen: set[str] = set()
        for g in failed_guids:
            if g in seen:
                continue
            seen.add(g)
            uniq.append(g)

        if not uniq:
            self._append_log(
                "[警告] 失败记录中没有可用 GUID（请先使用新版本导出以写入 GUID）"
            )
            return

        self._append_log(f"将重导失败记录：{len(uniq)} 条")
        self._start_export(
            cfg=cfg,
            output_dir=output_dir,
            notebooks=[],
            note_guid=None,
            failed_guids=uniq,
        )

    def _start_export(
        self,
        cfg: AuthConfig,
        output_dir: str,
        notebooks: List[NotebookInfo],
        note_guid: Optional[str],
        failed_guids: Optional[List[str]],
    ) -> None:
        self._stop_export_watchdog()
        existing = self._export_worker
        if existing and existing.isRunning():
            self._append_log("[警告] 上一次导出任务仍在运行，请先等待其停止完成")
            self._lbl_status.setText("仍有导出任务运行中")
            return

        self._btn_export.setEnabled(False)
        self._btn_export_failed.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_skip_note.setEnabled(False)
        self._progress.setRange(0, 0)
        self._progress.setFormat("准备中…")
        self._lbl_status.setText("准备中…")
        self._append_log("=" * 48)
        self._append_log(f"开始导出 → {os.path.abspath(output_dir)}")
        self._append_log("正在统计笔记列表…")
        self._skipped_titles = []
        self._failed_items = []
        self._stop_requested = False
        try:
            self._event_logger = create_export_logger("gui")
            self._append_log(f"日志文件：{self._event_logger.file_path}")
            self._event_logger.emit(
                "session_start",
                output_dir=os.path.abspath(output_dir),
                scope=(
                    "failed" if failed_guids else "note" if note_guid else "notebooks"
                ),
            )
        except Exception as e:
            self._append_log(f"[警告] 初始化结构化日志失败：{e}")
            self._event_logger = NullEventLogger()

        worker: Any = ExportWorker(
            auth_cfg=cfg,
            output_dir=output_dir,
            notebooks=notebooks,
            note_guid=note_guid,
            failed_guids=failed_guids,
            all_notebooks=self._all_notebooks,
            resume=self._chk_resume.isChecked(),
            event_logger=self._event_logger,
        )
        self._export_worker = worker
        if isinstance(worker, QThread):
            self._defunct_workers.append(worker)
            worker.finished.connect(self._reap_defunct_workers)
        getattr(worker, "progress").connect(
            lambda current, total, title, w=worker: self._on_exp_progress_for(
                w, current, total, title
            )
        )
        getattr(worker, "note_done").connect(
            lambda *args, w=worker: self._on_note_done_for(w, *args)
        )
        if hasattr(worker, "activity"):
            getattr(worker, "activity").connect(
                lambda msg, w=worker: self._on_exp_activity_for(w, msg)
            )
        if hasattr(worker, "export_done"):
            getattr(worker, "export_done").connect(
                lambda ok, fail, skipped, w=worker: self._on_exp_finished_for(
                    w, ok, fail, skipped
                )
            )
        elif hasattr(worker, "finished"):
            getattr(worker, "finished").connect(
                lambda ok, fail, skipped, w=worker: self._on_exp_finished_for(
                    w, ok, fail, skipped
                )
            )
        getattr(worker, "error").connect(
            lambda msg, w=worker: self._on_exp_error_for(w, msg)
        )
        worker.start()
        self._last_runtime_log_msg = ""
        self._touch_export_activity("导出任务已启动", log=False)
        self._export_watchdog_timer.start()

    def _on_stop(self) -> None:
        if self._export_worker:
            self._stop_requested = True
            self._btn_skip_note.setEnabled(False)
            request_interrupt = getattr(
                self._export_worker, "requestInterruption", None
            )
            if callable(request_interrupt):
                request_interrupt()
            abort = getattr(self._export_worker, "abort", None)
            if callable(abort):
                abort()
            self._event_logger.emit("session_stop")
            self._append_log("[用户] 已发送停止信号，等待收尾…")
            self._lbl_status.setText("已停止，等待收尾…")
            self._btn_stop.setEnabled(False)
            QTimer.singleShot(15000, self._on_stop_timeout)

    def _on_stop_timeout(self) -> None:
        worker = self._export_worker
        if worker and worker.isRunning():
            # ⚠️  严禁 terminate()：理由同 _on_connect_timeout。
            # 已发出 abort，线程最终会随 socket 超时自然退出。
            # 但这里必须强制重置 UI：若线程长期挂起，用户将无法重新导出。
            self._append_log(
                "[提示] 线程未及时退出，已强制重置界面。导出线程仍在后台运行直至 socket 超时。"
            )
            self._lbl_status.setText("已停止")
            self._progress.setRange(0, 100)
            self._progress.setValue(0)
            self._progress.setFormat("已停止")
            self._btn_export.setEnabled(True)
            self._btn_export_failed.setEnabled(True)
            self._btn_skip_note.setEnabled(False)
            self._btn_stop.setEnabled(False)
            self._export_worker = None
            self._stop_export_watchdog()

    def _on_skip_current_note(self) -> None:
        worker = self._export_worker
        if not worker or not worker.isRunning():
            return
        request_skip = getattr(worker, "request_skip_current_note", None)
        if not callable(request_skip):
            self._append_log("[提示] 当前导出线程不支持“跳过当前笔记”。")
            return
        request_skip()
        self._btn_skip_note.setEnabled(False)
        self._append_log("[用户] 已请求跳过当前笔记，等待本次网络请求返回…")
        self._lbl_status.setText("已请求跳过当前笔记，等待收尾…")
        self._event_logger.emit("session_skip_current")

    def _reap_defunct_workers(self) -> None:
        """由 QThread.finished 信号触发（主线程 QueuedConnection）。

        用 sender() 直接识别完成的 worker 并移除，避免用 isRunning() 带来的
        竞态（Qt 在发出 finished 信号后才将 d->running 置 false，两者之间有微小窗口）。
        """
        done = self.sender()
        if done is not None and done in self._defunct_workers:
            self._defunct_workers.remove(done)

    def _on_exp_progress_for(
        self, worker, current: int, total: int, title: str
    ) -> None:
        if worker is not self._export_worker:
            return
        self._on_exp_progress(current, total, title)

    def _on_note_done_for(self, worker, *args) -> None:
        if worker is not self._export_worker:
            return
        self._on_note_done(*args)

    def _on_exp_finished_for(self, worker, ok: int, fail: int, skipped: int) -> None:
        if worker is not self._export_worker:
            return
        summary: Optional[dict[str, object]] = None
        get_summary = getattr(worker, "get_summary", None)
        if callable(get_summary):
            summary_obj = get_summary()
            if isinstance(summary_obj, dict):
                normalized_summary: dict[str, object] = {}
                for key, value in summary_obj.items():
                    if isinstance(key, str):
                        normalized_summary[key] = value
                summary = normalized_summary
        self._on_exp_finished(ok, fail, skipped, summary)

    def _on_exp_error_for(self, worker, msg: str) -> None:
        if worker is not self._export_worker:
            return
        self._on_exp_error(msg)

    def _on_exp_activity_for(self, worker, msg: str) -> None:
        if worker is not self._export_worker:
            return
        self._on_exp_activity(msg)

    def _on_exp_progress(self, current: int, total: int, title: str) -> None:
        self._touch_export_activity(f"正在导出：{title}", log=False)
        if total <= 0:
            self._progress.setRange(0, 0)
            self._progress.setFormat("统计中…")
            self._lbl_status.setText(title)
            return
        if self._progress.minimum() == 0 and self._progress.maximum() == 0:
            self._progress.setRange(0, 100)
        pct = int(current / total * 100) if total else 0
        self._progress.setValue(pct)
        self._progress.setFormat(f"{current}/{total}  {pct}%")
        self._lbl_status.setText(f"正在导出：{title}")

    def _on_exp_activity(self, msg: str) -> None:
        self._touch_export_activity(msg, log=True)
        if self._export_worker and self._export_worker.isRunning():
            self._lbl_status.setText(f"处理中：{msg}")

    def _touch_export_activity(self, msg: str, log: bool) -> None:
        self._last_export_activity_at = monotonic()
        self._last_export_activity_msg = msg
        self._update_activity_age_label(0)
        self._btn_skip_note.setEnabled(False)
        if log and msg != self._last_runtime_log_msg:
            self._append_log(f"[状态] {msg}")
            self._last_runtime_log_msg = msg

    def _on_export_watchdog_tick(self) -> None:
        worker = self._export_worker
        if not worker or not worker.isRunning():
            self._stop_export_watchdog()
            return
        if self._last_export_activity_at <= 0:
            return
        idle_sec = int(monotonic() - self._last_export_activity_at)
        self._update_activity_age_label(idle_sec)
        if idle_sec < 90:
            return
        now = monotonic()
        if now - self._last_stall_hint_at < 60:
            return
        self._last_stall_hint_at = now
        hint = self._last_export_activity_msg or "正在处理当前笔记"
        self._append_log(
            f"[提示] 已 {idle_sec}s 无新进度。最后状态：{hint}。"
            "可能在等待网络/限流或大附件下载，可点击“跳过当前”或“停止”。"
        )
        self._lbl_status.setText(f"处理较慢（{idle_sec}s 无进度）：{hint}")
        self._btn_skip_note.setEnabled(True)
        self._event_logger.emit(
            "export.stall_hint", level="WARNING", idle_sec=idle_sec, last_status=hint
        )

    def _stop_export_watchdog(self) -> None:
        self._export_watchdog_timer.stop()
        self._last_export_activity_at = 0.0
        self._last_export_activity_msg = ""
        self._last_stall_hint_at = 0.0
        self._last_runtime_log_msg = ""
        self._btn_skip_note.setEnabled(False)
        self._update_activity_age_label(None)

    def _update_activity_age_label(self, idle_sec: Optional[int]) -> None:
        if idle_sec is None or idle_sec < 0:
            self._lbl_activity_age.setText("最近活动：--")
            return
        if idle_sec < 2:
            self._lbl_activity_age.setText("最近活动：刚刚")
            return
        self._lbl_activity_age.setText(f"最近活动：{idle_sec}s 前")

    def _on_note_done(self, *args) -> None:
        if len(args) == 4:
            guid, title, ok, err = args
        elif len(args) == 3:
            guid = ""
            title, ok, err = args
        else:
            return
        if ok and err == "跳过":
            self._skipped_titles.append(title)
            self._append_log(f"  ↷  {title}  [跳过]")
            return
        icon = "✓" if ok else "✗"
        suffix = f"  [{err}]" if err else ""
        self._append_log(f"  {icon}  {title}{suffix}")
        if not ok:
            error_msg = str(err)
            error_code = classify_export_error(error_msg)
            self._failed_items.append((str(guid), str(title), error_code, error_msg))

    def _on_exp_finished(
        self,
        ok: int,
        fail: int,
        skipped: int,
        summary: Optional[dict[str, object]] = None,
    ) -> None:
        self._stop_export_watchdog()
        self._export_worker = None
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._progress.setFormat("完成")
        self._btn_export.setEnabled(True)
        self._btn_export_failed.setEnabled(True)
        self._btn_skip_note.setEnabled(False)
        self._btn_stop.setEnabled(False)
        output = self._edit_output.text().strip() or _default_output_dir()
        stopped = self._stop_requested
        if stopped:
            self._lbl_status.setText(
                f"已停止：成功 {ok} 条，失败 {fail} 条，跳过 {skipped} 条"
            )
            self._append_log(
                f"\n导出已停止  成功 {ok} 条  失败 {fail} 条  跳过 {skipped} 条"
            )
        else:
            self._lbl_status.setText(
                f"完成：成功 {ok} 条，失败 {fail} 条，跳过 {skipped} 条"
            )
            self._append_log(
                f"\n导出完成 ✓  成功 {ok} 条  失败 {fail} 条  跳过 {skipped} 条"
            )
        self._stop_requested = False
        retries_total = 0
        elapsed_sec = 0.0
        if isinstance(summary, dict):
            retries_total = _to_int(summary.get("retries_total"), default=0)
            elapsed_sec = _to_float(summary.get("elapsed_sec"), default=0.0)
            avg_sec = _to_float(summary.get("avg_sec_per_note"), default=0.0)
            self._append_log(
                f"导出摘要：用时 {elapsed_sec:.1f}s，平均 {avg_sec:.2f}s/条，重试 {retries_total} 次"
            )
            top = summary.get("failure_reasons_top")
            if isinstance(top, list) and top:
                brief = []
                for item in top[:3]:
                    if not isinstance(item, dict):
                        continue
                    reason = str(item.get("reason", "unknown"))
                    count = _to_int(item.get("count"), default=0)
                    brief.append(f"{reason} x{count}")
                if brief:
                    self._append_log("失败原因 Top: " + " | ".join(brief))
            if retries_total > 0 and not stopped:
                self._lbl_status.setText(
                    f"完成：成功 {ok} 条，失败 {fail} 条，跳过 {skipped} 条，重试 {retries_total} 次"
                )
            try:
                summary_path = write_export_summary(
                    summary, os.path.join(output, "export-summary.json")
                )
                self._append_log(f"摘要文件：{summary_path}")
            except Exception as e:
                self._append_log(f"[警告] 写入导出摘要失败：{e}")
        if self._skipped_titles:
            self._append_log("\n跳过清单：")
            for title in self._skipped_titles[:50]:
                self._append_log(f"  - {title}")
            if len(self._skipped_titles) > 50:
                self._append_log(f"  … 其余 {len(self._skipped_titles) - 50} 条")
        self._append_log(f"输出目录：{os.path.abspath(output)}")
        if self._chk_fail_log.isChecked() and self._failed_items:
            path = os.path.join(output, "export-failures.txt")
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    for guid, title, error_code, err in self._failed_items:
                        f.write(f"{guid}\t{title}\t{error_code}\t{err}\n")
                self._append_log(f"失败记录：{path}")
            except Exception as e:
                self._append_log(f"[警告] 写入失败记录失败：{e}")
        self._event_logger.emit(
            "session_done",
            success=ok,
            failed=fail,
            skipped=skipped,
            stopped=stopped,
            retries_total=retries_total,
            elapsed_sec=elapsed_sec,
        )

    def _on_exp_error(self, msg: str) -> None:
        self._stop_export_watchdog()
        self._export_worker = None
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("失败")
        self._btn_export.setEnabled(True)
        self._btn_export_failed.setEnabled(True)
        self._btn_skip_note.setEnabled(False)
        self._btn_stop.setEnabled(False)
        stopped = self._stop_requested
        self._stop_requested = False
        self._append_log(f"[严重错误] {msg}")
        self._lbl_status.setText(f"导出失败：{msg}")
        self._event_logger.emit(
            "session_fail", level="ERROR", error=msg, stopped=stopped
        )

    # ── 工具方法 ────────────────────────────────────────────────────────────────

    def _append_log(self, msg: str) -> None:
        self._log_text.appendPlainText(msg)
        self._log_text.moveCursor(QTextCursor.MoveOperation.End)

    def _set_conn_label(self, text: str, level: str) -> None:
        colors = {"ok": "#40c057", "err": "#fa5252", "info": "#74c0fc"}
        color = colors.get(level, "")
        self._lbl_conn.setText(f'<span style="color:{color}">{text}</span>')

    def _collect_auth(self) -> Optional[AuthConfig]:
        # 优先使用本次会话从 API 获取的 token（即便 UI 还显示密码模式）
        if self._session_token:
            return AuthConfig(mode="token", token=self._session_token)
        if self._radio_token.isChecked():
            token = self._edit_token.text().strip()
            if not token:
                self._append_log("[警告] 请先填写 Developer Token")
                return None
            return AuthConfig(mode="token", token=token)
        u = self._edit_username.text().strip()
        p = self._edit_password.text().strip()
        ck = self._edit_ck.text().strip()
        cs = self._edit_cs.text().strip()
        if not all([u, p, ck, cs]):
            self._append_log(
                "[警告] 请填写完整的认证信息（包括高级选项中的 Key/Secret）"
            )
            return None
        return AuthConfig(
            mode="password", username=u, password=p, consumer_key=ck, consumer_secret=cs
        )

    # ── config.yaml 读写 ───────────────────────────────────────────────────────

    def _load_config(self) -> None:
        if not os.path.exists(_CONFIG_PATH):
            return
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception:
            return
        auth: dict[str, object] = cfg.get("auth", {})
        if auth.get("mode") == "password":
            self._radio_password.setChecked(True)
            self._edit_username.setText(str(auth.get("username") or ""))
            self._edit_password.setText("")
            self._edit_ck.setText(str(auth.get("consumer_key") or ""))
            self._edit_cs.setText(str(auth.get("consumer_secret") or ""))
        else:
            self._radio_token.setChecked(True)
            self._edit_token.setText(str(auth.get("token") or ""))
        output_dir = cfg.get("export", {}).get("output_dir") or ""
        self._edit_output.setText(output_dir or _default_output_dir())

    def _save_config(self) -> None:
        # 如果已有 session token，以 token 模式保存，不存储明文密码
        if self._session_token:
            auth: dict[str, object] = {"mode": "token", "token": self._session_token}
        elif self._radio_token.isChecked():
            auth = {"mode": "token", "token": self._edit_token.text().strip()}
        else:
            # 尚未连接成功时，只保存用户名/consumer_key，不保存明文密码
            auth = {
                "mode": "password",
                "username": self._edit_username.text().strip(),
                "consumer_key": self._edit_ck.text().strip(),
                "consumer_secret": self._edit_cs.text().strip(),
            }
        cfg: dict[str, object] = {
            "auth": auth,
            "export": {
                "output_dir": self._edit_output.text().strip() or _default_output_dir()
            },
        }
        try:
            with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(
                    cfg,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        except Exception as e:
            self._append_log(f"[警告] 配置保存失败：{e}")


def _default_output_dir() -> str:
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    return downloads if os.path.exists(downloads) else "./output"


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default
