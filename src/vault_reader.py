"""读取 Obsidian Vault 中的所有 Markdown 文件"""
import re
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from .config import VAULT_ROOT


@dataclass
class NoteDocument:
    """一篇 Obsidian 笔记"""
    path: Path
    title: str = ""
    content: str = ""
    frontmatter_data: dict = field(default_factory=dict)
    wikilinks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    modified_at: datetime | None = None
    category: str = ""


class VaultReader:
    """Obsidian Vault 读取器"""

    def __init__(self, vault_root: Path | None = None):
        self.vault_root = vault_root or VAULT_ROOT

    def discover(self) -> list[NoteDocument]:
        """扫描 Vault 中所有 markdown 文件"""
        notes = []
        for md_file in self.vault_root.rglob("*.md"):
            rel = md_file.relative_to(self.vault_root)

            # 跳过模板/系统/隐藏目录
            if rel.parts and rel.parts[0] in (
                "Templates", "System", ".obsidian", ".trash"
            ):
                continue

            try:
                note = self._parse_file(md_file)
                notes.append(note)
            except Exception:
                continue

        return notes

    def _parse_file(self, filepath: Path) -> NoteDocument:
        """解析单个 markdown 文件为 NoteDocument"""
        with open(filepath, "r", encoding="utf-8") as f:
            raw = f.read()

        # 尝试解析 YAML frontmatter
        fm_data = {}
        body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm_data = self._parse_yaml_frontmatter(parts[1])
                body = parts[2]

        # 提取 wikilinks: [[xxx]] 或 [[xxx|yyy]]
        wikilinks = re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]", body)

        # 提取 tags: #tag
        tags = list(set(re.findall(r"#([\w\u4e00-\u9fff-]+)", body)))

        # 标题：优先取 frontmatter title，否则取文件名
        title = fm_data.get("title", filepath.stem)

        # 分类：从相对路径推断
        rel = filepath.relative_to(self.vault_root)
        category = rel.parts[0] if rel.parts else ""

        # 文件时间戳
        stat = filepath.stat()
        modified_at = datetime.fromtimestamp(stat.st_mtime)

        return NoteDocument(
            path=filepath,
            title=title,
            content=body,
            frontmatter_data=fm_data,
            wikilinks=wikilinks,
            tags=tags,
            modified_at=modified_at,
            category=category,
        )

    def _parse_yaml_frontmatter(self, yaml_str: str) -> dict:
        """简单解析 frontmatter YAML（避免额外依赖）"""
        result = {}
        for line in yaml_str.strip().split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                result[key] = val
        return result
