"""ContainerMind 全局配置（基于 config.yaml 多环境：dev/sit/uat/prod）"""
import os
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent  # app 目录

# 环境：由 run.py <env> 参数设置 APP_ENV，缺省 dev
ENV = os.getenv("APP_ENV", "dev").lower()


def _load_config(env: str) -> dict:
    yaml_file = CONFIG_DIR / "config.yaml"
    if not yaml_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {yaml_file}")
    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or {}
    common = data.get("app", {}) or {}
    env_cfg = data.get(env, {}) or {}
    merged = {**common, **env_cfg}
    # 展开 {base_dir} 占位符为服务端根目录
    return {k: (str(v).replace("{base_dir}", str(BASE_DIR)) if isinstance(v, str) else v)
            for k, v in merged.items()}


_config = _load_config(ENV)


class Settings:
    APP_NAME: str = _config.get("app_name", "ContainerMind API")
    APP_DESC: str = _config.get("app_description", "集装箱制造业工业Agent协同系统 · 后端服务")
    API_PREFIX: str = _config.get("api_prefix", "/api/v1")
    HOST: str = _config.get("host", "0.0.0.0")
    PORT: int = int(_config.get("port", 8000))

    # 数据库：默认 SQLite（免安装），prod 等环境可切换 MySQL 8.0
    DATABASE_URL: str = _config.get(
        "database", f"sqlite:///{(BASE_DIR / 'data' / 'containermind.db').as_posix()}"
    )

    # 大模型（可选）：OpenAI 兼容协议；未配置时使用内置规则引擎
    LLM_BASE_URL: str = _config.get("llm_base_url", "https://api.deepseek.com/v1")
    LLM_API_KEY: str = _config.get("llm_api_key", "")
    LLM_MODEL: str = _config.get("llm_model", "deepseek-v4-flash-0731")

    @property
    def LLM_ENABLED(self) -> bool:
        return bool(self.LLM_API_KEY)


settings = Settings()