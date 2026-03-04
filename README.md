# 印象笔记导出工具 (YX Notes Export)

基于印象笔记官方 API 的 Python 导出工具，支持将笔记批量导出为结构化 Markdown。

## 功能特性

- 支持全量导出、指定笔记本导出、指定 GUID 单条导出
- 尽量保留原始内容、标签、元数据与附件资源
- 同时提供 GUI（`PySide6`）与 CLI 两种使用方式
- 内置重试、超时处理与结构化运行日志
- 支持断点续传与失败条目重导

## 运行环境

- Python 3.11+
- 安装依赖：

```bash
python -m pip install -r requirements.txt
```

## 快速开始

### GUI 模式

```bash
python gui_main.py
```

### CLI 模式

```bash
python main.py --all --output ./output
python main.py --notebook "Notebook Name" --output ./output
python main.py --note "NOTE_GUID" --output ./output
python main.py --all --output ./output --summary-json ./output/export-summary.json
```

默认会在输出目录生成摘要文件：`export-summary.json`。

失败记录文件 `export-failures.txt` 包含四列：`guid\ttitle\terror_code\terror_message`。
摘要中的失败 Top 同时按 `reason` 与 `error_code` 聚合。

## 配置

复制配置模板并填写认证信息：

```bash
# Windows (CMD)
copy config.example.yaml config.yaml

# macOS/Linux
cp config.example.yaml config.yaml
```

> `config.yaml` 可能包含私密 token，请勿提交到 Git 仓库。

## 测试

```bash
# 离线测试（默认，不依赖 YX_TOKEN）
python3 -m pytest -m "not real_api" -q

# 真实 API 测试（需要 YX_TOKEN）
YX_TOKEN="your-token" python3 -m pytest -m real_api -q
```

CI 工作流：`.github/workflows/tests.yml`

- PR / push（main, develop）自动运行离线测试
- `workflow_dispatch` / 每周定时任务运行 real API 测试
- `workflow_dispatch` 支持 `real_api_target=all|cli|gui`，可按子集触发 real API 回归

## 项目结构

- `src/` 核心实现
- `src/gui/` 图形界面
- `tests/` 自动化测试
- `context/` AIEF 上下文与经验沉淀
- `scripts/` 回归与诊断脚本

## 分支工作流

- 本项目采用 GitFlow：`main`（发布）、`develop`（日常集成）
- 详细约定见 `context/tech/GITFLOW_WORKFLOW.md`

## 发布流程

- 发布工作流：`.github/workflows/release.yml`
- 支持两种触发：
  - 推送 tag（格式 `vX.Y.Z`）
  - `workflow_dispatch` 手动触发并指定 tag
- 发布前会自动校验：
  - `VERSION` 与 tag 版本一致
  - `CHANGELOG.md` 包含对应版本段落（`## [X.Y.Z] - YYYY-MM-DD`）
- 校验通过后自动创建/更新 GitHub Release（内容来自 `CHANGELOG.md` 对应版本段落）

## Language Policy

- 中文为主，英文为辅
- 代码、命令、标识符保持英文

## License

MIT
