# Skills

本目录包含**零配置、纯文本**的通用 Skill 文件。不绑定任何特定 Agent 工具——任何能读写的 Agent 均可执行。

## 使用方法

1. 复制 `.md` 文件到你的 Agent 技能目录
2. Agent 对话中说"记录这段对话"即触发

## Skill 列表

| Skill | 说明 | 依赖 |
|-------|------|------|
| `dialogue-ingest.md` | 对话沉淀为结构化 Markdown 笔记 | 无 |

## 设计原则

- **零配置**：不开外部 API，不装依赖
- **纯文本**：输出标准 Markdown，任何编辑器可读
- **通用**：不绑定特定文件夹结构（Obsidian 可选）

## 与 kb-system 的关系

这些 Skill 提供**轻量摄入**。需要语义搜索、知识图谱、Web UI，请使用 [kb-system](../)。
