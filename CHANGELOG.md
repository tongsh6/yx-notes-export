# 更新日志 (Changelog)

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.2] - 2026-03-03

## [0.2.1] - 2026-03-03

## [0.2.0] - 2026-03-03

### Added
- **增量导出**：仅导出上次导出后新增或已修改的笔记
  - CLI：`--incremental`（依赖本地 `.export-index.json`，隐含断点续传）
  - GUI：选项「仅增量（只导出新增/已修改）」勾选后过滤笔记列表再导出
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
