"""测试 SQLite 知识索引数据库"""
import pytest
from pathlib import Path
from src.database import KnowledgeDB
from src.vault_reader import NoteDocument


@pytest.fixture
def db():
    """使用内存数据库隔离测试"""
    kb = KnowledgeDB(":memory:")
    kb.init()
    yield kb
    kb.close()


def test_init_creates_tables(db):
    """验证初始化创建了核心表"""
    tables = db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {t[0] for t in tables}
    assert "notes" in table_names
    assert "entities" in table_names
    assert "relations" in table_names


def test_upsert_note(db):
    """验证插入笔记"""
    note = NoteDocument(
        path=Path("/fake/Daily/test.md"),
        title="测试笔记",
        content="这是一个测试内容，包含关键词",
        wikilinks=["其他笔记"],
        tags=["test"],
        category="Daily",
    )
    db.upsert_note(note)
    rows = db.conn.execute("SELECT * FROM notes").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "测试笔记"
    assert row["category"] == "Daily"


def test_upsert_is_idempotent(db):
    """验证重复插入是幂等的（update）"""
    note = NoteDocument(
        path=Path("/fake/Projects/dup.md"),
        title="原始标题",
        content="v1",
        category="Projects",
    )
    db.upsert_note(note)
    # 更新内容
    note.content = "v2 updated"
    note.title = "新标题"
    db.upsert_note(note)

    rows = db.conn.execute("SELECT * FROM notes").fetchall()
    assert len(rows) == 1, "应该仍然只有 1 条"
    assert rows[0]["title"] == "新标题"


def test_search_by_keyword(db):
    """验证关键词检索"""
    notes = [
        NoteDocument(path=Path(f"/fake/Reports/r{i}.md"), title=f"报告{i}",
                     content=f"关于GSB评估的深度分析报告第{i}号",
                     category="Reports")
        for i in range(3)
    ]
    for n in notes:
        db.upsert_note(n)

    results = db.search_by_keyword("GSB", limit=10)
    assert len(results) == 3
    for r in results:
        assert "GSB" in r["snippet"]


def test_sync_from_vault(db):
    """验证从 Vault 批量同步"""
    notes = [
        NoteDocument(path=Path("/fake/Projects/p1.md"), title="项目A",
                     content="内容A", category="Projects"),
        NoteDocument(path=Path("/fake/Reports/r1.md"), title="报告A",
                     content="内容B", category="Reports"),
        NoteDocument(path=Path("/fake/Daily/d1.md"), title="日记A",
                     content="内容C", category="Daily"),
    ]
    db.sync_from_vault(notes)

    stats = db.get_stats()
    assert stats["total_notes"] == 3
    by_cat = {r["category"]: r["count"] for r in stats["by_category"]}
    assert by_cat.get("Projects") == 1
    assert by_cat.get("Reports") == 1
    assert by_cat.get("Daily") == 1


def test_get_stats_empty(db):
    """验证空数据库统计"""
    stats = db.get_stats()
    assert stats["total_notes"] == 0
    assert stats["total_entities"] == 0
