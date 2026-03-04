# 更新日志 (Changelog)

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.5] - 2026-03-04

### Improved
- 文档一致性修订：统一 Python 命令风格（`python3` / Windows 使用 `py -3`）
- 架构文档补齐发布自动化、summary/失败记录契约、contract tests 覆盖说明
- GitFlow 文档补充自动化发布触发与校验门禁
- README 与 scripts 文档补全测试触发条件和平台命令示例

## [0.2.4] - 2026-03-04

### Added
- 发布自动化：新增 `release.yml`，支持 tag/手动触发发布，并在发布前校验 `VERSION` 与 `CHANGELOG` 一致性
- 可观测性增强：默认写入 `export-summary.json`，并新增 summary 趋势聚合脚本 `scripts/export_summary_trend.py`
- 错误分类标准化：新增稳定 `error_code` 映射并接入 CLI/GUI 导出失败路径
- 契约测试：新增 summary schema、失败记录格式、CLI `--summary-json` 行为测试

### Improved
- real API 测试工作流支持 `workflow_dispatch` 子集选择：`all|cli|gui`
- 失败记录输出统一为四列：`guid\ttitle\terror_code\terror_message`

## [0.2.3] - 2026-03-04

### Added
- CI 工作流：新增 GitHub Actions 自动测试（PR/push 跑离线测试，手动/定时触发 real API 测试）
- 新增导出摘要能力：CLI/GUI 输出关键指标（耗时、平均每条耗时、重试次数、失败原因 Top）
- CLI 新增 `--summary-json` 参数，可将导出摘要写入 JSON 文件
- 新增 `scripts/gui_regression.sh`，支持 macOS/Linux 一键回归

### Improved
- 测试分层：引入 `real_api` marker，离线测试与真实 API 测试执行路径更清晰
- 文档跨平台化：README 与 scripts/README 补充 Windows/macOS/Linux 对照命令

## [0.2.2] - 2026-03-03

## [0.2.1] - 2026-03-03

## [0.2.0] - 2026-03-03

### Added
- **断点续传能力**：仅导出上次导出后新增或已修改的笔记
  - CLI：`--resume`（依赖本地 `.export-index.json`）
  - GUI：默认启用“断点续传（跳过已导出且未更新的笔记）”
- 应用图标：主窗口与 Windows 任务栏使用自定义图标（`src/gui/app_icon.svg`），并设置 AppUserModelID 以区分 Python 进程

### Improved
- GUI 勾选可见度：深色/浅色主题下 QCheckBox 显式样式，选中态增加白色对勾图标
- GUI 布局：左侧操作区加宽、右侧日志区收窄（splitter 初始 520/540）；导出选项三个勾选改为竖排、左侧内容区最大宽度放宽，避免文案截断
- 右侧日志面板设置最小宽度 380px，避免拖拽过窄

## [0.1.0] - 2026-02-28

### Added
- 首次开源发布，提供 GUI 与 CLI 两种导出入口
- 支持全量/指定笔记本/指定 GUID 导出
- 支持断点续传与失败条目重导
- 新增结构化运行日志与卡顿诊断脚本

### Improved
- 导出长任务交互优化：状态提示、watchdog、停止与跳过当前笔记
- GUI 布局打磨：按钮对齐、文案可读性与中文显示稳定性提升
- 项目文档调整为“中文为主，英文为辅”
