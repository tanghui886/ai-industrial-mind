from . import (admin, agents, approval, auth, chat_history, cost, dashboard,  # noqa: F401
               device, llm_log, material, meta, mobile, orchestrator, planning, storage,
               supplier)

ALL_ROUTERS = [meta.router, auth.router, dashboard.router, planning.router,
               approval.router, orchestrator.router, mobile.router, agents.router,
               device.router, cost.router, material.router, admin.router, llm_log.router,
               chat_history.router, storage.router, supplier.router]
