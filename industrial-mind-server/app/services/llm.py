"""大模型客户端（deepseek-v4-flash-0731，OpenAI 兼容协议；未配置 Key 时返回 None，由规则引擎兜底）"""
from __future__ import annotations

import json
import logging
import time

import httpx

from ..config import settings

logger = logging.getLogger("containermind.llm")

INTENT_SYSTEM_PROMPT = """你是一个集装箱制造企业的多智能体意图识别助手。请分析用户输入，判断该调用哪个智能体（意图类型），并抽取结构化信息。

## 智能体与意图类型
- new_order_intent: 智能排产——新订单/意向订单评估、下单
- schedule_query: 智能排产——排产/工令查询（如查某工令排到几号）
- capacity_query: 智能排产——产能查询（如某产线还有多少空位）
- device_query: 设备诊断——设备情况、健康状况、异常、诊断、报警、保养
- material_gap: 物料缺口——物料、库存、缺料、缺口、需补货
- storage_risk: 堆存风险——堆存、爆仓、剩余空间、预堆存、库容
- cost_analysis: 成本动因——成本、单箱、毛利、费用、降本、成本动因
- general_chat: 其他——以上均不匹配的一般对话

## 抽取字段（针对所有意图，尽量抽取）
- line_code: 产线编号（如 PD-D、BS-A、JS-A、JS-B、FX-A）。从用户输入中识别产线，例如「PD-D线」「金山A线」「NH-A线」等；若输入明确提到某种产线写法，原样归一化为对应的标准编号；无法识别则为 null
- work_order_no: 工令/工单号（若有）
- box_type: 箱型（如40HC、20GP、Ener C+等）
- quantity: 数量（台）
- delivery_date: 计划交付日期（YYYY-MM-DD）
- delivery_location: 交付地点
- customer: 客户名称（如有）
- urgency: 紧急程度（如有）

## 输出格式（严格 JSON，不要输出其他内容）
{
  "intent": "capacity_query",
  "confidence": 0.95,
  "extracted_info": {"line_code": "NH-A", "work_order_no": null, "box_type": null,
                     "quantity": null, "delivery_date": null, "delivery_location": null,
                     "customer": null, "urgency": null},
  "missing_fields": [],
  "clarification_needed": false
}"""


async def chat_completion(messages: list[dict], temperature: float = 0.3,
                          json_mode: bool = False, timeout: float = 20.0,
                          scene: str = "", user: str = "", session_id: str = "") -> str | None:
    """调用大模型；失败或未配置时返回 None（调用方需规则引擎兜底）"""
    if not settings.LLM_ENABLED:
        return None
    payload = {"model": settings.LLM_MODEL, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    start = time.time()
    latency_ms = 0
    success = False
    content: str | None = None
    error = ""
    prompt_tokens = completion_tokens = total_tokens = 0
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{settings.LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            total_tokens = int(usage.get("total_tokens") or 0)
            success = True
    except Exception as e:  # noqa: BLE001
        error = str(e)
        logger.warning("LLM 调用失败，使用规则引擎兜底: %s", e)
    finally:
        latency_ms = int((time.time() - start) * 1000)
        _record_call(scene=scene, user=user, session_id=session_id, model=settings.LLM_MODEL,
                     messages=messages, content=content,
                     prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                     total_tokens=total_tokens, latency_ms=latency_ms, success=success, error=error)
    return content


def _record_call(**kwargs) -> None:
    """将一次 LLM 调用写入 model_call_log 表（独立 session，失败不影响主流程）"""
    try:
        from ..database import SessionLocal
        from ..models import ModelCallLog

        db = SessionLocal()
        try:
            db.add(ModelCallLog(
                scene=kwargs.get("scene", ""),
                user=kwargs.get("user", ""),
                session_id=kwargs.get("session_id", ""),
                model=kwargs.get("model", ""),
                prompt=json.dumps(kwargs.get("messages") or [],
                                  ensure_ascii=False, default=str),
                response=(kwargs.get("content") or "")[:20000],
                prompt_tokens=kwargs.get("prompt_tokens") or 0,
                completion_tokens=kwargs.get("completion_tokens") or 0,
                total_tokens=kwargs.get("total_tokens") or 0,
                latency_ms=kwargs.get("latency_ms") or 0,
                success=kwargs.get("success", True),
                error=(kwargs.get("error") or "")[:2000],
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001
        logger.warning("写入模型调用日志失败: %s", e)


async def llm_parse_intent(text: str, user: str = "", session_id: str = "") -> dict | None:
    content = await chat_completion(
        [{"role": "system", "content": INTENT_SYSTEM_PROMPT},
         {"role": "user", "content": text}],
        json_mode=True,
        scene="intent", user=user, session_id=session_id,
    )
    if not content:
        return None
    try:
        data = json.loads(content)
        if isinstance(data.get("extracted_info"), dict):
            ei = data["extracted_info"]
            data["extracted_info"].setdefault("line_code", None)
            data["extracted_info"].setdefault("work_order_no", None)
            data["extracted_info"].setdefault("what_if", False)
        return data
    except (json.JSONDecodeError, KeyError):
        return None
