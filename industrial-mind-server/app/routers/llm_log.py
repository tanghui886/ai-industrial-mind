"""模型调用日志查询接口"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ModelCallLog

router = APIRouter(prefix="/llm-log", tags=["llm_log"])


@router.get("/records")
def llm_log_records(
    scene: str | None = None,
    user: str | None = None,
    session_id: str | None = None,
    success: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """查询模型调用记录（按场景、用户、会话、时间、状态过滤，分页返回）"""
    q = db.query(ModelCallLog)
    if scene:
        q = q.filter(ModelCallLog.scene == scene)
    if user:
        q = q.filter(ModelCallLog.user == user)
    if session_id:
        q = q.filter(ModelCallLog.session_id == session_id)
    if success is not None:
        q = q.filter(ModelCallLog.success == success)
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            q = q.filter(ModelCallLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            q = q.filter(ModelCallLog.created_at <= dt)
        except ValueError:
            pass
    total = q.count()
    rows = q.order_by(ModelCallLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "scene": r.scene,
                "user": r.user,
                "session_id": r.session_id,
                "model": r.model,
                "prompt": r.prompt[:500],
                "response": r.response[:1000],
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "total_tokens": r.total_tokens,
                "latency_ms": r.latency_ms,
                "success": r.success,
                "error": r.error[:200],
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }