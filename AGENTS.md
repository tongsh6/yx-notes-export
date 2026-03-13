# 印象笔记导出工具 AI Guide

This is the project-level entry for AI-assisted engineering.

Language:
- Use Chinese for communication by default
- Keep code/commands/identifiers in English

Project:
- One-liner: 通过印象笔记官方 API 连接服务端，支持配置认证后按层级结构批量导出笔记为 Markdown 的 Python 工具
- Core value: 完整保留笔记内容、标签、附件和元数据，生成可读性强的 Markdown 文档

Quick Commands:
- build: N/A
- test: python3 -m pytest
- run (CLI): python3 main.py [--notebook NAME] [--note GUID] [--all] [--incremental] --output ./output
- run (GUI): python3 gui_main.py
- release: python scripts/release_version.py --bump patch --push  # 需 gh 以创建 GitHub Release

Context Entry:
- context/INDEX.md
- context/README.md  # AIEF 说明（上下文目录用途与结构）

Knowledge Base（文档体系按 AIEF 组织，详见 context/README.md）：

| Directory | Purpose | When to Load |
|-----------|---------|-------------|
| context/business/ | Business knowledge | Understanding requirements, domain models；入口 [business/README.md](context/business/README.md) |
| context/tech/ | Technical docs | Architecture, API, conventions；入口 [tech/README.md](context/tech/README.md) |
| context/experience/ | Experience library | Avoid repeating mistakes；入口 [experience/INDEX.md](context/experience/INDEX.md) |
