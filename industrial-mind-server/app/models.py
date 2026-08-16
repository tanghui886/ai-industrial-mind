"""ORM 数据模型（对齐方案 v6 数据表设计）"""
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Factory(Base):
    __tablename__ = "factory"
    id: Mapped[int] = mapped_column(primary_key=True)
    factory_code: Mapped[str] = mapped_column(String(16), unique=True)
    factory_name: Mapped[str] = mapped_column(String(64))


class ProductionLine(Base):
    __tablename__ = "production_line"
    id: Mapped[int] = mapped_column(primary_key=True)
    line_code: Mapped[str] = mapped_column(String(16), unique=True)
    line_name: Mapped[str] = mapped_column(String(64))
    factory_code: Mapped[str] = mapped_column(String(16))
    line_type: Mapped[str] = mapped_column(String(32))          # 特种箱/标准箱
    daily_teu_capacity: Mapped[int] = mapped_column(Integer)    # 产线日产能（TEU/天）
    storage_capacity: Mapped[int] = mapped_column(Integer, default=0)  # 堆存总容纳（台）
    storage_units: Mapped[int] = mapped_column(Integer, default=0)     # 当前堆存量（台）


class BoxType(Base):
    __tablename__ = "box_type"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    daily_capacity_min: Mapped[int] = mapped_column(Integer)
    daily_capacity_max: Mapped[int] = mapped_column(Integer)
    daily_capacity_std: Mapped[int] = mapped_column(Integer)
    teu_factor: Mapped[float] = mapped_column(Numeric(4, 2))
    cteu_factor: Mapped[float] = mapped_column(Numeric(4, 2))


class WorkCalendarDay(Base):
    """排产日历覆盖记录（每日排班：0 表示休息日，>0 表示当日产线日产能 TEU）"""
    __tablename__ = "work_calendar"
    id: Mapped[int] = mapped_column(primary_key=True)
    line_code: Mapped[str] = mapped_column(String(16), index=True)
    cal_date: Mapped[date] = mapped_column(Date, index=True)
    is_workday: Mapped[bool] = mapped_column(Boolean)
    planned_hours: Mapped[int] = mapped_column(Integer)         # 8 / 5.5 / 0
    daily_capacity: Mapped[int] = mapped_column(Integer, default=0)  # 当日日产能 TEU，0=休息日
    note: Mapped[str] = mapped_column(String(128), default="")


class SchedulePlan(Base):
    __tablename__ = "schedule_plan"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), unique=True)
    plan_month: Mapped[str] = mapped_column(String(7), index=True)
    factory_code: Mapped[str] = mapped_column(String(16))
    line_code: Mapped[str] = mapped_column(String(16), index=True)
    work_order_no: Mapped[str] = mapped_column(String(64), index=True)
    order_confirm_no: Mapped[str] = mapped_column(String(64), default="")
    contract_no: Mapped[str] = mapped_column(String(64), default="")
    customer: Mapped[str] = mapped_column(String(128))
    box_type: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[int] = mapped_column(Integer)
    teu: Mapped[int] = mapped_column(Integer)
    cteu: Mapped[int] = mapped_column(Integer, default=0)
    serial_no: Mapped[str] = mapped_column(String(128), default="")
    production_deadline: Mapped[str] = mapped_column(String(64), default="按时")
    delivery_status: Mapped[str] = mapped_column(String(64), default="")
    order_source: Mapped[str] = mapped_column(String(16), default="自接单")   # 自接单/总部
    trade_type: Mapped[str] = mapped_column(String(16), default="外贸")       # 内贸/外贸
    delivery_location: Mapped[str] = mapped_column(String(128), default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    daily_capacity: Mapped[int] = mapped_column(Integer)
    daily_planned_qty: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    order_type: Mapped[str] = mapped_column(String(16), default="批量")       # 样箱/批量/预排/借用/火烧/研发/小批量
    is_cross_month: Mapped[bool] = mapped_column(Boolean, default=False)
    cross_month_part: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft/pending_approval/confirmed/cancelled/completed
    version: Mapped[int] = mapped_column(Integer, default=1)
    source: Mapped[str] = mapped_column(String(16), default="manual")         # manual/smart/mobile
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    approved_by: Mapped[str] = mapped_column(String(64), default="")
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ScheduleDaily(Base):
    __tablename__ = "schedule_daily"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), index=True)
    work_order_no: Mapped[str] = mapped_column(String(64))
    line_code: Mapped[str] = mapped_column(String(16), index=True)
    schedule_date: Mapped[date] = mapped_column(Date, index=True)
    planned_qty: Mapped[int] = mapped_column(Integer)
    teu: Mapped[int] = mapped_column(Integer, default=0)
    is_workday: Mapped[bool] = mapped_column(Boolean, default=True)
    day_of_week: Mapped[str] = mapped_column(String(4), default="")


