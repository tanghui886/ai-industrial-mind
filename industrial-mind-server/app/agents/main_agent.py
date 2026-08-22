"""主 Agent Main：基于 deepagents.create_deep_agent 的规范多 Agent 编排。

- 主 Agent 内置 SubAgentMiddleware（暴露 `task` 工具）与 TodoListMiddleware。
- 注册各子 Agent：scheduler（智能排产）/ device（设备诊断）/ material（物料缺口）/
  storage（堆存风险）/ cost（成本动因）/ supplier（供货商动态）。
- 子 Agent stateless：由主 Agent 一次性下发完整指令后独立执行并返回结论。
- 通过 `task(agent=..., instruction=...)` 触发对应子 Agent。
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..config import settings
from .base import ENABLE_DEEP_AGENTS, AGENT_DISPLAY, get_model
from .scheduler_agent import make_scheduler_agent
from .device_agent import make_device_agent
from .material_agent import make_material_agent
from .storage_agent import make_storage_agent
from .cost_agent import make_cost_agent
from .supplier_agent import make_supplier_agent

logger = logging.getLogger("containermind.agents")

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

MAIN_SYSTEM_PROMPT = """你是「ContainerMind 工业协同」的主调度 Agent。负责理解用户意图并编排各专业子 Agent 协同完成任务。

可调用的子 Agent（通过 task 工具下发指令，agent=<名称>，instruction=<完整指令>）：
- scheduler：智能排产——新订单排产可行性评估、产线产能查询、工令排产进度查询。
- device：设备诊断——指定产线异常设备逐台说明、未指定产线按产线汇总异常、单台故障诊断。
- material：物料缺口——统计各物料在库/订单扣减/缺口及补货建议。
- storage：堆存风险——按产线统计堆存与剩余空间，标出爆仓风险产线。
- cost：成本动因——单箱成本拆解、占比、驱动因素与异常项。
- supplier：供货商动态——查询 5 家供货商未来数月各物料可用量/可到货日期/紧张度，辅助接单与排产预测。

规则约束：
1. 先用 write_todos 制定处理计划（若任务较复杂）。
2. 根据意图选择并调用对应子 Agent；子 Agent 是无状态的，须在单次指令里提供完整上下文
   （用户问题 + 需要返回的结论要求：简洁、专业、直接给结论）。
3. 属于一般闲聊/不涉及以上领域时，直接回答，不调用子 Agent。
4. 涉及排产变更、设备操作、产线停机等决策，必须在回答末尾提醒：须由具备资质的专业人员确认后执行。
5. 回答使用中文，直接给结论，不要堆砌内部数据结构。"""

_agent_manager = None


def build_agent():
    """构建（或复用）deepagents 主 Agent。未启用或无模型时返回 None。"""
    global _agent_manager
    if not ENABLE_DEEP_AGENTS:
        return None
    if _agent_manager is not None:
        return _agent_manager
    model = get_model()
    if model is None:
        return None
    create_deep_agent = None
    MemorySaver = None
    try:
        from deepagents import create_deep_agent as _cda
        from langgraph.checkpoint.memory import MemorySaver as _ms
        create_deep_agent, MemorySaver = _cda, _ms
    except Exception as e:  # noqa: BLE001
        logger.warning("导入 deepagents 失败，回退规则引擎: %s", e)
        return None

    # 子 Agent 定义（模型继承主 Agent）
    subagents = [
        make_scheduler_agent(),
        make_device_agent(),
        make_material_agent(),
        make_storage_agent(),
        make_cost_agent(),
        make_supplier_agent(),
    ]

    checkpointer = MemorySaver() if MemorySaver else None
    agent_kwargs = dict(
        name="containermind-main",
        model=model,
        system_prompt=MAIN_SYSTEM_PROMPT,
        subagents=subagents,
    )
    if SKILLS_DIR.is_dir():
        agent_kwargs["skills"] = [str(SKILLS_DIR)]
    if checkpointer is not None:
        agent_kwargs["checkpointer"] = checkpointer

    try:
        _agent_manager = create_deep_agent(**agent_kwargs)
    except Exception as e:  # noqa: BLE001
        logger.warning("构建 deepagents 主 Agent 失败，回退规则引擎: %s", e)
        _agent_manager = None
    return _agent_manager


async def chat(message: str, session_id: str = "default", user: str = "anonymous") -> str | None:
    """主 Agent 单轮对话。返回回复文本；失败/未启用时返回 None（调用方回退规则引擎）。"""
    if not ENABLE_DEEP_AGENTS:
        return None
    agent = build_agent()
    if agent is None:
        return None
    config = {"configurable": {"thread_id": session_id or "default"}}
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        # 取最后一条 assistant 消息作为回复
        content = None
        for msg in reversed(result.get("messages") or []):
            if getattr(msg, "type", "") == "ai" or msg.get("type") == "ai":
                content = getattr(msg, "content", None) or msg.get("content")
                break
        if not content:
            content = str(result)
        return content.strip() if isinstance(content, str) else str(content).strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("主 Agent 调用失败，回退规则引擎: %s", e)
        return None