"""权限控制：基于 X-Username header 识别登录用户
- 按钮权限（perm_code）可配置，存放在 role_permission 表，管理员可在「权限管理」维护
- 未登录（无 X-Username 头）一律放行，保持对冒烟测试 / 旧调用兼容
- 管理员角色拥有全部按钮权限
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Menu, RoleMenu, RolePermission, User

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
    "menu.manage": "菜单管理",
}

# 默认菜单树定义（种子数据）：前端导航据此渲染，管理员可在「菜单管理」维护
DEFAULT_MENU_TREE: list[dict] = [
    # 顶级菜单
    {"code": "dashboard", "name": "产线总览", "path": "/pc/dashboard", "parent_code": "",
     "icon": "LayoutDashboard", "sort_order": 10, "admin_only": False, "is_builtin": True},
    {"code": "agent", "name": "Agent 对话台", "path": "/pc/agent", "parent_code": "",
     "icon": "BotMessageSquare", "sort_order": 20, "admin_only": False, "is_builtin": True},
    {"code": "planning", "name": "排产工作台", "path": "/pc/planning", "parent_code": "",
     "icon": "CalendarDays", "sort_order": 30, "admin_only": False, "is_builtin": True},
    {"code": "approval", "name": "审批工作台", "path": "/pc/approval", "parent_code": "",
     "icon": "ClipboardCheck", "sort_order": 40, "admin_only": False, "is_builtin": True},
    # 物料管理（分组）
    {"code": "box", "name": "物料管理", "path": "", "parent_code": "",
     "icon": "Boxes", "sort_order": 50, "admin_only": False, "is_builtin": True},
    {"code": "material", "name": "物料维护", "path": "/pc/material", "parent_code": "box",
     "icon": "Boxes", "sort_order": 51, "admin_only": False, "is_builtin": True},
    {"code": "supplier", "name": "供货商动态", "path": "/pc/supplier", "parent_code": "box",
     "icon": "BadgeMinus", "sort_order": 52, "admin_only": False, "is_builtin": True},
    # 堆存管理
    {"code": "storage", "name": "堆存管理", "path": "/pc/storage", "parent_code": "",
     "icon": "Warehouse", "sort_order": 60, "admin_only": False, "is_builtin": True},
    # 设备管理（分组）
    {"code": "device", "name": "设备管理", "path": "", "parent_code": "",
     "icon": "Cpu", "sort_order": 70, "admin_only": False, "is_builtin": True},
    {"code": "device-screen", "name": "设备大屏", "path": "/pc/device", "parent_code": "device",
     "icon": "Cpu", "sort_order": 71, "admin_only": False, "is_builtin": True},
    {"code": "device-manage", "name": "设备明细", "path": "/pc/device-manage", "parent_code": "device",
     "icon": "Cpu", "sort_order": 72, "admin_only": False, "is_builtin": True},
    # 成本管理（分组）
    {"code": "cost", "name": "成本管理", "path": "", "parent_code": "",
     "icon": "BadgeDollarSign", "sort_order": 80, "admin_only": False, "is_builtin": True},
    {"code": "cost-screen", "name": "成本动因大屏", "path": "/pc/cost", "parent_code": "cost",
     "icon": "BadgeDollarSign", "sort_order": 81, "admin_only": False, "is_builtin": True},
    {"code": "cost-manage", "name": "各维度数据管理", "path": "/pc/cost-manage", "parent_code": "cost",
     "icon": "BadgeDollarSign", "sort_order": 82, "admin_only": False, "is_builtin": True},
    {"code": "cost-baseline", "name": "基准配置", "path": "/pc/cost-baseline", "parent_code": "cost",
     "icon": "BadgeDollarSign", "sort_order": 83, "admin_only": False, "is_builtin": True},
    {"code": "cost-analyze", "name": "成本动因分析", "path": "/pc/cost-analyze", "parent_code": "cost",
     "icon": "BadgeDollarSign", "sort_order": 84, "admin_only": False, "is_builtin": True},
    {"code": "cost-records", "name": "分析明细", "path": "/pc/cost-records", "parent_code": "cost",
     "icon": "BadgeDollarSign", "sort_order": 85, "admin_only": False, "is_builtin": True},
    {"code": "cost-material-detail", "name": "物料明细", "path": "/pc/cost-material-detail", "parent_code": "cost",
     "icon": "BadgeDollarSign", "sort_order": 86, "admin_only": False, "is_builtin": True},
    # 系统设置（分组，仅管理员）
    {"code": "setting", "name": "系统设置", "path": "", "parent_code": "",
     "icon": "Settings", "sort_order": 90, "admin_only": True, "is_builtin": True},
    {"code": "user", "name": "用户管理", "path": "/pc/users", "parent_code": "setting",
     "icon": "Users", "sort_order": 91, "admin_only": True, "is_builtin": True},
    {"code": "perm", "name": "权限管理", "path": "/pc/permissions", "parent_code": "setting",
     "icon": "ShieldCheck", "sort_order": 92, "admin_only": True, "is_builtin": True},
    {"code": "role", "name": "角色管理", "path": "/pc/roles", "parent_code": "setting",
     "icon": "UserCog", "sort_order": 93, "admin_only": True, "is_builtin": True},
    {"code": "llm-log", "name": "模型调用记录", "path": "/pc/llm-log", "parent_code": "setting",
     "icon": "BotMessageSquare", "sort_order": 94, "admin_only": True, "is_builtin": True},
    {"code": "menu", "name": "菜单管理", "path": "/pc/menu-manage", "parent_code": "setting",
     "icon": "ListTree", "sort_order": 95, "admin_only": True, "is_builtin": True},
]

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
    "管理员": [d["code"] for d in DEFAULT_MENU_TREE],
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


def menu_defs(db: Session) -> list[dict]:
    """返回全部菜单定义（含层级字段），供「菜单管理」页面维护；DB 为空时回退种子数据"""
    rows = db.query(Menu).order_by(Menu.sort_order, Menu.id).all()
    if rows:
        return [_menu_dict(m) for m in rows]
    return [{**d} for d in DEFAULT_MENU_TREE]


def _menu_dict(m) -> dict:
    return {
        "code": m.code,
        "name": m.name,
        "path": m.path,
        "parent_code": m.parent_code,
        "icon": m.icon,
        "sort_order": m.sort_order,
        "admin_only": m.admin_only,
        "is_builtin": m.is_builtin,
    }


def build_menu_tree(defs: list[dict], codes: set[str] | None = None) -> list[dict]:
    """根据菜单定义与可见编码集合构建菜单树（含 children，按 sort_order 排序）。
    - codes 为空表示全部可见
    - 父子关系通过 parent_code 关联；父节点即使不在 codes 中，只要有可见子节点也会保留
    """
    by_code: dict[str, dict] = {d["code"]: {**d, "children": []} for d in defs}
    roots: list[dict] = []
    for d in defs:
        node = by_code[d["code"]]
        parent = by_code.get(d["parent_code"])
        if parent is not None and parent is not node:
            parent["children"].append(node)
        else:
            roots.append(node)

    def _sort(nodes: list[dict]):
        nodes.sort(key=lambda n: (n["sort_order"], n["code"]))
        for n in nodes:
            _sort(n["children"])

    _sort(roots)

    if codes is not None:
        def _filter(nodes: list[dict]) -> list[dict]:
            kept = []
            for n in nodes:
                n["children"] = _filter(n["children"])
                if n["code"] in codes or n["children"]:
                    kept.append(n)
            return kept
        roots = _filter(roots)
    return roots


def role_menu_tree(role: str, db: Session) -> list[dict]:
    """返回角色可见的菜单树（含层级），供前端动态渲染导航；管理员拥有全部（含 admin_only）"""
    defs = menu_defs(db)
    if role == ADMIN_ROLE:
        return build_menu_tree(defs)
    codes = set(role_menus(role, db))
    # 非管理员不可见 admin_only 菜单（如系统设置下的管理菜单）
    codes &= {d["code"] for d in defs if not d["admin_only"]}
    return build_menu_tree(defs, codes)


def role_menus(role: str, db: Session) -> list[str]:
    """返回角色可见菜单编码列表；管理员拥有全部；未配置时回退默认值"""
    if role == ADMIN_ROLE:
        return [d["code"] for d in menu_defs(db)]
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
