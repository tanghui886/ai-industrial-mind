"""认证接口：账号密码 / 手机验证码（演示版，统一密码 123456，验证码 123456）"""
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..permissions import role_menu_tree, role_menus, role_perms

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginReq(BaseModel):
    username: str
    password: str


class SmsLoginReq(BaseModel):
    phone: str
    code: str


def _token(user: User, db: Session) -> dict:
    return {
        "token": uuid.uuid4().hex,
        "user": {"username": user.username, "display_name": user.display_name,
                 "role": user.role, "phone": user.phone},
        "perms": sorted(role_perms(user.role, db)),
        "menus": sorted(role_menus(user.role, db)),
        "menu_tree": role_menu_tree(user.role, db),
    }


@router.post("/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or req.password != "123456":
        raise HTTPException(status_code=401, detail="用户名或密码错误（演示账号密码均为 123456）")
    return _token(user, db)


@router.post("/sms-login")
def sms_login(req: SmsLoginReq, db: Session = Depends(get_db)):
    if req.code != "123456":
        raise HTTPException(status_code=401, detail="验证码错误（演示验证码为 123456）")
    user = db.query(User).filter(User.phone == req.phone).first()
    if not user:
        raise HTTPException(status_code=401, detail="该手机号未注册")
    return _token(user, db)


@router.get("/me")
def me(x_username: str | None = Header(default=None, alias="X-Username"),
       db: Session = Depends(get_db)):
    """返回当前登录用户信息 + 按钮权限，供前端渲染/刷新权限"""
    if not x_username:
        raise HTTPException(status_code=401, detail="未登录")
    user = db.query(User).filter(User.username == x_username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"username": user.username, "display_name": user.display_name,
            "role": user.role, "phone": user.phone,
            "perms": sorted(role_perms(user.role, db)),
            "menus": sorted(role_menus(user.role, db)),
            "menu_tree": role_menu_tree(user.role, db)}


@router.post("/refresh")
def refresh():
    return {"token": uuid.uuid4().hex}
