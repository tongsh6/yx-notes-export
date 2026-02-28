# QThread 生命周期崩溃：根因与修复

## 背景
GUI 程序（PySide6 + QThread）在点击"连接"后，过一段时间进程直接退出，无任何错误弹窗。
终端输出：`QThread: Destroyed while thread '' is still running`

## 现象
- 点击"连接"后约数秒，进程无声崩溃
- Windows 下有时出现 access violation / GIL 内部 assertion 失败
- 偶发，网络越慢越容易触发

## 根因

### 根因一：Python 引用归零触发 Qt 析构 → TerminateThread → GIL 损坏
```python
# 危险代码（原 main_window.py）
def _on_conn_ok(self, ...):
    self._connect_worker = None   # ← 清掉最后一个引用
    # CPython GC 立即调用 QThread::~QThread()
    # Qt 发现线程仍在运行 → 内部 terminate()
    # → Windows TerminateThread()
    # → 线程正处于 socket I/O（CPython 已释放 GIL）
    # → GIL 计数损坏 → 进程崩溃
```
触发点共三处：`_on_conn_ok`、`_on_conn_fail`、`_on_connect_timeout`。

### 根因二：`ExportWorker.finished` 遮蔽 `QThread.finished`
```python
# 危险代码（原 worker.py）
class ExportWorker(QThread):
    finished = Signal(int, int, int)  # ← 遮蔽了 QThread.finished()（无参内置信号）
    # 导致无法连接 QThread.finished 到生命周期清理槽
```

### 根因三：`isRunning()` 竞态
Qt 先发出 `finished` 信号，再将 `d->running` 置 `false`，两者之间存在微小时间窗口。
若在槽函数里用 `isRunning()` 判断是否可以释放，会出现误判。

## 结论（已落地）

### worker.py
```python
# 改名，避免遮蔽 QThread.finished()
class ExportWorker(QThread):
    export_done = Signal(int, int, int)   # 原来是 finished
```

### main_window.py
```python
class MainWindow(QMainWindow):
    _defunct_workers: List[object] = []  # 持有 QThread 引用直到线程真正退出

    def _on_connect(self):
        worker = ConnectWorker(cfg)
        self._connect_worker = worker
        self._defunct_workers.append(worker)          # 额外持有引用
        worker.finished.connect(self._reap_defunct_workers)  # QThread.finished（无参）
        worker.start()

    def _reap_defunct_workers(self) -> None:
        done = self.sender()                          # sender() 精确识别完成的 worker
        if done is not None and done in self._defunct_workers:
            self._defunct_workers.remove(done)        # 安全释放
        # 不用 isRunning()，绕过竞态
```

## 影响
- 永远不要在 worker 的信号槽里将 `self._xxx_worker = None`（清掉最后引用）
- `QThread` 子类中的自定义信号命名要避开 `finished`、`started`、`terminated` 等内置名
- 需要延迟释放 QThread 时，用"持有列表 + sender() reap"模式，不用 `isRunning()` 判断

## 衍生问题：socket 超时不能过短
原本 `_SOCKET_TIMEOUT_SEC = 45`，修复过程中被误改为 `10`。
`socket.setdefaulttimeout` 是全局设置，10s 超时会截断大附件（图片/PDF）的下载数据读取，导致附件损坏。
结论：保持 45s；如需更激进的超时，应仅对"连接建立阶段"单独设置。
