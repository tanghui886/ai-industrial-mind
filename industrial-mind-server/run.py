"""启动入口：python run.py [dev|sit|uat|prod]（默认 dev）"""
import os
import sys

# 修复 Windows 控制台中文乱码：强制 Python 以 UTF-8 编码 stdio（reload 子进程继承环境变量）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 选择运行环境：python run.py dev/sit/uat/prod，缺省 dev
_env = sys.argv[1] if len(sys.argv) > 1 else "dev"
os.environ["APP_ENV"] = _env

import uvicorn
# 在 APP_ENV 设置之后导入配置，确保读取对应 yaml 环境
from app.config import settings

if __name__ == "__main__":
    print(f"[{_env}] API 服务启动: http://{settings.HOST}:{settings.PORT}  db={settings.DATABASE_URL}")
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)