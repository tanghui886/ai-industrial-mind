"""Deep Agents 基础模块：模型初始化 / 开关 / 会话基座。

统一从 config.yaml 读取 LLM 配置（OpenAI 兼容协议，指向 DeepSeek）。
未配置 API Key 时 `ENABLE_DEEP_AGENTS=False`，编排层回退到内置规则引擎。
"""
from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger("containermind.agents")

# 是否启用 Deep Agents 编排（依赖 LLM Key 与依赖包是否可用）
try:
    import deepagents  # noqa: F401
    _HAS_DEEPAGENTS = True
except Exception as e:  # noqa: BLE001
    _HAS_DEEPAGENTS = False
    logger.warning("deepagents 未安装或不可用，多 Agent 编排将回退规则引擎: %s", e)

ENABLE_DEEP_AGENTS = settings.LLM_ENABLED and _HAS_DEEPAGENTS

# 主 Agent 名称与展示名
MAIN_AGENT_NAME = "containermind-main"
AGENT_DISPLAY = "深度协同 · 多智能体编排"


def get_model(temperature: float = 0.2):
    """构建 LangChain ChatOpenAI 模型（指向 config.yaml 中的 LLM_BASE_URL/API_KEY/MODEL）。"""
    if not settings.LLM_ENABLED:
        return None
    try:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            temperature=temperature,
            timeout=60,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("构建 LangChain 模型失败: %s", e)
        return None