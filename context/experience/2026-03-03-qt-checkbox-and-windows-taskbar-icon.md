# Qt 勾选框对勾与 Windows 任务栏图标

## 背景
GUI 深色主题下 QCheckBox 选中态不明显；自定义 indicator 样式后无对勾。另，Windows 上窗口使用 setWindowIcon 后任务栏仍显示 Python 图标。

## 现象
- QCheckBox::indicator 在 QSS 中只设 border/background-color 时，Qt 不会自动绘制对勾。
- 使用 `image: url(file:///path/to/check.svg)` 在 Windows 上有时不加载。
- 仅 setWindowIcon 不足以让任务栏显示应用图标，仍显示 pythonw.exe 图标。

## 结论
- **对勾图标**：在 QSS 中用 `background-image: url(绝对路径)`（不用 `image:`），路径用正斜杠、不含 `file://`；资源放于与 theme 同目录，用 `Path(__file__).resolve().parent` 解析路径注入 QSS。
- **任务栏图标**：在创建 QApplication 与任何窗口**之前**，Windows 下调用 `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("app.id.string")`，再 setWindowIcon；否则任务栏会按进程归属到 Python。
- QCheckBox 无 setWordWrap；长文案可改为竖排布局或放宽容器宽度避免截断。

## 影响
- 主题与图标资源集中在 src/gui/，发布脚本无需额外打包资源路径。
- 任务栏需在 main 入口最早处设置 AppUserModelID，仅 Windows 分支执行。
