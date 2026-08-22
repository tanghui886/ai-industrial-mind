---
name: scheduler
description: 智能排产能力：新订单/意向订单排产可行性评估（建议排产期、日产能、交付缓冲与风险）、产线产能查询（月度计划/已排/剩余空位/分日空位）、工令排产进度查询。当用户询问排产可行性、产能空位、工令排期时使用本技能。
---

# 智能排产（Scheduler）

面向集装箱制造企业的排产协同。调用本技能前先明确是否已具备箱型、数量、交付日期、产线等字段。

## 运用方法

1. **意图判定**
   - 排产可行性评估：用户给出箱型+数量（+交付日期/产线）时，调用 `evaluate_feasibility`。
   - 产能查询：用户询问某产线某月空位/利用率时，调用 `query_capacity`。
   - 排产查询：用户给出工令号或箱型+月份时，调用 `query_schedule`。

2. **字段补全**：若缺少箱型/数量/交付日期/产线，先向用户确认或在回复中明确指出缺失字段。

3. **产线校验**：产线编号为标准编号（PD-D/BS-A/JS-A/JS-B/FX-A）；不确定时先用 `list_lines` 确认。

4. **输出**：基于工具返回的真实数据作答；排产变更须在结尾注明需专业人员确认。

## 工具
- `evaluate_feasibility(box_type, quantity, delivery_date, line_code, delivery_location)`：排产可行性分析。
- `query_capacity(line_code, month, year)`：月度产能概况与分日空位明细。
- `query_schedule(line_code, work_order_no, box_type, month)`：工令排产列表。
- `list_lines()`：系统支持的产线。
- `get_box_type(code)`：箱型日产能标准与 TEU 系数。