class IntentionOrder(Base):
    __tablename__ = "intention_order"
    id: Mapped[int] = mapped_column(primary_key=True)
    intention_id: Mapped[str] = mapped_column(String(64), unique=True)
    source: Mapped[str] = mapped_column(String(16), default="mobile")
    input_text: Mapped[str] = mapped_column(Text, default="")
    box_type: Mapped[str] = mapped_column(String(32), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    delivery_location: Mapped[str] = mapped_column(String(128), default="")
    customer: Mapped[str] = mapped_column(String(128), default="")
    teu: Mapped[int] = mapped_column(Integer, default=0)
    schedule_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/confirmed/converted/cancelled
    converted_order_id: Mapped[str] = mapped_column(String(64), default="")
    created_by: Mapped[str] = mapped_column(String(64), default="张业务")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Approval(Base):
    __tablename__ = "approval"
    id: Mapped[int] = mapped_column(primary_key=True)
    approval_no: Mapped[str] = mapped_column(String(64), unique=True)
    approval_type: Mapped[str] = mapped_column(String(32))       # 排产变更/紧急维修/采购申请/成本分摊/样箱插单
    title: Mapped[str] = mapped_column(String(256))
    priority: Mapped[str] = mapped_column(String(16), default="普通")  # 紧急/高优先级/普通
    applicant: Mapped[str] = mapped_column(String(64))
    applicant_role: Mapped[str] = mapped_column(String(32), default="")
    submitted_at: Mapped[str] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending/approved/rejected
    target_type: Mapped[str] = mapped_column(String(32), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    affect_lines: Mapped[str] = mapped_column(String(128), default="")
    expect_effect_time: Mapped[str] = mapped_column(String(64), default="")
    risk_level: Mapped[str] = mapped_column(String(16), default="中风险")
    related_agent: Mapped[str] = mapped_column(String(64), default="")
    need_countersign: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)      # reason/plan_compare/impacts/attachments/timeline


class Device(Base):
    __tablename__ = "device"
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    line_code: Mapped[str] = mapped_column(String(16))
    health: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))              # 正常/预警/警告/故障
    rul_hours: Mapped[int] = mapped_column(Integer, default=0)
    rul_note: Mapped[str] = mapped_column(String(128), default="")


class Alert(Base):
    __tablename__ = "alert"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_time: Mapped[str] = mapped_column(String(16))
    source_agent: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))               # 严重/警告/提示
    message: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16))              # 处理中/待确认/已关闭


class Material(Base):
    __tablename__ = "material"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    factory: Mapped[str] = mapped_column(String(16), default="DFQD")   # 所属工厂
    unit: Mapped[str] = mapped_column(String(16), default="")          # 物料单位（吨/箱/张/套）
    stock_note: Mapped[str] = mapped_column(String(128), default="")
    in_stock_units: Mapped[int] = mapped_column(Integer, default=0)          # 在库物料总量
    order_deducted_units: Mapped[int] = mapped_column(Integer, default=0)    # 订单扣减量
    gap_units: Mapped[int] = mapped_column(Integer, default=0)               # 缺口量
    support_units: Mapped[int] = mapped_column(Integer, default=0)           # 转换台数（20'当量）
    in_transit_units: Mapped[int] = mapped_column(Integer, default=0)        # 在途量
    purchase_units: Mapped[int] = mapped_column(Integer, default=0)          # 采购量
    arrival_date: Mapped[date] = mapped_column(Date, nullable=True)          # 采购到货日期
    status: Mapped[str] = mapped_column(String(16), default="充足")  # 充足/需补货/预警


class Notification(Base):
    __tablename__ = "notification"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_name: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text, default="")
    ntype: Mapped[str] = mapped_column(String(16), default="系统")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password: Mapped[str] = mapped_column(String(64), default="123456")
    display_name: Mapped[str] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32))                # 管理员/业务经理/计划员/设备主管/采购专员/财务专员/生产主管
    phone: Mapped[str] = mapped_column(String(16), default="")


