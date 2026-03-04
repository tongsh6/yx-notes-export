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

## 项目结构

- `src/` 核心实现
- `src/gui/` 图形界面
- `tests/` 自动化测试
- `context/` AIEF 上下文与经验沉淀
- `scripts/` 回归与诊断脚本

## 分支工作流

- 本项目采用 GitFlow：`main`（发布）、`develop`（日常集成）
- 详细约定见 `context/tech/GITFLOW_WORKFLOW.md`

## Language Policy

- 中文为主，英文为辅
- 代码、命令、标识符保持英文

## License

MIT
