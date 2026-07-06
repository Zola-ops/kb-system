"""对话摄入：LLM 驱动的分类器 + 结构化笔记生成器"""
import json
from datetime import datetime
from openai import OpenAI
from .config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL


CLASSIFIER_PROMPT = """你是一个知识管理分类器。分析以下对话内容，判断是否值得沉淀为个人知识库笔记。

## 分类标准

**值得记录（return true）**的场景：
- 完成了复杂任务（3+ 步骤或多次工具调用）
- 解决了一个非预期的错误/bug
- 得出了数据分析结论或报告
- 创建/部署了新项目或功能
- 学到了新技术/工具/API 用法
- 做出了重要的技术决策或方案确认

**不值得记录（return false）**的场景：
- 简单的一问一答
- 闲聊/问候
- 仅查询信息但没有新产出
- 内容已在已有笔记中重复覆盖

## 对话内容

{conversation}

## 输出格式

严格输出 JSON，不要任何额外文字：
{{
  "worth_saving": true,
  "category": "Projects",
  "title": "简洁标题15字内",
  "summary": "一句话30字内",
  "reason": "为什么值得/不值得10字内",
  "tags": ["标签1", "标签2"]
}}

category 必须是以下之一：Projects, Fixes, Reports, Learnings
"""


NOTE_GENERATOR_PROMPT = """基于以下对话内容，生成一篇结构化的 Obsidian 笔记。

## 笔记要求

1. 从对话中提取关键信息，不要编造不存在的内容
2. 踩坑记录只写对话中真实出现的问题和解决方法
3. wikilink 必须使用 [[笔记名]] 格式，引用对话中明确提到的项目或概念
4. 使用中文书写

## 输出格式

**直接输出完整的 markdown 原始内容，不要用代码块包裹。** 格式如下：

# {{标题}}

> {{一句话总结}}

## 背景

为什么要做这件事？上下文是什么？

## 做了什么

### 关键步骤
1. 步骤一
2. 步骤二

### 技术细节
- 使用的工具/技术
- 关键操作

## 踩坑记录

（如果对话中没有踩坑，写"本次无踩坑"）

### 坑 1：{{问题描述}}
- **现象**：xxx
- **原因**：xxx
- **解决**：xxx

## 收获与反思

1. **技术收获**：xxx
2. **可复用经验**：xxx

## 相关链接

- [[相关笔记1]]
- [[相关笔记2]]

---
*自动生成于 {timestamp}*

## 对话内容

{conversation}

## 额外上下文

分类: {category}
已有相关笔记（wikilink 候选）: {existing_notes}
"""


class ConversationIngestor:
    """对话摄入器：分类 → 生成 → 返回结构化笔记"""

    def __init__(self, base_url: str | None = None,
                 api_key: str | None = None,
                 model: str | None = None):
        self.client = OpenAI(
            base_url=base_url or LLM_BASE_URL,
            api_key=api_key or LLM_API_KEY,
        )
        self.model = model or LLM_MODEL

    def classify(self, conversation: str) -> dict:
        """判断对话是否值得沉淀"""
        prompt = CLASSIFIER_PROMPT.format(
            conversation=self._truncate(conversation, 6000)
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)

    def generate_note(self, conversation: str, classification: dict,
                      existing_notes: list[str] | None = None) -> str:
        """生成结构化 Obsidian 笔记"""
        prompt = NOTE_GENERATOR_PROMPT.format(
            conversation=self._truncate(conversation, 6000),
            category=classification.get("category", "Projects"),
            existing_notes=", ".join(existing_notes or []),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content

    def process(self, conversation: str,
                existing_notes: list[str] | None = None) -> dict | None:
        """完整处理管线：分类 → 生成 → 返回"""
        classification = self.classify(conversation)

        if not classification.get("worth_saving"):
            return {
                "action": "skip",
                "reason": classification.get("reason", "不值得记录"),
            }

        note_content = self.generate_note(
            conversation, classification, existing_notes
        )

        return {
            "action": "create",
            "classification": classification,
            "note_content": note_content,
        }

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """截断过长文本"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n... (内容过长已截断)"
