"""kb-system Web API — FastAPI 后端"""
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .pipeline import KnowledgePipeline
from .config import NOTES_ROOT

pipeline = KnowledgePipeline()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动索引已有笔记"""
    pipeline.db.init()
    notes = pipeline.reader.discover()
    pipeline.db.sync_from_vault(notes)
    n = len(notes)
    if n > 0 and pipeline.db.embedding_count() == 0:
        print(f"发现 {n} 篇已有笔记，正在生成索引…")
        r = pipeline.index_embeddings()
        pipeline.build_graph()
        print(f"✅ 已索引 {r['total']} 篇，{r['dim']}维向量")
    yield


app = FastAPI(title="知识库", version="0.2.0", lifespan=lifespan)
_pipeline = pipeline  # 别名


@app.get("/api/search")
def api_search(q: str = "", mode: str = "semantic", limit: int = 10):
    return _pipeline.search(q, limit, mode)


@app.get("/api/stats")
def api_stats():
    return _pipeline.search("", limit=0, mode="keyword")


@app.get("/api/graph")
def api_graph(title: str = ""):
    if title:
        return _pipeline.query_graph(title)
    return _pipeline.graph_stats()


@app.post("/api/ingest")
async def api_ingest(data: dict):
    content = data.get("content", "")
    write = data.get("write", False)
    p = KnowledgePipeline(dry_run=not write)
    return p.ingest(content)


@app.get("/api/notes")
def api_notes():
    notes = _pipeline.reader.discover()
    return [
        {"title": n.title, "category": n.category, "tags": n.tags,
         "wikilinks": n.wikilinks[:10], "path": str(n.path)}
        for n in notes
    ]


@app.get("/api/note/{title:path}")
def api_note(title: str):
    """获取笔记全文"""
    _pipeline.db.init()
    row = _pipeline.db.conn.execute(
        "SELECT title, category, content, filepath, wikilinks_json, tags_json FROM notes WHERE title=?",
        (title,)
    ).fetchone()
    if not row:
        return {"error": "not found"}
    import json
    return {
        "title": row["title"],
        "category": row["category"],
        "content": row["content"],
        "path": row["filepath"],
        "wikilinks": json.loads(row["wikilinks_json"]),
        "tags": json.loads(row["tags_json"]),
    }


@app.post("/api/index")
def api_index():
    """重建索引（新增笔记后调用）"""
    notes = _pipeline.reader.discover()
    _pipeline.db.init()
    _pipeline.db.sync_from_vault(notes)
    r = _pipeline.index_embeddings()
    g = _pipeline.build_graph()
    return {**r, "graph_edges": g["total_edges"]}


# 静态文件
STATIC = Path(__file__).parent.parent / "static"
STATIC.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC / "index.html"))
