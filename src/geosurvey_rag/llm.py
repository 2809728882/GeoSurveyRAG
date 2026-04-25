from __future__ import annotations

from dataclasses import dataclass


SYSTEM_PROMPT = """你是 GeoSurveyRAG，一个面向测绘工程、WebGIS 和空间数据生产的专业助手。
回答必须结合检索上下文；如果上下文不足，要明确说明缺口，并给出下一步数据需求。
涉及测绘质量、坐标、面积、距离和成果入库时，优先给出可执行检查清单。"""


@dataclass
class LocalLLM:
    """Offline answer composer used for demos and tests."""

    def generate(self, question: str, context: str, tool_summary: str = "") -> str:
        lines = [
            "基于当前测绘知识库，我的回答如下：",
            "",
            self._summarize_context(context),
        ]
        if tool_summary:
            lines.extend(["", "空间工具计算结果：", tool_summary])
        lines.extend(
            [
                "",
                "建议落地方式：先把该问题沉淀为标准 Prompt 和评测样例，再用 TopK、切片大小、召回阈值逐轮优化。",
                f"原始问题：{question}",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _summarize_context(context: str) -> str:
        if not context.strip():
            return "知识库没有召回到足够相关的片段，建议补充项目规范、作业指导书或验收报告。"
        sentences = [item.strip(" -。") for item in context.replace("\n", "。").split("。")]
        bullets = [item for item in sentences if len(item) >= 8][:6]
        return "\n".join(f"- {item}" for item in bullets)
