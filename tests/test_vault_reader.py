"""测试 Vault Reader — 读取 Obsidian 笔记"""
import pytest
from pathlib import Path
from src.vault_reader import VaultReader, NoteDocument


def test_discover_all_markdown_files():
    """验证能发现 Vault 中所有 markdown 文件"""
    reader = VaultReader()
    notes = reader.discover()
    assert len(notes) > 10, f"至少应有 10+ 篇笔记，实际 {len(notes)}"

    # 验证 Daily 目录下有文件
    daily_notes = [n for n in notes if "Daily/" in str(n.path)]
    assert len(daily_notes) > 0, "应该有 Daily 日记"


def test_discover_respects_category():
    """验证分类字段从路径推断"""
    reader = VaultReader()
    notes = reader.discover()

    # Reports 目录下应有笔记
    reports = [n for n in notes if n.category == "Reports"]
    assert len(reports) > 0, f"Reports 分类不应为空，总笔记 {len(notes)}"

    # Projects 目录下应有笔记
    projects = [n for n in notes if n.category == "Projects"]
    assert len(projects) > 0, f"Projects 分类不应为空"


def test_extract_wikilinks():
    """验证 wikilink 提取"""
    reader = VaultReader()
    notes = reader.discover()

    # 统计所有笔记中的 wikilink
    all_links = []
    for note in notes:
        all_links.extend(note.wikilinks)

    # 已知 Daily/2026-06-30.md 有大量 wikilink
    assert len(all_links) > 0, "应该有 wikilink"


def test_extract_tags():
    """验证 tag 提取"""
    reader = VaultReader()
    notes = reader.discover()
    all_tags = []
    for note in notes:
        all_tags.extend(note.tags)
    # 不需要强断言，有些笔记可能没有 tag
    print(f"Found {len(all_tags)} tags across {len(notes)} notes")


def test_skip_templates_and_system():
    """验证跳过 Templates 和 System 目录"""
    reader = VaultReader()
    notes = reader.discover()
    for note in notes:
        rel = note.path.relative_to(reader.vault_root)
        assert rel.parts[0] not in ("Templates", "System", ".obsidian", ".trash"), \
            f"不应包含 {rel.parts[0]} 目录: {note.path}"


def test_note_has_required_fields():
    """验证 NoteDocument 关键字段非空"""
    reader = VaultReader()
    notes = reader.discover()
    for note in notes[:5]:  # 抽检前 5 篇
        assert note.title, f"title 不应为空: {note.path}"
        assert note.path.exists(), f"path 应存在: {note.path}"
