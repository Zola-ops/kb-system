"""SQLite 知识索引数据库 — notes / entities / relations"""
import json
import sqlite3
import struct
import numpy as np
from pathlib import Path
from datetime import datetime
from .vault_reader import NoteDocument


class KnowledgeDB:
    """知识库关系索引"""

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self.conn: sqlite3.Connection | None = None

    def init(self):
        """初始化数据库和表"""
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filepath TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT '',
                content TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                wikilinks_json TEXT DEFAULT '[]',
                tags_json TEXT DEFAULT '[]',
                entities_json TEXT DEFAULT '[]',
                created_at TEXT,
                modified_at TEXT,
                has_embedding INTEGER DEFAULT 0
            );

            -- 全文搜索虚拟表
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title, content, content=notes, content_rowid=id
            );

            -- 触发器：插入 notes 时自动同步到 FTS
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, title, content)
                VALUES (new.id, new.title, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content)
                VALUES ('delete', old.id, old.title, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content)
                VALUES ('delete', old.id, old.title, old.content);
                INSERT INTO notes_fts(rowid, title, content)
                VALUES (new.id, new.title, new.content);
            END;

            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                entity_type TEXT DEFAULT 'concept',
                first_seen TEXT,
                mention_count INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_note_id INTEGER NOT NULL,
                target_note_id INTEGER,
                relation_type TEXT DEFAULT 'reference',
                source_entity TEXT,
                target_entity TEXT,
                confidence REAL DEFAULT 1.0,
                FOREIGN KEY (source_note_id) REFERENCES notes(id)
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                note_id INTEGER PRIMARY KEY,
                vector BLOB NOT NULL,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category);
            CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_note_id);
        """)
        self.conn.commit()

    def upsert_note(self, note: NoteDocument):
        """插入或更新笔记（按 filepath 去重）"""
        self.conn.execute("""
            INSERT INTO notes (title, filepath, category, content, wikilinks_json,
                               tags_json, modified_at, has_embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(filepath) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                wikilinks_json=excluded.wikilinks_json,
                tags_json=excluded.tags_json,
                modified_at=excluded.modified_at
        """, (
            note.title,
            str(note.path),
            note.category,
            note.content[:5000],
            json.dumps(note.wikilinks, ensure_ascii=False),
            json.dumps(note.tags, ensure_ascii=False),
            datetime.now().isoformat(),
        ))
        self.conn.commit()

    def sync_from_vault(self, notes: list[NoteDocument]):
        """从 Vault 全量同步笔记"""
        for note in notes:
            self.upsert_note(note)

    def search_by_keyword(self, query: str, limit: int = 10) -> list[dict]:
        """关键词检索（SQLite LIKE）"""
        pattern = f"%{query}%"
        rows = self.conn.execute("""
            SELECT title, filepath, category,
                   substr(content, 1, 200) as snippet
            FROM notes
            WHERE content LIKE ? OR title LIKE ?
            ORDER BY modified_at DESC
            LIMIT ?
        """, (pattern, pattern, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        return {
            "total_notes": self.conn.execute(
                "SELECT COUNT(*) FROM notes"
            ).fetchone()[0],
            "total_entities": self.conn.execute(
                "SELECT COUNT(*) FROM entities"
            ).fetchone()[0],
            "total_relations": self.conn.execute(
                "SELECT COUNT(*) FROM relations"
            ).fetchone()[0],
            "by_category": [
                dict(r) for r in self.conn.execute(
                    "SELECT category, COUNT(*) as count FROM notes "
                    "GROUP BY category ORDER BY count DESC"
                ).fetchall()
            ],
        }

    # ── 向量嵌入 ──

    def store_embedding(self, note_id: int, vector: np.ndarray):
        """存储单条向量的 float32 二进制"""
        blob = vector.astype(np.float32).tobytes()
        self.conn.execute(
            "INSERT OR REPLACE INTO embeddings (note_id, vector) VALUES (?, ?)",
            (note_id, blob)
        )
        self.conn.execute(
            "UPDATE notes SET has_embedding=1 WHERE id=?", (note_id,)
        )
        self.conn.commit()

    def get_embeddings(self) -> list[tuple[int, str, np.ndarray]]:
        """获取所有有向量的笔记 (id, title, vector)"""
        rows = self.conn.execute("""
            SELECT n.id, n.title, e.vector
            FROM notes n JOIN embeddings e ON n.id = e.note_id
        """).fetchall()
        return [(r[0], r[1], np.frombuffer(r[2], dtype=np.float32)) for r in rows]

    def get_notes_needing_embedding(self) -> list[tuple[int, str, str]]:
        """获取需要生成向量的笔记 (id, title, content)"""
        rows = self.conn.execute(
            "SELECT id, title, content FROM notes WHERE has_embedding=0"
        ).fetchall()
        return [(r[0], r[1], r[2] or "") for r in rows]

    def embedding_count(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM embeddings"
        ).fetchone()[0]

    # ── 语义搜索 ──

    def search_semantic(self, query_vector: np.ndarray, top_k: int = 10) -> list[dict]:
        """余弦相似度搜索（全量计算，86 条毫秒级）"""
        all_embs = self.get_embeddings()
        if not all_embs:
            return []

        scored = []
        for nid, title, vec in all_embs:
            sim = float(np.dot(query_vector, vec))
            scored.append((nid, title, sim))

        scored.sort(key=lambda x: x[2], reverse=True)
        top = scored[:top_k]

        # 补充 snippet
        result = []
        for nid, title, sim in top:
            row = self.conn.execute(
                "SELECT filepath, category, substr(content,1,200) FROM notes WHERE id=?",
                (nid,)
            ).fetchone()
            if row:
                result.append({
                    "title": title,
                    "filepath": row[0],
                    "category": row[1],
                    "snippet": row[2],
                    "score": round(sim, 4),
                })
        return result

    def close(self):
        if self.conn:
            self.conn.close()
