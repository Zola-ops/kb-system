# 📚 kb-system — 个人知识图谱构建与管理 Agent

> 对话自动沉淀 · 语义检索 · 知识图谱 · 本地 Web 界面 · MCP 通用协议

[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-17%20passed-brightgreen)](tests/)

---

## 是什么

把你的对话和笔记变成**可搜索、可关联、可演化**的知识网络。

你每天和 AI 对话产生的结论、踩坑、分析、决策——自动沉淀为结构化笔记，用自然语言就能检索，笔记之间自动发现关联形成知识图谱。

### 🎯 两种用法

| | [dialogue-ingest](skills/dialogue-ingest.md) (轻量 Skill) | kb-system (完整管线) |
|---|---|---|
| 本质 | 一份 Markdown 文档，复制即用 | 本地服务 + Python 管线 |
| 摄入笔记 | ✅ Agent 自己总结 | ✅ 外部 LLM 总结 |
| 配置 | **零** | 需配 LLM API Key + pip install |
| 适用 Agent | **任意**（能读写文件即可） | MCP 兼容（Claude/Codex/Cursor/Hermes…） |
| 适用笔记工具 | **任意** Markdown 文件夹 | **任意** Markdown 文件夹 |
| 语义搜索 | ❌ | ✅ 384维向量索引 |
| 知识图谱 | ❌ | ✅ 自动关联 + D3 可视化 |
| Web 界面 | ❌ | ✅ localhost:8765 |
| 定时自动 | ❌ | ✅ Cron 每 6 小时 |
| 适合 | 随手记录，我用故我记 | 建知识大脑，搜索+发现 |

> **只想要一个"记录对话"的 Skill？复制 `skills/dialogue-ingest.md` 到你的 Agent 技能目录，说完"记录"就完成。零依赖。**
>
> **想要搜索引擎 + 知识图谱 + 可视化？用 kb-system。**

### 适用场景速查

| 你是谁 | 推荐 |
|--------|------|
| 用 Hermes，只需要记录对话 | 复制 `skills/dialogue-ingest.md` 到 `~/.hermes/skills/`，说"记录"即触发 |
| 用 Codex / Claude Code / Cursor | 复制 `skills/dialogue-ingest.md` 到对应技能目录 |
| 用任意 Agent，需要搜索+图谱 | kb-system + MCP 一行 JSON |
| 不用 Obsidian | 设 `NOTES_ROOT`，两个方案都支持 |

> dialogue-ingest Skill 是一份纯 Markdown 文档，不绑定任何平台。复制到你的 Agent 技能目录即可使用。

### 🔍 为什么 kb-system 用外部模型总结？

dialogue-ingest Skill 由 Agent 自己总结对话——简单，零配置，够用。

kb-system 额外配置了外部 LLM 来完成摄入。原因：**同一模型总结自己的对话 = 瞎子摸象**——会选择性忽略错误、遗漏关键上下文。外部模型只看对话原文，不带立场，更客观完整。

**作者自评 vs 独立书评——前者方便，后者可信。两种都合理，场景不同。**

## 快速开始

```bash
# 1. 安装
git clone https://github.com/Zola-ops/kb-system.git && cd kb-system
pip install -e ".[dev]"

# 2. 配置 LLM
cp .env.example .env
# 编辑 .env，填入 OpenAI 兼容的 API 地址和 Key

# 3. 启动
uvicorn src.api:app --port 8765
# 浏览器打开 http://localhost:8765
```

首次启动自动扫描笔记文件夹、生成语义索引、构建知识图谱。**零手动配置。**

## 做什么

| 能力 | 说明 |
|------|------|
| 📝 **自动摄入** | 对话 → LLM 判断价值 → 生成结构化笔记 → 写入文件夹 |
| 🔍 **语义检索** | "我之前的 GSB 分析结论是什么"——自然语言搜，不用关键词 |
| 🕸️ **知识图谱** | 自动发现 wikilink / 标签 / 语义关联，D3.js 力导向图可视化 |
| 🖥️ **Web 界面** | 搜索、浏览、图谱、摄入、统计——简约白色主题 |
| ⏰ **定时任务** | Cron 每 6 小时扫描最近对话，自动沉淀有价值内容 |

