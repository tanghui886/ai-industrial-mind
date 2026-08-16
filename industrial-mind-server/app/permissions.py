"""权限控制：基于 X-Username header 识别登录用户
- 按钮权限（perm_code）可配置，存放在 role_permission 表，管理员可在「权限管理」维护
- 未登录（无 X-Username 头）一律放行，保持对冒烟测试 / 旧调用兼容
- 管理员角色拥有全部按钮权限
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import RoleMenu, RolePermission, User

# 按钮权限定义：perm_code -> 中文名（管理端展示 + 默认授权）
PERMISSION_DEFS: dict[str, str] = {
    "workorder.add": "添加工令",
    "workorder.edit": "编辑工令",
    "workorder.delete": "删除工令",
    "planning.schedule": "排产（确认/甘特）",
    "planning.smart": "智能排产",
    "planning.calendar": "排班配置",
    "approval.approve": "审批通过",
    "approval.reject": "审批驳回",
    "approval.transfer": "审批转交",
    "material.manage": "物料维护",
    "user.manage": "用户管理",
    "perm.manage": "权限管理",
    "role.manage": "角色管理",
}

# 菜单定义：menu_code -> 中文名（角色可配置可见菜单）
MENU_DEFS: dict[str, str] = {
    "dashboard": "产线总览",
    "planning": "排产工作台",
    "agent": "Agent 对话台",
    "approval": "审批工作台",
    "material": "物料维护",
    "device": "设备管理",
    "storage": "堆存管理",
    "cost": "成本动因",
    "user": "用户管理",
    "perm": "权限管理",
    "role": "角色管理",
}

# 角色 -> 默认按钮权限（角色尚未配置任何权限时兜底）
DEFAULT_PERMS: dict[str, list[str]] = {
    "业务经理": ["workorder.add", "workorder.edit", "workorder.delete"],
    "计划员": ["workorder.edit", "workorder.delete",
               "planning.schedule", "planning.smart", "planning.calendar"],
    "生产主管": ["approval.approve", "approval.reject", "approval.transfer"],
    "设备主管": ["approval.approve", "approval.reject", "approval.transfer"],
    "采购专员": [],
    "财务专员": [],
    "物料管理员": ["material.manage"],
}

# 角色 -> 默认可见菜单（角色尚未配置任何菜单时兜底）
DEFAULT_MENUS: dict[str, list[str]] = {
    "管理员": list(MENU_DEFS),
    "业务经理": ["dashboard", "planning", "agent", "approval", "storage"],
    "计划员": ["dashboard", "planning", "agent", "approval", "storage"],
    "生产主管": ["dashboard", "approval", "storage"],
    "设备主管": ["dashboard", "approval", "device", "storage"],
    "采购专员": ["dashboard", "cost"],
    "财务专员": ["dashboard", "cost"],
    "物料管理员": ["dashboard", "material"],
}

# 用户角色 -> 权限组（用于数据可见范围等粗粒度过滤）
ROLE_GROUP = {
    "业务经理": "business",
    "计划员": "planner",
    "生产主管": "approver",
    "设备主管": "approver",
    "采购专员": "viewer",
    "财务专员": "viewer",
    "物料管理员": "viewer",
    "管理员": "admin",
}

# 内置角色（角色管理中的预设角色；自定义角色存于 role 表）
BUILTIN_ROLES = ["管理员", "业务经理", "计划员", "生产主管",
                 "设备主管", "采购专员", "财务专员", "物料管理员"]

ADMIN_ROLE = "管理员"


def all_roles(db: Session) -> list[str]:
    """返回全部可选角色（role 表 + 内置角色兜底），供用户/权限/角色管理下拉使用"""
    from .models import Role
    rows = db.query(Role).order_by(Role.id).all()
    if rows:
        return [r.name for r in rows]
    return BUILTIN_ROLES


def user_role(username: str | None, db: Session) -> str:
    """按用户名返回角色；未登录/不存在返回空串"""
    if not username:
        return ""
    u = db.query(User).filter(User.username == username).first()
    return u.role if u else ""


def role_group(role: str) -> str:
    return ROLE_GROUP.get(role, "viewer")


def role_perms(role: str, db: Session) -> set[str]:
    """返回角色实际拥有的按钮权限编码集合；管理员拥有全部；未配置时回退默认值"""
    if role == ADMIN_ROLE:
        return set(PERMISSION_DEFS)
    rows = db.query(RolePermission).filter(RolePermission.role == role).all()
    if rows:
        return {r.perm_code for r in rows}
    return set(DEFAULT_PERMS.get(role, []))


def role_menus(role: str, db: Session) -> list[str]:
    """返回角色可见菜单编码列表；管理员拥有全部；未配置时回退默认值"""
    if role == ADMIN_ROLE:
        return list(MENU_DEFS)
    rows = db.query(RoleMenu).filter(RoleMenu.role == role).all()
    if rows:
        return [r.menu_code for r in rows]
    return list(DEFAULT_MENUS.get(role, []))


def get_current_group(x_username: str | None = Header(default=None, alias="X-Username"),
                      db: Session = Depends(get_db)) -> str:
    """返回当前登录用户的权限组（未提供 header 时返回 'anonymous' 表示兼容放行）"""
    if not x_username:
        return "anonymous"
    return role_group(user_role(x_username, db))


def get_current_role(x_username: str | None = Header(default=None, alias="X-Username"),
                     db: Session = Depends(get_db)) -> str:
    """返回当前登录用户角色（未提供 header 时返回 'anonymous'）"""
    if not x_username:
        return "anonymous"
    return user_role(x_username, db) or "anonymous"


def get_current_perms(x_username: str | None = Header(default=None, alias="X-Username"),
                      db: Session = Depends(get_db)) -> set[str] | None:
    """返回当前用户按钮权限集合；未登录返回 None（表示兼容放行）"""
    if not x_username:
        return None
    return role_perms(user_role(x_username, db), db)


def require_perm(*codes: str):
    """要求当前用户拥有任一给定按钮权限编码；管理员放行；未登录放行（保持兼容）"""
    def dep(perms: set[str] | None = Depends(get_current_perms)):
        if perms is None:            # 未登录
            return perms
        if any(c in perms for c in codes):
            return perms
        raise HTTPException(403, "无权限执行该操作")
    return dep


def require_role(*roles: str):
    """要求当前用户角色属于给定角色之一；未登录放行（保持兼容）"""
    def dep(role: str = Depends(get_current_role)):
        if role == "anonymous":
            return role
        if role not in roles:
            raise HTTPException(403, "无权限执行该操作")
        return role
    return dep
