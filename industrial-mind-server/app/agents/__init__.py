"""智能体 Agents 目录：规范多 Agent 编排（Deep Agents 框架）。

目录结构约定：
- base.py        模型初始化与公共工具基座
- <domain>_agent.py  各子 Agent（排产/设备诊断/物料缺口/堆存风险/成本动因）
- main_agent.py  主 Agent（deepagents 编排，注册子 Agent 与 skills）

子 Agent 通过主 Agent 暴露的 `task` 工具被调用，各自持有独立的领域工具与
system prompt（stateless，单次指令完成完整上下文）。
"""
from .base import ENABLE_DEEP_AGENTS, get_model  # noqa: F401
from .main_agent import build_agent, chat  # noqa: F401

__all__ = ["ENABLE_DEEP_AGENTS", "get_model", "build_agent", "chat"]