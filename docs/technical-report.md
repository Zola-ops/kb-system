# kb-system 技术汇报

> 个人知识图谱构建与管理 Agent — 技术架构、实现细节、设计决策

---

## 一、项目概述

kb-system 是一个**本地知识管理系统**，将用户与 AI 的对话自动转化为可检索、有关联、能演化的知识网络。

核心链路：`对话 → LLM 分类 → 结构化笔记 → 语义向量索引 → 知识图谱 → Web/CLI/MCP 多接口`

## 二、技术架构

```
┌────────────── 摄入层 ──────────────┐
│  对话原文 → 外部 LLM 分类+生成      │
│  OpenAI 兼容接口，可替换任意模型     │
├────────────── 存储层 ──────────────┤
│  Markdown 文件 (人类可读)            │
│  + SQLite 关系索引 (notes/entities/relations) │
│  + 384维语义向量 (float32 BLOB)     │
├────────────── 检索层 ──────────────┤
│  关键词 LIKE + FTS5 全文搜索        │
│  + 语义余弦相似度 (全量计算, 毫秒级) │
│  + 知识图谱三元组关系查询            │
├────────────── 呈现层 ──────────────┤
│  FastAPI REST · MCP Server          │
│  · CLI (bash) · Python SDK          │
│  · Web UI (单页, 无框架依赖)        │
└────────────────────────────────────┘
```

## 三、核心技术实现

### 3.1 语义向量引擎

| 项目 | 选择 |
|------|------|
| 模型 | `paraphrase-multilingual-MiniLM-L12-v2` |
| 参数量 | 118MB |
| 向量维度 | 384 |
| 推理速度 | 86 篇 2.7 秒 (Mac M2 CPU) |
| 中文支持 | ✅ 多语言模型, 中文语义匹配准确 |

```python
# 模块级单例缓存, 首次加载 ~2s, 后续毫秒级
_model_cache: dict[str, SentenceTransformer] = {}

# 余弦相似度归因于向量已归一化, 等价于点积
similarity = float(np.dot(vec_a, vec_b))
```

### 3.2 知识图谱构建

三种自动关联策略:

| 策略 | 置信度 | 说明 |
|------|:---:|------|
| wikilink 解析 | 0.9 | ` [[笔记名]] ` 双向链接直接解析为有向边 |
| 共享标签 | 0.7 | 两篇笔记共享 `#标签` → 无向边 |
| 语义近邻 | 0.55+ | 向量余弦相似度 > 阈值 → 无向边 |

```sql
-- relations 表结构
CREATE TABLE relations (
    source_note_id INTEGER,
    target_note_id INTEGER,
    relation_type TEXT,     -- wikilink | shared_tag | semantic
    confidence REAL
);
```

### 3.3 摄入管线

```
对话原文 → LLM 两步处理:
  第一步 (T=0.1): JSON 结构化分类
    { worth_saving: bool, category: str, title: str, summary: str, tags: [] }
  第二步 (T=0.3): 生成结构化 Markdown 笔记
    模板: 背景 → 做了什么 → 踩坑 → 收获 → 相关链接
```

**设计决策: 使用外部独立 LLM 而非 Agent 自我总结。**

理由: 同一模型评判自己的输出存在确认偏见——会选择性忽略错误、遗漏关键上下文。外部模型逐字分析对话原文, 不带立场, 信息更完整。

### 3.4 多接口设计

| 接口 | 协议 | 适用 |
|------|------|------|
| MCP Server | JSON-RPC stdio | Claude/Cursor/Hermes 等任意 Agent |
| REST API | HTTP/JSON | 任何 HTTP 客户端 |
| CLI | Bash | 终端直接操作 |
| Python SDK | 直接 import | 代码集成 |

MCP Server 提供 4 个工具: `kb_search` / `kb_ingest` / `kb_graph` / `kb_stats`

## 四、关键设计决策

### 4.1 不绑定 Obsidian

读取任意 Markdown 文件夹。wikilink `[[link]]` 和 frontmatter 是通用语法。通过 `NOTES_ROOT` 环境变量配置路径。

### 4.2 不绑定特定 Agent

核心管线是标准 Python。Hermes 的 `kb-ingest` skill 只是一个便捷 wrapper。任何 Agent 通过 MCP 即可接入。

### 4.3 本地优先

所有数据本地存储 (SQLite + MD 文件), 嵌入模型本地推理。无需联网即可搜索。LLM API 仅在摄入时调用。

## 五、性能数据

| 指标 | 数值 |
|------|------|
| 索引笔记数 | 86 篇 (可扩展) |
| 向量生成耗时 | 2.7s / 86 篇 |
| 语义搜索耗时 | < 50ms |
| 图谱边数 | 600 条自动关联 |
| 嵌入模型大小 | 118MB |
| 首次模型加载 | ~2s |
| 内存占用 | < 500MB |

## 六、技术栈

| 层 | 技术 |
|------|------|
| 语言 | Python 3.11 |
| Web 框架 | FastAPI + Uvicorn |
| 数据库 | SQLite (WAL 模式) |
| 向量引擎 | sentence-transformers |
| 前端 | 单页 HTML + D3.js + Tailwind CSS CDN |
| MCP 协议 | JSON-RPC 2.0 over stdio |
| 测试 | pytest (17 个测试) |
| LLM | OpenAI 兼容接口 (DeepSeek/OpenAI/OneAPI) |

## 七、项目规模

| 指标 | 数值 |
|------|------|
| Python 模块 | 8 个 |
| 测试用例 | 17 个 |
| 前端页面 | 1 个 (单页, 5 Tab) |
| 代码行数 | ~1,800 行 |
| 依赖包 | 6 个核心 + 测试 |
