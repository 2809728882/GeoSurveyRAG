from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from geosurvey_rag.settings import settings


SYSTEM_PROMPT = """你是 GeoSurveyRAG，一个面向测绘工程、WebGIS 和空间数据生产的专业助手。
回答必须结合检索上下文；如果上下文不足，要明确说明缺口，并给出下一步数据需求。
涉及测绘质量、坐标、面积、距离和成果入库时，优先给出可执行检查清单。
回答风格要像业务系统里的专业结论，不要使用 Markdown 标题符号、星号、横线项目符号或代码围栏。"""


class LLMClient(Protocol):
    def generate(self, question: str, context: str, tool_summary: str = "") -> str:
        ...


def build_user_prompt(question: str, context: str, tool_summary: str = "") -> str:
    parts = [
        "请基于以下检索上下文回答用户问题。",
        "",
        "## 用户问题",
        question,
        "",
        "## 检索上下文",
        context or "未召回到相关上下文。",
    ]
    if tool_summary:
        parts.extend(["", "## 工具调用结果", tool_summary])
    parts.extend(
        [
            "",
            "## 回答要求",
            "- 用中文回答。",
            "- 优先给出测绘/GIS 场景下可执行的步骤或检查清单。",
            "- 不要编造上下文中没有的事实；如信息不足，请明确说明。",
            "- 如使用了工具结果，请在回答中说明计算结论。",
            "- 输出要简洁美观，不要使用 #、*、-、``` 等 Markdown 符号。",
        ]
    )
    return "\n".join(parts)


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


@dataclass
class OpenAICompatibleLLM:
    """OpenAI-compatible chat completions client.

    It works with OpenAI and many compatible providers when base_url/model/api_key are set.
    """

    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 60
    temperature: float = 0.2

    def generate(self, question: str, context: str, tool_summary: str = "") -> str:
        if not self.api_key:
            return LocalLLM().generate(
                question,
                context,
                tool_summary + "\n- LLM API 未配置 OPENAI_API_KEY，已回退到本地回答器。",
            )

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(question, context, tool_summary)},
            ],
        }
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        request = Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return LocalLLM().generate(
                question,
                context,
                tool_summary + f"\n- LLM API 调用失败，已回退到本地回答器：{exc}",
            )

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            return LocalLLM().generate(
                question,
                context,
                tool_summary + "\n- LLM API 返回格式异常，已回退到本地回答器。",
            )


def create_llm() -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider in {"openai", "openai-compatible", "compatible"}:
        return OpenAICompatibleLLM(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout=settings.openai_timeout,
            temperature=settings.openai_temperature,
        )
    return LocalLLM()
