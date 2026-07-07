#!/usr/bin/env python3
"""kb-system MCP Server — 任何 MCP 兼容 Agent 均可对接

支持: Claude Desktop, Cursor, Continue, Copilot, Hermes 等

配置方式 (以 Claude Desktop 为例):
  {
    "mcpServers": {
      "kb-system": {
        "command": "python",
        "args": ["scripts/kb_mcp.py"],
        "cwd": "/path/to/kb-system"
      }
    }
  }
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import KnowledgePipeline

_pipeline = KnowledgePipeline()

TOOLS = [
    {
        "name": "kb_search",
        "description": "搜索知识库——支持语义搜索和关键词搜索",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索内容"},
                "mode": {"type": "string", "enum": ["semantic", "keyword"]},
                "limit": {"type": "integer"}
            }
        }
    },
    {
        "name": "kb_stats",
        "description": "知识库统计——笔记数、分类分布、向量索引状态",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "kb_graph",
        "description": "查询笔记的知识图谱关联",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "笔记标题"}
            }
        }
    },
    {
        "name": "kb_ingest",
        "description": "摄入对话内容——生成结构化笔记并写入笔记文件夹",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "要沉淀的对话内容"},
                "write": {"type": "boolean", "description": "是否实际写入（false=仅预览）"}
            }
        }
    },
]


def handle_request(req):
    method = req.get("method", "")
    params = req.get("params", {})
    rid = req.get("id")

    try:
        if method == "tools/list":
            return _ok(rid, {"tools": TOOLS})

        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            return _call_tool(rid, name, args)

        return _err(rid, -32601, f"Unknown method: {method}")

    except Exception as e:
        return _err(rid, -32000, str(e))


def _call_tool(rid, name, args):
    if name == "kb_search":
        q = args.get("query", "")
        mode = args.get("mode", "semantic")
        limit = min(args.get("limit", 5), 10)
        r = _pipeline.search(q, limit, mode)
        text = "\n".join(
            f"{h.get('score',''):.3f} [{h['category']}] {h['title']}"
            for h in r["results"]
        ) or "无结果"
        return _ok(rid, {"content": [{"type": "text", "text": text}]})

    elif name == "kb_stats":
        s = _pipeline.search("", limit=0)["db_stats"]
        text = f"{s['total_notes']} 篇笔记\n" + "\n".join(
            f"  {c['category']}: {c['count']}" for c in s["by_category"][:8]
        )
        return _ok(rid, {"content": [{"type": "text", "text": text}]})

    elif name == "kb_graph":
        title = args.get("title", "")
        if title:
            g = _pipeline.query_graph(title)
            edges = g.get("edges", [])
            text = f"{g['center']['title']} — {len(edges)} 条关联\n" + "\n".join(
                f"  [{e['relation_type']}] {e['neighbor']} ({e['confidence']})"
                for e in edges[:10]
            )
        else:
            gs = _pipeline.graph_stats()
            text = f"{gs['total_notes']} 节点, {gs['total_relations']} 边"
        return _ok(rid, {"content": [{"type": "text", "text": text}]})

    elif name == "kb_ingest":
        content = args.get("content", "")
        write = args.get("write", False)
        r = _pipeline.ingest(content) if not write else _pipeline.ingest(content)
        if r["action"] == "skip":
            text = f"跳过: {r.get('reason', '')}"
        else:
            text = f"[{r.get('category','')}] {r.get('title','')}\n{r.get('note_content','')[:500]}"
        return _ok(rid, {"content": [{"type": "text", "text": text}]})

    return _err(rid, -32601, f"Unknown tool: {name}")


def _ok(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _err(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def main():
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            print(json.dumps(handle_request(req), ensure_ascii=False), flush=True)
        except json.JSONDecodeError:
            continue


if __name__ == "__main__":
    main()
