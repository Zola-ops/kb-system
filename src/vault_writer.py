"""写入 Obsidian Vault — 笔记创建 + Daily 更新"""
import re
from pathlib import Path
from datetime import datetime


class VaultWriter:
    """Obsidian Vault 写入器"""

    def __init__(self, vault_root: Path):
        self.vault_root = vault_root

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除冒号、括号、斜杠等
        name = re.sub(r'[:/\\*?"<>|()（）]', '', name)
        # 多个空格合并
        name = re.sub(r'\s+', ' ', name).strip()
        # 限制长度
        if len(name) > 50:
            name = name[:50]
        return name or "untitled"

    def write_note(self, category: str, filename: str, content: str) -> Path:
        """写入笔记到指定分类目录"""
        dir_path = self.vault_root / category
        dir_path.mkdir(parents=True, exist_ok=True)

        safe_name = self._sanitize_filename(filename)
        filepath = dir_path / f"{safe_name}.md"

        # 如果已存在同名文件，追加时间戳
        if filepath.exists():
            ts = datetime.now().strftime("%H%M")
            filepath = dir_path / f"{safe_name}-{ts}.md"

        filepath.write_text(content, encoding="utf-8")
        return filepath

    def update_daily(self, note_title: str, note_path: str, summary: str):
        """在今日 Daily 日记中添加笔记链接"""
        today = self._today_str()
        daily_dir = self.vault_root / "Daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        daily_path = daily_dir / f"{today}.md"

        # 如果 Daily 不存在，创建
        if not daily_path.exists():
            daily_path.write_text(
                f"# {today}\n\n## Agent 活动日志\n\n",
                encoding="utf-8"
            )

        content = daily_path.read_text(encoding="utf-8")
        link_line = f"- [[{note_title}]] — {summary}"

        if link_line not in content:
            if "## 今日记录" in content:
                content = content.replace(
                    "## 今日记录",
                    f"## 今日记录\n{link_line}",
                )
            elif "## Agent 活动日志" in content:
                content = content.replace(
                    "## Agent 活动日志",
                    f"## Agent 活动日志\n{link_line}",
                )
            else:
                content += f"\n{link_line}\n"

            daily_path.write_text(content, encoding="utf-8")
