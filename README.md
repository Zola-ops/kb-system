# 📚 kb-system — 个人知识库管理系统

> AI 驱动的本地知识库：对话自动沉淀 → 语义检索 → 知识图谱 → Web 界面

## 能力一览

| 功能 | 说明 |
|------|------|
| 📝 **自动摄入** | 粘贴对话 → LLM 判断价值 → 生成结构化笔记 → 写入 Obsidian |
| 🔍 **语义检索** | 自然语言搜索，不用精确关键词也能找到 |
| 🕸️ **知识图谱** | 自动发现笔记间关联（wikilink + 语义 + 标签），D3 力导向图 |
| 🖥️ **Web UI** | 本地网页界面，搜索/浏览/图谱/摄入/统计 |

## 快速开始

### 1. 安装

```bash
git clone https://github.com/yourname/kb-system.git
cd kb-system
pip install -e ".[dev]"
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM API 地址和 Key
```

### 3. 启动

```bash
python -m uvicorn src.api:app --port 8765
# 浏览器打开 http://localhost:8765
```

### 4. 索引你的 Obsidian Vault

首次使用需要索引笔记：

```bash
python -c "from src.pipeline import KnowledgePipeline; p = KnowledgePipeline(); p.index_embeddings()"
```

## CLI 工具

```bash
scripts/kb search "关键词"         # 关键词搜索
scripts/kb search -s "语义描述"    # 语义搜索
scripts/kb graph                   # 图谱统计
scripts/kb ingest --write "内容"   # 摄入对话并写入 Obsidian
```

## 架构

```
摄入层: 对话 → LLM (OpenAI 兼容) → 分类 → 结构化笔记 → Obsidian MD
存储层: Obsidian Vault + SQLite + 向量嵌入 (384维)
检索层: 关键词 LIKE + 语义余弦相似度 + 知识图谱三元组
呈现层: FastAPI + 单页 HTML (简约白色主题)
```

## 依赖

- Python 3.11+
- LLM API (任何 OpenAI 兼容接口，如 DeepSeek/OpenAI/OneAPI)
- sentence-transformers (首次启动自动下载多语言嵌入模型 ~118MB)
- Obsidian (可选，摄入功能需要 Vault 路径)

## 测试

```bash
pytest tests/ -q
```

## License

MIT
