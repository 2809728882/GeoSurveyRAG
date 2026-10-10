import pytest
from urllib.error import URLError

from geosurvey_rag import llm


def test_offline_excerpt_selects_relevant_tail_and_preserves_citation():
    text = "[1] 来源：field.md\nRTK 作业检查差分延迟。全站仪检查闭合差。Python 清洗数据检查重复点、空值和异常坐标。"
    answer = llm.LocalLLM().generate("Python 如何清洗数据", text)
    assert "Python 清洗数据检查重复点" in answer
    assert "[1]" in answer


@pytest.mark.parametrize(
    "payload", [{"choices": []}, {"choices": [{"message": {"content": None}}]}, {}]
)
def test_malformed_model_response_falls_back(monkeypatch, payload):
    import json

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            return json.dumps(payload).encode()

    monkeypatch.setattr(llm, "urlopen", lambda *args, **kwargs: Response())
    client = llm.OpenAICompatibleLLM(api_key="fixture", model="fixture")
    assert "本地资料摘录" in client.generate("RTK 检查", "RTK 作业检查固定解与差分延迟。")


def test_network_failure_falls_back(monkeypatch):
    def offline(*args, **kwargs):
        raise URLError("offline fixture")

    monkeypatch.setattr(llm, "urlopen", offline)
    client = llm.OpenAICompatibleLLM(api_key="fixture", model="fixture")
    assert "差分延迟" in client.generate("RTK 检查", "RTK 作业检查固定解与差分延迟。")
