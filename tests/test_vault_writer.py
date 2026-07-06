"""测试 Vault Writer — 写入 Obsidian 笔记"""
import tempfile
from pathlib import Path
from src.vault_writer import VaultWriter


def test_write_note_creates_file():
    """验证写入笔记文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(Path(tmpdir))
        (Path(tmpdir) / "Projects").mkdir()

        result = writer.write_note(
            category="Projects",
            filename="test-project",
            content="# 测试项目\n\nHello world",
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "# 测试项目" in content
        assert "Hello world" in content


def test_write_note_handles_duplicate():
    """验证重名文件加时间戳"""
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(Path(tmpdir))
        (Path(tmpdir) / "Projects").mkdir()

        # 写入两次同名文件
        path1 = writer.write_note("Projects", "dup-name", "# V1")
        path2 = writer.write_note("Projects", "dup-name", "# V2")

        assert path1.exists()
        assert path2.exists()
        assert path1 != path2  # 不同文件
        assert "dup-name" in path2.stem  # 包含原名


def test_update_daily_adds_wikilink():
    """验证更新 Daily 日记"""
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(Path(tmpdir))
        (Path(tmpdir) / "Daily").mkdir()

        today = writer._today_str()
        daily_path = Path(tmpdir) / "Daily" / f"{today}.md"
        daily_path.write_text(f"# {today}\n\n## 今日记录\n\n", encoding="utf-8")

        writer.update_daily(
            note_title="test-project",
            note_path="Projects/test-project.md",
            summary="测试项目记录摘要",
        )

        content = daily_path.read_text(encoding="utf-8")
        assert "[[test-project]]" in content
        assert "测试项目记录摘要" in content


def test_update_daily_creates_if_missing():
    """验证 Daily 不存在时自动创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = VaultWriter(Path(tmpdir))

        writer.update_daily(
            note_title="new-note",
            note_path="Projects/new-note.md",
            summary="新笔记",
        )

        today = writer._today_str()
        daily_path = Path(tmpdir) / "Daily" / f"{today}.md"
        assert daily_path.exists()
        content = daily_path.read_text(encoding="utf-8")
        assert "[[new-note]]" in content


def test_sanitize_filename():
    """验证文件名清理"""
    writer = VaultWriter(Path("/tmp"))
    # 带特殊字符的文件名应被清理
    result = writer._sanitize_filename("GSB分析: 猎户座 vs 豆包 (2024)")
    assert ":" not in result
    assert "(" not in result
    assert "GSB分析" in result
