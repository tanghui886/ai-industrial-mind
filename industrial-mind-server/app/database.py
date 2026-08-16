"""数据库连接与会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# SQLite：确保数据库文件所在目录存在（引擎创建前执行，避免 unable to open database file）
if settings.DATABASE_URL.startswith("sqlite:///"):
    _db_path = settings.DATABASE_URL.split("///", 1)[1]
    if _db_path and _db_path != ":memory:":
        from pathlib import Path

        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  确保模型注册
    Base.metadata.create_all(engine)
    _migrate()


def _migrate():
    """轻量迁移：为已存在的表补齐新增列（SQLite ALTER TABLE ADD COLUMN）"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if insp.has_table("work_calendar"):
        cols = {c["name"] for c in insp.get_columns("work_calendar")}
        if "daily_capacity" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE work_calendar ADD COLUMN daily_capacity INTEGER DEFAULT 0"))

    # 旧版 chat_session 表结构（含 messages 列、缺 user 列）需重建为当前结构
    if insp.has_table("chat_session"):
        cols = {c["name"] for c in insp.get_columns("chat_session")}
        if "user" not in cols:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE chat_session"))
            # 重建（含 chat_message 若同样为旧结构）
            if insp.has_table("chat_message"):
                cols_msg = {c["name"] for c in insp.get_columns("chat_message")}
                if "user" not in cols_msg:
                    with engine.begin() as conn:
                        conn.execute(text("DROP TABLE chat_message"))
            Base.metadata.create_all(engine)

    # model_call_log 补齐 user / session_id 列（旧表无该列，create_all 不会新增）
    if insp.has_table("model_call_log"):
        cols = {c["name"] for c in insp.get_columns("model_call_log")}
        with engine.begin() as conn:
            if "user" not in cols:
                conn.execute(text("ALTER TABLE model_call_log ADD COLUMN user VARCHAR(64) DEFAULT ''"))
            if "session_id" not in cols:
                conn.execute(text("ALTER TABLE model_call_log ADD COLUMN session_id VARCHAR(64) DEFAULT ''"))

    # material 补齐 工厂/数量统计 列（旧表无该列，create_all 不会新增）
    if insp.has_table("material"):
        cols = {c["name"] for c in insp.get_columns("material")}
        adds = {
            "factory": "VARCHAR(16) DEFAULT 'DFQD'",
            "unit": "VARCHAR(16) DEFAULT ''",
            "in_stock_units": "INTEGER DEFAULT 0",
            "order_deducted_units": "INTEGER DEFAULT 0",
            "gap_units": "INTEGER DEFAULT 0",
            "purchase_units": "INTEGER DEFAULT 0",
        }
        with engine.begin() as conn:
            for col, ddl in adds.items():
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE material ADD COLUMN {col} {ddl}"))

    # production_line 补齐 堆存 列（旧表无该列，create_all 不会新增）
    if insp.has_table("production_line"):
        cols = {c["name"] for c in insp.get_columns("production_line")}
        with engine.begin() as conn:
            if "storage_capacity" not in cols:
                conn.execute(text("ALTER TABLE production_line ADD COLUMN storage_capacity INTEGER DEFAULT 0"))
            if "storage_units" not in cols:
                conn.execute(text("ALTER TABLE production_line ADD COLUMN storage_units INTEGER DEFAULT 0"))