class RolePermission(Base):
    """角色按钮权限配置：某角色拥有哪些按钮权限编码（perm_code）"""
    __tablename__ = "role_permission"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    perm_code: Mapped[str] = mapped_column(String(64))
    __table_args__ = (UniqueConstraint("role", "perm_code", name="uq_role_perm"),)


class Role(Base):
    """系统角色：管理员可在「角色管理」维护，支持自定义角色"""
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    description: Mapped[str] = mapped_column(String(128), default="")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)


class RoleMenu(Base):
    """角色-菜单配置：某角色可见哪些菜单（menu_code）"""
    __tablename__ = "role_menu"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    menu_code: Mapped[str] = mapped_column(String(32))
    __table_args__ = (UniqueConstraint("role", "menu_code", name="uq_role_menu"),)


class MonthlyPlanTarget(Base):
    """月度计划产能目标（TEU），用于产能汇总展示"""
    __tablename__ = "monthly_plan_target"
    id: Mapped[int] = mapped_column(primary_key=True)
    line_code: Mapped[str] = mapped_column(String(16), index=True)
    plan_month: Mapped[str] = mapped_column(String(7), index=True)
    plan_teu: Mapped[int] = mapped_column(Integer)


class CostBaseline(Base):
    """成本动因明细基准配置：按 同客户 + 同箱型 维度设置基准动因因子

    customer 为空字符串表示「无客户」基线（任意客户同箱型的兜底基准）。
    """
    __tablename__ = "cost_baseline"
    __table_args__ = (UniqueConstraint("customer", "box_type", name="uq_cost_baseline"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    customer: Mapped[str] = mapped_column(String(128), default="")
    box_type: Mapped[str] = mapped_column(String(32))
    source_work_order_no: Mapped[str] = mapped_column(String(64), default="")
    remark: Mapped[str] = mapped_column(String(255), default="")
    factors: Mapped[list] = mapped_column(JSON, default=list)   # [{key, dimension, scene, driver, unit, value}]
    created_by: Mapped[str] = mapped_column(String(64), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class CostAnalysis(Base):
    """成本动因分析结果：按最小工令维度保存（一个工令一条记录，重复分析覆盖更新）"""
    __tablename__ = "cost_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_no: Mapped[str] = mapped_column(String(64), index=True)
    customer: Mapped[str] = mapped_column(String(128), default="")
    box_type: Mapped[str] = mapped_column(String(32))
    baseline_kind: Mapped[str] = mapped_column(String(32), default="")
    deltas: Mapped[list] = mapped_column(JSON, default=list)     # [{dimension, scene, driver, unit, value, baseline, delta, delta_pct}]
    llm_analysis: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(String(16), default="all")  # work_order/customer/box_type/all
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ModelCallLog(Base):
    """模型调用记录：记录每次 LLM 调用的场景、输入、输出与 token 使用情况"""
    __tablename__ = "model_call_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    scene: Mapped[str] = mapped_column(String(32), default="")          # 调用场景：intent/refine/cost_analysis 等
    user: Mapped[str] = mapped_column(String(64), default="", index=True)   # 发起调用的用户
    session_id: Mapped[str] = mapped_column(String(64), default="", index=True)  # 会话ID
    model: Mapped[str] = mapped_column(String(64), default="")
    prompt: Mapped[str] = mapped_column(Text, default="")               # 输入（消息序列）
    response: Mapped[str] = mapped_column(Text, default="")             # 输出内容
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class ChatSession(Base):
    """Agent 对话台：会话（按用户隔离，一个用户可有多个会话）"""
    __tablename__ = "chat_session"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)   # 业务会话ID
    user: Mapped[str] = mapped_column(String(64), index=True)         # 创建者用户名
    title: Mapped[str] = mapped_column(String(128), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ChatMessage(Base):
    """Agent 对话台：会话内消息记录"""
    __tablename__ = "chat_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(16))                    # user/agent
    content: Mapped[str] = mapped_column(Text, default="")           # 文本内容
    card: Mapped[dict] = mapped_column(JSON, default=dict)           # 结构化卡片（可选）
    intent_label: Mapped[str] = mapped_column(String(64), default="")
    agent: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
