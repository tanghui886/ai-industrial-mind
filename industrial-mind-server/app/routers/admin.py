"""系统管理接口：用户管理 / 按钮权限管理 / 角色管理 / 菜单配置
（仅管理员 + 具备对应 perm.manage 权限者操作）"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, RoleMenu, RolePermission, User
from ..permissions import (ADMIN_ROLE, MENU_DEFS, PERMISSION_DEFS, all_roles,
                           require_perm, role_menus, role_perms)

router = APIRouter(prefix="/admin", tags=["admin"])


class UserIn(BaseModel):
    username: str
    password: str = "123456"
    display_name: str
    role: str
    phone: str = ""


class UserUpdate(BaseModel):
    display_name: str
    role: str
    phone: str = ""


class PermSaveReq(BaseModel):
    role: str
    perms: list[str]


def _check_role(role: str, db: Session):
    if role not in all_roles(db):
        raise HTTPException(400, f"非法角色：{role}")


@router.get("/users")
def list_users(_: str = Depends(require_perm("user.manage")), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [{"id": u.id, "username": u.username, "display_name": u.display_name,
             "role": u.role, "phone": u.phone, "is_admin": u.role == "管理员"} for u in users]


@router.post("/users")
def create_user(body: UserIn, _: str = Depends(require_perm("user.manage")),
                db: Session = Depends(get_db)):
    _check_role(body.role, db)
    if not body.username.strip():
        raise HTTPException(400, "用户名不能为空")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, f"用户名 {body.username} 已存在")
    db.add(User(username=body.username.strip(), password=body.password or "123456",
                display_name=body.display_name.strip() or body.username.strip(),
                role=body.role, phone=body.phone))
    db.commit()
    return {"ok": True, "message": "用户已创建"}


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, _: str = Depends(require_perm("user.manage")),
                db: Session = Depends(get_db)):
    _check_role(body.role, db)
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    u.display_name = body.display_name.strip() or u.username
    u.role = body.role
    u.phone = body.phone
    db.commit()
    return {"ok": True, "message": "用户已更新"}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, _: str = Depends(require_perm("user.manage")),
                   db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    u.password = "123456"
    db.commit()
    return {"ok": True, "message": f"密码已重置为 123456"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, _: str = Depends(require_perm("user.manage")),
                db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(404, "用户不存在")
    if u.role == "管理员":
        raise HTTPException(400, "管理员账号不可删除")
    db.delete(u)
    db.commit()
    return {"ok": True, "message": "用户已删除"}


# ---------------- 权限管理 ----------------

@router.get("/permissions")
def get_permissions(_: str = Depends(require_perm("perm.manage")),
                    db: Session = Depends(get_db)):
    """返回按钮权限定义 + 各角色当前配置（管理员拥有全部）"""
    roles = all_roles(db)
    return {
        "defs": [{"code": c, "name": n} for c, n in PERMISSION_DEFS.items()],
        "roles": roles,
        "config": {r: sorted(role_perms(r, db)) for r in roles},
    }


@router.put("/permissions")
def save_permissions(body: PermSaveReq, _: str = Depends(require_perm("perm.manage")),
                     db: Session = Depends(get_db)):
    _check_role(body.role, db)
    if body.role == "管理员":
        raise HTTPException(400, "管理员拥有全部权限，无需配置")
    invalid = [c for c in body.perms if c not in PERMISSION_DEFS]
    if invalid:
        raise HTTPException(400, f"非法权限编码：{invalid}")
    db.query(RolePermission).filter(RolePermission.role == body.role).delete()
    for c in sorted(set(body.perms)):
        db.add(RolePermission(role=body.role, perm_code=c))
    db.commit()
    return {"ok": True, "role": body.role, "perms": sorted(set(body.perms)),
            "message": f"角色「{body.role}」权限已更新"}


# ---------------- 角色管理 ----------------

class RoleIn(BaseModel):
    name: str
    description: str = ""


@router.get("/roles")
def list_roles(_: str = Depends(require_perm("role.manage")), db: Session = Depends(get_db)):
    """返回全部角色（含内置与自定义），供角色管理界面展示"""
    return [{"name": r.name, "description": r.description, "is_builtin": r.is_builtin}
            for r in db.query(Role).order_by(Role.id).all()]


@router.post("/roles")
def create_role(body: RoleIn, _: str = Depends(require_perm("role.manage")),
                db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "角色名称不能为空")
    if db.query(Role).filter(Role.name == name).first():
        raise HTTPException(400, f"角色「{name}」已存在")
    db.add(Role(name=name, description=body.description.strip(), is_builtin=False))
    db.commit()
    return {"ok": True, "message": f"角色「{name}」已创建"}


@router.put("/roles/{name}")
def update_role(name: str, body: RoleIn, _: str = Depends(require_perm("role.manage")),
                db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise HTTPException(404, f"角色「{name}」不存在")
    if not role.is_builtin:
        new_name = body.name.strip() or role.name
        if new_name != role.name and db.query(Role).filter(Role.name == new_name).first():
            raise HTTPException(400, f"角色「{new_name}」已存在")
        role.name = new_name
        role.description = body.description.strip() or role.description
    else:
        role.description = body.description.strip() or role.description
    db.commit()
    return {"ok": True, "message": f"角色「{role.name}」已更新"}


@router.delete("/roles/{name}")
def delete_role(name: str, _: str = Depends(require_perm("role.manage")),
                db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise HTTPException(404, f"角色「{name}」不存在")
    if role.is_builtin:
        raise HTTPException(400, f"内置角色「{name}」不可删除")
    if db.query(User).filter(User.role == name).first():
        raise HTTPException(400, f"仍有用户使用角色「{name}」，请先调整后再删除")
    db.query(RolePermission).filter(RolePermission.role == name).delete()
    db.query(RoleMenu).filter(RoleMenu.role == name).delete()
    db.delete(role)
    db.commit()
    return {"ok": True, "message": f"角色「{name}」已删除"}


# ---------------- 菜单配置 ----------------

class MenuSaveReq(BaseModel):
    role: str
    menus: list[str]


@router.get("/menus")
def get_menus(_: str = Depends(require_perm("role.manage")), db: Session = Depends(get_db)):
    """返回菜单定义 + 各角色当前可见菜单配置（管理员拥有全部）"""
    return {
        "defs": [{"code": c, "name": n} for c, n in MENU_DEFS.items()],
        "roles": all_roles(db),
        "config": {r: sorted(role_menus(r, db)) for r in all_roles(db)},
    }


@router.put("/menus")
def save_menus(body: MenuSaveReq, _: str = Depends(require_perm("role.manage")),
               db: Session = Depends(get_db)):
    _check_role(body.role, db)
    if body.role == ADMIN_ROLE:
        raise HTTPException(400, "管理员拥有全部菜单，无需配置")
    invalid = [c for c in body.menus if c not in MENU_DEFS]
    if invalid:
        raise HTTPException(400, f"非法菜单编码：{invalid}")
    db.query(RoleMenu).filter(RoleMenu.role == body.role).delete()
    for c in sorted(set(body.menus)):
        db.add(RoleMenu(role=body.role, menu_code=c))
    db.commit()
    return {"ok": True, "role": body.role, "menus": sorted(set(body.menus)),
            "message": f"角色「{body.role}」菜单已更新"}
