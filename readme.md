# ContainerMind · 集装箱制造业工业 Agent 系统

面向集装箱制造业的痛点：**前线业务人员在现场无法实时获取各产线的预排产情况**。本系统通过智能排产引擎，支持业务人员输入现场的预期需求，实时进行智能排产并给出排产方案，促进接单成功率、降低公司接单风险；同时**实时掌握设备异常、成本异常、堆存异常、物料异常**，更快实现预测与解决方案的落地。

系统能力：多 Agent 编排（智能排产 / 设备诊断 / 物料缺口 / 堆存风险 / 成本动因）、智能排产引擎、AI 现场接单与移动审批、物料与堆存管理、成本动因分析。

## 项目结构

```
ai-industrial-mind/
├── 说明文档/                      # 方案文档与 PC/移动端设计稿
├── industrial-mind-server/        # 后端（FastAPI + SQLAlchemy + SQLite）
│   ├── app/
│   │   ├── main.py                # 入口（启动时自动建表 + 写入种子数据）
│   │   ├── routers/               # 接口：meta / auth / dashboard / planning / approval
│   │   │                          #       / agents / orchestrator / mobile / device
│   │   │                          #       / cost / material / storage / admin / llm_log / chat_history
│   │   ├── services/              # 排产引擎、意图识别、LLM 接入、物料用量估算
│   │   ├── models.py / seed.py / database.py / config.py / permissions.py
│   ├── data/containermind.db      # SQLite 数据库（首次启动自动生成）
│   ├── smoke_test.py              # 冒烟测试
│   └── requirements.txt
└── industrial-mind-front/         # 前端（Vue3 + TS + Vite + Element Plus + Vant4 + ECharts）
    ├── src/
    │   ├── views/pc/              # PC 端：产线总览 / 排产 / Agent / 审批 / 物料 / 堆存
    │   │                          #       / 设备 / 成本动因 / 系统管理
    │   ├── views/mobile/          # 移动端：现场接单 / 排产查看 / 审批中心
    │   ├── layouts/               # PC 顶部导航布局 / 移动端底部 Tab 布局
    │   ├── api/index.ts           # Axios + SSE 封装（代理至后端 /api/v1）
    │   └── router / styles
    └── vite.config.ts             # 端口 5173，/api 代理到 127.0.0.1:8000
```

## 环境要求

- Python ≥ 3.10（含 fastapi、uvicorn、sqlalchemy 等，见 requirements.txt）
- Node.js ≥ 18

## 启动命令

### 1. 后端（端口 8000）

```bash
cd d:\pycharm\ai-industrial-mind\industrial-mind-server

# 首次：安装依赖
pip install -r requirements.txt

# 启动（Windows PowerShell / CMD 通用）
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API 文档（Swagger）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/v1/health
- 首次启动自动建表并写入演示种子数据（工厂/产线/箱型/工令/审批单/物料/设备/成本基准等）

### 2. 前端（端口 5173）

```bash
cd d:\pycharm\ai-industrial-mind\industrial-mind-front

# 首次：安装依赖
npm install

# 启动开发服务器
npm run dev
```

- 生产构建：`npm run build`（产物在 `dist/`），本地预览：`npm run preview`

### 3. 访问入口与功能

| 端 | 地址 | 页面 | 主要功能 |
| --- | --- | --- | --- |
| PC | /pc/dashboard | 产线总览 | KPI / 产能图 / 设备健康 / 告警 |
| PC | /pc/planning | 排产工作台 | 日历甘特 / 表格 / 智能排产 / 日产能 |
| PC | /pc/agent | Agent 对话台 | SSE 流式思考 + 结构化结论（6 个子智能体） |
| PC | /pc/approval | 审批工作台 | 通过 / 驳回 / 转交 |
| PC | /pc/material | 物料维护 | 物料增删改、库存、订单扣减 / 缺口自动计算 |
| PC | /pc/storage | 堆存管理 | 各产线总容纳 / 堆存 / 预堆存 / 剩余空间与爆仓风险 |
| PC | /pc/device | 设备大屏 | 各产线设备健康 / 异常汇总 |
| PC | /pc/device-manage | 设备管理 | 设备台账维护 |
| PC | /pc/cost | 成本动因大屏 | 按产线 / 工令的成本动因看板 |
| PC | /pc/cost-manage | 各维度数据管理 | 成本维度数据维护 |
| PC | /pc/cost-baseline | 基准配置 | 动因基准配置 |
| PC | /pc/cost-analyze | 成本动因分析 | 四种范围分析 + LLM 总结 |
| PC | /pc/cost-records | 分析明细 | 历史分析记录与明细 |
| PC | /pc/cost-material-detail | 物料明细 | 产线×工令×物料用量明细 |
| PC | /pc/users | 用户管理 | 系统管理员 |
| PC | /pc/permissions | 权限管理 | 系统管理员 |
| PC | /pc/roles | 角色管理 | 系统管理员 |
| PC | /pc/llm-log | 模型调用记录 | 系统管理员 |
| 移动端 | /m/quick-order | 现场接单 | 一句话 AI 排产可行性分析 |
| 移动端 | /m/schedule | 排产查看 | KPI / 日历 / 当日工令 |
| 移动端 | /m/approvals | 审批中心 | 待办 / 已办 / 我发起的 |

> 前端通过 Vite 代理将 `/api` 转发到后端 8000 端口，需先启动后端。

## Agent 子智能体

Agent 编排层通过大模型意图识别（未配置时回退规则引擎）将用户输入路由到以下子智能体：

| 子智能体 | 意图类型 | 能力 |
| --- | --- | --- |
| 智能排产 | new_order_intent / schedule_query / capacity_query | 新订单可行性 / 产能查询 / 排产查询 |
| 设备诊断 | device_query | 设备健康、异常、诊断、报警 |
| 物料缺口 | material_gap | 缺料物料统计、补货建议 |
| 堆存风险 | storage_risk | 产线堆存爆仓风险预警 |
| 成本动因 | cost_analysis | 成本动因分析与总结 |
| 其他 | general_chat | 一般性对话 |

## 测试

```bash
# 后端冒烟测试（元数据/大屏/排产/审批/Agent/移动端/SSE 流式）
cd d:\pycharm\ai-industrial-mind\industrial-mind-server
python smoke_test.py
```

## 演示数据速览

- 工厂：启东 QD-D（特箱线）、上海 SH-A、南通 NT-A/NT-B、连云港 LYG-A
- 示例指令：
  - 「意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海」→ 智能排产可行性 / 建议排产期 / 产能影响 / 物料齐套 / 风险
  - 「9月份QD-D线还有多少空位」（产能查询）
  - 「当前各产线物料缺口情况如何」（物料缺口）
  - 「哪些产线的堆存存在爆仓风险」（堆存风险）
  - 「本月成本动因分析」（成本动因）

## 关键业务口径

- 物料缺口 = 在库总量 − 订单扣减（审批中工令用量）− 草稿工令用量，差值为负时取绝对值
- 堆存数量 = 该产线已确认工令合计；预堆存 = 待审批/审批中 + 草稿工令合计；剩余空间 = 总容纳 − 堆存 − 预堆存，小于 0 标识爆仓风险
- 角色权限：业务角色维护工令、计划员排产、审批人审批、物料管理员维护物料、设备主管查看设备、采购/财务查看成本；系统管理员管理用户/权限/角色

## 说明

- LLM 意图增强通过环境变量配置（`services/llm.py`），未配置时自动回退到内置规则解析，功能不受影响。
- 所有 AI 结论均附带安全提示：排产变更、设备操作等决策须由专业人员确认后执行。