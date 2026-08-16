"""Agent 对话台：会话与消息管理接口（按用户隔离）"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionCreate(BaseModel):
    title: str = "新会话"


def _current_user(x_username: str | None) -> str:
    return (x_username or "anonymous").strip() or "anonymous"


@router.get("/sessions")
def list_sessions(x_username: str | None = Header(default=None, alias="X-Username"),
                  db: Session = Depends(get_db)):
    """当前用户的会话列表（按最近更新倒序）"""
    user = _current_user(x_username)
    rows = db.query(ChatSession).filter(ChatSession.user == user) \
        .order_by(ChatSession.updated_at.desc()).all()
    return [{"session_id": r.session_id, "title": r.title,
             "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}
            for r in rows]


@router.post("/sessions")
def create_session(body: SessionCreate, x_username: str | None = Header(default=None, alias="X-Username"),
                   db: Session = Depends(get_db)):
    """新建会话"""
    user = _current_user(x_username)
    session_id = uuid.uuid4().hex[:16]
    db.add(ChatSession(session_id=session_id, user=user, title=body.title or "新会话"))
    db.commit()
    return {"session_id": session_id, "title": body.title or "新会话", "user": user}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, x_username: str | None = Header(default=None, alias="X-Username"),
                   db: Session = Depends(get_db)):
    """删除会话（连同其消息）"""
    user = _current_user(x_username)
    sess = db.query(ChatSession).filter(ChatSession.session_id == session_id,
                                        ChatSession.user == user).first()
    if not sess:
        raise HTTPException(404, "会话不存在")
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id,
                                 ChatMessage.user == user).delete()
    db.delete(sess)
    db.commit()
    return {"ok": True}


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str,
                         x_username: str | None = Header(default=None, alias="X-Username"),
                         db: Session = Depends(get_db)):
    """加载某会话的历史消息"""
    user = _current_user(x_username)
    rows = db.query(ChatMessage).filter(ChatMessage.session_id == session_id,
                                        ChatMessage.user == user) \
        .order_by(ChatMessage.id.asc()).all()
    return [{
        "role": m.role,
        "content": m.content,
        "card": m.card,
        "intent_label": m.intent_label,
        "agent": m.agent,
        "created_at": m.created_at.isoformat(),
    } for m in rows]