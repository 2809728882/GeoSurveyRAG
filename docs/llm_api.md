# 大模型 API 配置

GeoSurveyRAG 默认使用本地回答器，保证没有 API Key 时也能运行完整 RAG 流程。需要接入真实大模型时，可以启用 OpenAI-compatible provider。

## 环境变量

```env
LLM_PROVIDER=openai-compatible
OPENAI_API_KEY=你的_API_Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT=60
OPENAI_TEMPERATURE=0.2
```

字段说明：

- `LLM_PROVIDER`：`local` 或 `openai-compatible`。
- `OPENAI_API_KEY`：模型服务 API Key。
- `OPENAI_BASE_URL`：OpenAI-compatible 服务地址，不包含 `/chat/completions`。
- `OPENAI_MODEL`：模型名称。
- `OPENAI_TIMEOUT`：请求超时时间，单位秒。
- `OPENAI_TEMPERATURE`：生成温度，越低越稳定。

## 常见配置

```env
# OpenAI
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini

# DeepSeek
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash

# Qwen / 阿里云百炼
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# 智谱 GLM
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4-flash
```

## 回退机制

如果出现以下情况，系统会自动回退到本地回答器：

- 未配置 `OPENAI_API_KEY`。
- 模型接口网络请求失败。
- 返回 JSON 格式异常。
- 返回内容没有 `choices[0].message.content`。

这样可以保证演示、测试和离线评测不被外部模型服务影响。
