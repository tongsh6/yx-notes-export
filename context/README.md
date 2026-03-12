# AIEF 上下文 (Context for AI-Assisted Engineering)

本目录为 **AI 辅助工程** 提供的结构化上下文与知识库，便于 AI 与人类协作时快速理解业务、技术约定与历史经验。

## 什么是 AIEF

AIEF（AI-Assisted Engineering Context）指本项目采用的「上下文目录 + 索引」方式：将业务、技术、经验分目录存放，通过入口索引与 AGENTS.md 的 Knowledge Base 表，在需要时按主题加载，避免一次性灌入无关信息。

## 目录结构

| 目录 | 用途 | 典型内容 |
|------|------|----------|
| **business/** | 业务与领域知识 | 目标、用户场景、数据模型、输出结构、认证方式 |
| **tech/** | 技术文档与约定 | 架构、API、依赖、流程、检查清单、最佳实践 |
| **experience/** | 经验与复盘 | 问题现象、解决方案、可复用结论与教训 |

## 入口与阅读顺序

- **总入口**：[context/INDEX.md](INDEX.md) — 目录导航与按 AIEF 分层的「建议优先阅读」列表。
- **业务**：[business/README.md](business/README.md) 为索引，核心为 [business/DOMAIN.md](business/DOMAIN.md)。
- **技术**：[tech/README.md](tech/README.md) 为索引，优先 [tech/ARCHITECTURE.md](tech/ARCHITECTURE.md)、[tech/GITFLOW_WORKFLOW.md](tech/GITFLOW_WORKFLOW.md)，再按任务选读。
- **经验**：[experience/INDEX.md](experience/INDEX.md) 列出所有经验条目与记录模板，按日期与主题查阅。

## 项目内文档体系

- **根目录**： [README.md](../README.md)（使用说明）、[CHANGELOG.md](../CHANGELOG.md)（版本变更）、[AGENTS.md](../AGENTS.md)（AI 协作约定与 Context Entry）。
- **context/**：本目录，即 AIEF 上下文；不重复 README 的快速开始，侧重业务、技术与经验的分类沉淀。
- **scripts/**： [scripts/README.md](../scripts/README.md) 说明各脚本用途。

## 与 AGENTS.md 的关系

项目根目录的 [AGENTS.md](../AGENTS.md) 中「Context Entry」与「Knowledge Base」表引用本目录，约定 AI 在何时加载哪类上下文。本 README 与 [INDEX.md](INDEX.md) 共同构成 AIEF 相关文档的说明。

## 维护建议

- 新增业务/技术约定：放入对应子目录，并在 INDEX.md 的「建议优先阅读」中按需添加。
- 新增经验：在 experience/ 下新建 `YYYY-MM-DD-主题.md`，并在 [experience/INDEX.md](experience/INDEX.md) 登记。
