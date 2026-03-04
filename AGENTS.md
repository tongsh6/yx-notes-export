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
- run (CLI): python3 main.py [--notebook NAME] [--note GUID] [--all] --output ./output
- run (GUI): python3 gui_main.py

Context Entry:
- context/INDEX.md

Knowledge Base:

| Directory | Purpose | When to Load |
|-----------|---------|-------------|
| context/business/ | Business knowledge | Understanding requirements, domain models |
| context/tech/ | Technical docs | Architecture, API, conventions |
| context/experience/ | Experience library | Avoid repeating mistakes |
| workflow/ | Workflows | Complex task phase guides (optional) |
| docs/standards/ | Standards | Skill/Command/Agent specs (L1, optional) |
| docs/standards/patterns/ | Patterns | Phase routing, experience mgmt, context loading (L2, optional) |
