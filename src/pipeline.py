"""知识摄入管线 — 串联读取→分类→生成→写入→索引→语义检索"""
import json
from .vault_reader import VaultReader
from .vault_writer import VaultWriter
from .database import KnowledgeDB
from .ingest import ConversationIngestor
from .embeddings import EmbeddingEngine
from .config import VAULT_ROOT, DB_PATH


class KnowledgePipeline:
    """端到端知识摄入管线"""

    def __init__(self, dry_run: bool = False):
        self.reader = VaultReader(VAULT_ROOT)
        self.writer = VaultWriter(VAULT_ROOT)
        self.db = KnowledgeDB(DB_PATH)
        self.ingestor = ConversationIngestor()
        self.embedder: EmbeddingEngine | None = None
        self.dry_run = dry_run

    def _get_embedder(self) -> EmbeddingEngine:
        if self.embedder is None:
            self.embedder = EmbeddingEngine()
        return self.embedder

    def ingest(self, conversation: str) -> dict:
        """摄入一段对话，自动沉淀为 Obsidian 笔记

        Returns:
            {
                "action": "create" | "skip",
                "title": str,
                "category": str,
                "path": str,
                "note_content": str,
                "reason": str,
            }
        """
        # 1. 获取已有笔记列表（用于 wikilink 建议）
        existing_notes = self._get_existing_titles()

        # 2. LLM 分类 + 生成
        result = self.ingestor.process(conversation, existing_notes)
        if result is None or result["action"] == "skip":
            return {
                "action": "skip",
                "reason": result.get("reason", "不值得记录") if result else "处理失败",
            }

        classification = result["classification"]
        note_content = result["note_content"]

        if self.dry_run:
            return {
                "action": "dry_run",
                "title": classification.get("title", ""),
                "category": classification.get("category", ""),
                "summary": classification.get("summary", ""),
                "tags": classification.get("tags", []),
                "note_content": note_content,
            }

        # 3. 写入 Obsidian
        category = classification.get("category", "Projects")
        title = classification.get("title", "untitled")
        filepath = self.writer.write_note(category, title, note_content)

        # 4. 更新 Daily 日记
        self.writer.update_daily(
            note_title=title,
            note_path=str(filepath.relative_to(VAULT_ROOT)),
            summary=classification.get("summary", ""),
        )

        # 5. 同步到 SQLite 索引
        self.db.init()
        notes = self.reader.discover()
        self.db.sync_from_vault(notes)

        return {
            "action": "created",
            "title": title,
            "category": category,
            "path": str(filepath),
            "note_content": note_content,
        }

    def search(self, query: str, limit: int = 10, mode: str = "keyword") -> dict:
        """检索知识库

        Args:
            query: 搜索内容
            limit: 返回条数
            mode: 'keyword' (默认) | 'semantic' (语义)
        """
        self.db.init()
        stats = self.db.get_stats()

        if mode == "semantic" and self.db.embedding_count() > 0:
            embedder = self._get_embedder()
            qv = embedder.embed(query)
            results = self.db.search_semantic(qv, limit)
        else:
            results = self.db.search_by_keyword(query, limit)

        return {
            "query": query,
            "mode": mode,
            "results": results,
            "total_hits": len(results),
            "db_stats": stats,
        }

    def index_embeddings(self) -> dict:
        """为所有未索引的笔记生成向量嵌入"""
        self.db.init()
        pending = self.db.get_notes_needing_embedding()
        if not pending:
            return {"status": "up_to_date", "count": self.db.embedding_count()}

        embedder = self._get_embedder()
        texts = []
        for _, title, content in pending:
            # 标题权重加倍 + 取前 1500 字（MiniLM 支持 256 token ≈ 600-800 中文字，取充足些）
            texts.append(f"{title}\n{title}\n{content[:1500]}")

        print(f"生成 {len(texts)} 条向量... (模型: {embedder.model_name})")
        vectors = embedder.embed_batch(texts)

        for i, (nid, title, _) in enumerate(pending):
            self.db.store_embedding(nid, vectors[i])

        return {
            "status": "indexed",
            "new": len(pending),
            "total": self.db.embedding_count(),
            "dim": embedder.dim,
        }

    def build_graph(self) -> dict:
        """构建知识图谱：wikilink 解析 + 共享实体 + 语义近邻"""
        self.db.init()

        # 清除旧关系
        self.db.conn.execute("DELETE FROM relations")
        self.db.conn.execute("DELETE FROM entities")

        stats = {"wikilink_edges": 0, "shared_tag_edges": 0, "semantic_edges": 0}

        # 1. wikilink → 关系（A 链接 B 是可解析的笔记名）
        notes = self.db.conn.execute(
            "SELECT id, title, wikilinks_json FROM notes"
        ).fetchall()
        id_map = {r["title"]: r["id"] for r in notes}
        title_norm = {t.lower().replace(" ", ""): t for t in id_map}

        for row in notes:
            src_id = row["id"]
            try:
                links = json.loads(row["wikilinks_json"])
            except (json.JSONDecodeError, TypeError):
                links = []
            for link in links:
                target_id = id_map.get(link) or id_map.get(
                    title_norm.get(link.lower().replace(" ", ""), "")
                )
                if target_id and target_id != src_id:
                    self.db.conn.execute(
                        "INSERT INTO relations (source_note_id, target_note_id, "
                        "relation_type, confidence) VALUES (?,?,?,?)",
                        (src_id, target_id, "wikilink", 0.9)
                    )
                    stats["wikilink_edges"] += 1

        # 2. 共享 tag → 关系
        tags_data = self.db.conn.execute(
            "SELECT id, tags_json FROM notes"
        ).fetchall()
        tag_to_notes: dict[str, list[int]] = {}
        for row in tags_data:
            try:
                tags = json.loads(row["tags_json"])
            except (json.JSONDecodeError, TypeError):
                tags = []
            for tag in tags:
                tag_to_notes.setdefault(tag, []).append(row["id"])

        seen_pairs = set()
        for tag, nids in tag_to_notes.items():
            for i in range(len(nids)):
                for j in range(i + 1, len(nids)):
                    pair = (min(nids[i], nids[j]), max(nids[i], nids[j]))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        self.db.conn.execute(
                            "INSERT INTO relations (source_note_id, target_note_id, "
                            "relation_type, source_entity, confidence) VALUES (?,?,?,?,?)",
                            (nids[i], nids[j], "shared_tag", tag, 0.7)
                        )
                        stats["shared_tag_edges"] += 1

        # 3. 语义近邻 → 关系（相似度 > 0.5）
        all_embs = self.db.get_embeddings()
        if len(all_embs) > 1:
            embedder = self._get_embedder()
            vectors = {nid: vec for nid, _, vec in all_embs}
            nids = list(vectors.keys())
            for i in range(len(nids)):
                for j in range(i + 1, len(nids)):
                    a, b = nids[i], nids[j]
                    sim = embedder.similarity(vectors[a], vectors[b])
                    if sim > 0.55:  # 阈值偏高，只保留强关联
                        self.db.conn.execute(
                            "INSERT INTO relations (source_note_id, target_note_id, "
                            "relation_type, confidence) VALUES (?,?,?,?)",
                            (a, b, "semantic", round(sim, 3))
                        )
                        stats["semantic_edges"] += 1

        self.db.conn.commit()
        stats["total_edges"] = sum(stats.values())
        return stats

    def query_graph(self, note_title: str, depth: int = 1) -> dict:
        """查询某篇笔记的知识图谱邻域"""
        self.db.init()
        row = self.db.conn.execute(
            "SELECT id, title, category FROM notes WHERE title=?",
            (note_title,)
        ).fetchone()
        if not row:
            return {"error": f"未找到笔记: {note_title}"}

        center_id = row["id"]

        # 查询直接关联的笔记
        edges = self.db.conn.execute("""
            SELECT r.relation_type, r.confidence,
                   CASE WHEN r.source_note_id=? THEN n2.title ELSE n1.title END as neighbor,
                   CASE WHEN r.source_note_id=? THEN n2.category ELSE n1.category END as neighbor_cat
            FROM relations r
            JOIN notes n1 ON r.source_note_id = n1.id
            JOIN notes n2 ON r.target_note_id = n2.id
            WHERE r.source_note_id=? OR r.target_note_id=?
            ORDER BY r.confidence DESC
            LIMIT 20
        """, (center_id, center_id, center_id, center_id)).fetchall()

        return {
            "center": {"title": row["title"], "category": row["category"]},
            "edges": [dict(e) for e in edges],
            "total_relations": len(edges),
        }

    def graph_stats(self) -> dict:
        """知识图谱全局统计"""
        self.db.init()
        return {
            "total_notes": self.db.conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0],
            "total_relations": self.db.conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
            "by_type": [dict(r) for r in self.db.conn.execute(
                "SELECT relation_type, COUNT(*) as count FROM relations GROUP BY relation_type"
            ).fetchall()],
            "most_connected": [dict(r) for r in self.db.conn.execute("""
                SELECT n.title, n.category, COUNT(*) as degree
                FROM relations r JOIN notes n ON n.id IN (r.source_note_id, r.target_note_id)
                GROUP BY n.id ORDER BY degree DESC LIMIT 10
            """).fetchall()],
        }

    def _get_existing_titles(self, limit: int = 30) -> list[str]:
        """获取已有笔记标题列表（用于 wikilink 建议）"""
        try:
            notes = self.reader.discover()
            # 优先返回 Reports + Projects 的标题
            important = [n.title for n in notes
                        if n.category in ("Reports", "Projects", "Learnings")]
            return important[:limit]
        except Exception:
            return []
