"""全局配置"""
import os
from pathlib import Path

# 自动加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# 笔记根目录（默认 Obsidian Vault，可指向任意 Markdown 文件夹）
NOTES_ROOT = Path(os.getenv("NOTES_ROOT", os.path.expanduser("~/Documents/Obsidian Vault")))

# Obsidian 特有功能（wikilink [[解析]]、Daily 日记自动更新）
# 如果使用普通 Markdown 文件夹，这些功能仍然可用（wikilink 是通用语法）
OBSIDIAN_MODE = os.getenv("OBSIDIAN_MODE", "true").lower() == "true"

# 知识库系统数据目录
DATA_DIR = Path(__file__).parent.parent / "data"

# LLM 配置（复用 Hermes 的 OneAPI / 百度 AI）
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v3")

# 嵌入模型（80MB，本地推理）
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 数据库路径
DB_PATH = DATA_DIR / "kb_index.db"

# 文档分类关键词映射
CATEGORY_KEYWORDS = {
    "Projects": ["创建", "部署", "发布", "开发", "构建", "初始化项目"],
    "Fixes": ["修复", "解决", "bug", "报错", "踩坑", "排查"],
    "Reports": ["分析", "报告", "评估", "总结", "对比", "GSB"],
    "Learnings": ["学习", "发现", "笔记", "教程", "文档"],
}
