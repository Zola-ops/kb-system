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

| | kb-ingest (轻量) | kb-system (完整) |
|---|---|---|
| 怎么做 | 一个 skill，说"记录"就行 | 启动服务，Web + CLI + Agent |
| 摄入方式 | Hermes 自己总结 | 外部 LLM 总结 |
| 配置 | **零**，开箱即用 | 需配 LLM API Key |
| 语义搜索 | ❌ | ✅ |
| 知识图谱 | ❌ | ✅ |
| Web 界面 | ❌ | ✅ |
| 定时自动 | ❌ | ✅ Cron |
| 跨平台 | ❌ | ✅ MCP |

> **随手记录 → kb-ingest。建知识大脑 → kb-system。**

### 🔍 为什么 kb-system 用外部模型总结？

kb-ingest 由 Hermes 自己总结对话——简单，零配置，够用。

kb-system 作为完整知识管理系统，额外配置了外部 LLM 来完成摄入。原因：**同一模型总结自己的对话 = 瞎子摸象**——会选择性忽略错误、遗漏关键上下文。外部模型只看对话原文，不带立场，更客观完整。

这就像**让作者自己写书评 vs 让独立评论家写书评**——前者方便，后者可信。两种都合理，场景不同。

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

| 方式 | 适用场景 |
|------|---------|
| **MCP Server** | Claude Desktop / Cursor / Continue / Hermes 等，一行 JSON 配置 |
| **REST API** | 任何能发 HTTP 的工具 |
| **CLI** `scripts/kb` | 终端直接操作，自动检测 Python 环境 |
| **Python SDK** | `from src.pipeline import KnowledgePipeline` |

### MCP 配置

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

配置后 Agent 获得 `kb_search` / `kb_stats` / `kb_graph` 三个工具。

### Hermes 用户

额外提供 `knowledge-agent` skill：对话中直接问"我之前的结论是什么"，Agent 自动检索知识库回答。支持 cron 定时自动摄入。

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