## 架构

```
┌─────────────────────────────────────────┐
│                摄入层                     │
│  对话 → LLM 分类 → 结构化笔记生成         │
├─────────────────────────────────────────┤
│                存储层                     │
│  Markdown 文件 + SQLite 索引 + 384维向量   │
├─────────────────────────────────────────┤
│                检索层                     │
│  关键词 LIKE + 语义余弦 + 知识图谱三元组    │
├─────────────────────────────────────────┤
│                接口层                     │
│  Web UI · CLI · MCP Server · Python SDK  │
└─────────────────────────────────────────┘
```

## 对接 Agent 工具

不绑定任何特定平台。四种方式接入：

| 方式 | 适用场景 | 支持的 Agent |
|------|---------|------------|
| **MCP Server** ← 推荐 | 通用标准协议 | Claude Desktop, Codex, Cursor, Continue, Copilot, Hermes… |
| **REST API** | 任何能发 HTTP 的工具 | 所有 |
| **CLI** `scripts/kb` | 终端直接操作 | 所有 |
| **Python SDK** | 代码调用 | 所有 |

### MCP 配置（一行 JSON，通用接入）

```json
{
  "mcpServers": {
    "kb-system": {
      "command": "python",
      "args": ["scripts/kb_mcp.py"],
      "cwd": "/path/to/kb-system"
    }
  }
}
```

配置后 Agent 获得 4 个工具：`kb_search` / `kb_ingest` / `kb_graph` / `kb_stats`

### Hermes 用户

额外提供 `kb-ingest` skill（零配置，Hermes 自己总结对话写入笔记）和 `knowledge-agent` skill（对话式检索 + cron 自动摄入）。其他 Agent 工具通过 MCP 获得同等能力。

## 不使用 Obsidian？

设置环境变量指向任意 Markdown 文件夹：

```bash
NOTES_ROOT=~/my-notes uvicorn src.api:app --port 8765
```

wikilink `[[链接]]` 和 frontmatter 是通用 Markdown 语法，不限于 Obsidian。

## 与 Obsidian 的关系

**不依赖 Obsidian，只是恰好兼容。**

启动时自动扫描笔记文件夹，提取：
- 📂 `.md` 文件 → 🏷️ frontmatter 元数据 → 🔗 `[[wikilink]]` 双向链接 → #️⃣ 标签

| Obsidian 用户 | 其他 Markdown 用户 |
|---|---|
| 默认路径 `~/Documents/Obsidian Vault`，开箱即用 | 设 `NOTES_ROOT=/your/folder`，同样支持 |

用 Obsidian 编辑笔记，用 kb-system 搜索、发现关联、看知识图谱——互补，互不干扰。

## CLI

```bash
scripts/kb search "关键词"           # 关键词搜索
scripts/kb search -s "语义描述"      # 语义搜索
scripts/kb graph                     # 图谱概览
scripts/kb graph "笔记标题"          # 查看某篇笔记的关联
scripts/kb ingest "对话内容"         # 干跑预览
scripts/kb ingest --write "内容"     # 写入文件夹
scripts/kb stats                     # 知识库统计
scripts/kb index                     # 重建向量索引
```

## 依赖

- Python 3.11+
- LLM API（OpenAI 兼容接口：DeepSeek / OpenAI / OneAPI 等）
- sentence-transformers（首次启动自动下载 `paraphrase-multilingual-MiniLM-L12-v2`，~118MB）

## 开发

```bash
# 测试
pytest tests/ -q        # 17 passed

# 项目结构
src/
├── pipeline.py         # 端到端管线 + 图谱构建
├── ingest.py           # LLM 分类器 + 笔记生成
├── database.py         # SQLite 索引 + 向量存储
├── embeddings.py       # 多语言语义嵌入引擎
├── vault_reader.py     # Markdown 文件夹解析
├── vault_writer.py     # 笔记写入
├── config.py           # 配置（自动加载 .env）
└── api.py              # FastAPI Web 接口
static/index.html       # Web UI（单页，无框架）
scripts/
├── kb                  # CLI 工具
└── kb_mcp.py           # MCP Server
tests/                  # 17 个测试
```

## License

MIT
