<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CalendarDays, Factory, Sparkles, Plus, Pencil, Trash2, CheckCircle2, Save, RefreshCw } from 'lucide-vue-next'
import {
  getSchedule, getGantt, getGanttDays, saveGanttDays, getBoxTypes, smartPlan,
  createWorkOrder, confirmSchedule, deleteSchedule, saveCalendarBatch, getCalendar,
  smartAnalyzeAdjusted,
} from '@/api'
import { canAddWorkOrder, canSchedule, canApprove, canManageWorkOrder } from '@/utils/permission'

// 角色权限：添加工令(业务) / 排产(计划) / 审批(审批人) / 编辑删除(业务+计划)
const perm = computed(() => ({
  add: canAddWorkOrder(),
  schedule: canSchedule(),
  approve: canApprove(),
  manage: canManageWorkOrder(),
}))

const month = ref('2026-08')
const lineCode = ref('QD-D')
const view = ref<'calendar' | 'gantt' | 'table'>('calendar')
const loading = ref(false)
const data = ref<any>(null)
const boxTypes = ref<any[]>([])
let ganttChart: echarts.ECharts | null = null

// 甘特按天矩阵
const ganttDays = ref<any>(null)
const ganttDirty = ref(false)
const ganttSaving = ref(false)

const lines = [
  { code: 'QD-D', label: 'QD-D 特箱线' }, { code: 'SH-A', label: 'SH-A 上海A线' },
  { code: 'NT-A', label: 'NT-A 南通A线' }, { code: 'NT-B', label: 'NT-B 南通B线' },
  { code: 'LYG-A', label: 'LYG-A 连云港A线' },
]
const statusTag: Record<string, { label: string; cls: string }> = {
  confirmed: { label: '已确认', cls: 'cm-tag-success' },
  pending_approval: { label: '待审批', cls: 'cm-tag-warning' },
  draft: { label: '草稿', cls: 'cm-tag-info' },
  completed: { label: '已完成', cls: 'cm-tag-muted' },
  cancelled: { label: '已取消', cls: 'cm-tag-muted' },
}
const utilColor = (u: number, isWorkday: boolean) =>
  !isWorkday ? 'var(--cm-slate-300)' : u > 100 ? 'var(--cm-state-error)' : u >= 85 ? 'var(--cm-state-warning)' : 'var(--cm-primary)'

// 日历分段条：按工令号取稳定颜色（用于按订单产能量分段展示）
const ORDER_PALETTE = ['#06b6d4', '#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#ec4899', '#14b8a6', '#a855f7', '#f97316']
const orderColor = (wo: string) => {
  let h = 0
  for (let i = 0; i < wo.length; i++) h = (h * 31 + wo.charCodeAt(i)) % 997
  return ORDER_PALETTE[h % ORDER_PALETTE.length]
}

// 日历网格：前导空位 + 当月每日 + 尾部补齐
const calendarCells = computed(() => {
  const days: any[] = data.value?.calendar ?? []
  if (!days.length) return []
  const firstDow = new Date(days[0].date + 'T00:00:00').getDay()
  const cells: any[] = Array.from({ length: firstDow }, () => ({ blank: true, key: 'b' + Math.random() }))
  days.forEach((d: any) => cells.push({ ...d, key: d.date }))
  while (cells.length % 7 !== 0) cells.push({ blank: true, key: 't' + Math.random() })
  return cells
})

const monthLabel = computed(() => {
  const [y, m] = month.value.split('-')
  return `${y}年${Number(m)}月`
})

async function load() {
  loading.value = true
  try {
    data.value = await getSchedule({ line_code: lineCode.value, month: month.value })
    if (view.value === 'gantt') await nextTick(loadGanttDays)
  } finally { loading.value = false }
}

// ---- 甘特按天矩阵 ----
const ganttTotal = computed<Record<string, number>>(() => {
  const total: Record<string, number> = {}
  for (const o of ganttDays.value?.orders ?? []) {
    for (const [d, q] of Object.entries(o.daily ?? {})) total[d] = (total[d] ?? 0) + (q as number)
  }
  return total
})
const ganttCell = (wo: string, date: string) => Number(ganttDays.value?.orders?.find((o: any) => o.work_order_no === wo)?.daily?.[date] ?? 0)
// 甘特图中某工令已排总量（所有排产日数量之和）
const scheduledTotal = (o: any) => Object.values(o.daily ?? {}).reduce((a: number, q: any) => a + (Number(q) || 0), 0)
// 智能排产甘特矩阵：按日读取/写入某工令排产量
const smartRestDay = (date: string) => Number(smartDaysOfMonth.value?.find((d: any) => d.date === date)?.daily_capacity ?? 0) <= 0
const smartDayCap = (date: string) => Number(smartDaysOfMonth.value?.find((d: any) => d.date === date)?.daily_capacity ?? 0)
const smartCell = (p: any, date: string) => Number(p.daily_schedule?.find((s: any) => s.date === date)?.qty ?? 0)
function updateSmartCell(p: any, date: string, qty: number) {
  const q = Math.max(Number(qty) || 0, 0)
  const idx = p.daily_schedule?.findIndex((s: any) => s.date === date) ?? -1
  if (q > 0) {
    if (idx >= 0) p.daily_schedule[idx].qty = q
    else {
      p.daily_schedule.push({ date, qty: q })
      p.daily_schedule.sort((a: any, b: any) => (a.date < b.date ? -1 : 1))
    }
  } else if (idx >= 0) {
    p.daily_schedule.splice(idx, 1)
  }
}
// 合并行：智能排产工令（高亮、可编辑）+ 已排工令（仅展示，提供整体排产上下文）
const smartGanttRows = computed(() => {
  const rows: any[] = []
  const seen = new Set<string>()
  for (const p of smartResult.value?.proposals ?? []) {
    rows.push({ isSmart: true, work_order_no: p.work_order_no, box_type: p.box_type, quantity: p.quantity, prop: p })
    seen.add(p.work_order_no)
  }
  for (const o of ganttDays.value?.orders ?? []) {
    if (seen.has(o.work_order_no)) continue
    rows.push({ isSmart: false, work_order_no: o.work_order_no, box_type: o.box_type, quantity: o.quantity, teu: o.teu, daily: o.daily ?? {} })
  }
  return rows
})
const smartRowCell = (row: any, date: string) =>
  row.isSmart ? smartCell(row.prop, date) : Number(row.daily?.[date] ?? 0)
function updateSmartRowCell(row: any, date: string, qty: number) {
  if (row.isSmart) updateSmartCell(row.prop, date, qty)   // 已排工令仅展示，不调整
}
const smartTotal = (date: string) =>
  smartGanttRows.value.reduce((a: number, r: any) => a + smartRowCell(r, date), 0)
// 增加排产日：可选日期
const smartAddDate = reactive<Record<string, string>>({})
const availableDays = (p: any) => {
  const used = new Set((p.daily_schedule ?? []).map((s: any) => s.date))
  return smartDaysOfMonth.value.filter((d: any) => !used.has(d.date))
}
function addProposalDay(p: any) {
  const sel = smartAddDate[p.work_order_no]
  if (!sel) { ElMessage.warning('请先选择日期'); return }
  if ((p.daily_schedule ?? []).some((s: any) => s.date === sel)) { ElMessage.info('该日期已存在'); return }
  p.daily_schedule.push({ date: sel, qty: 0 })
  p.daily_schedule.sort((a: any, b: any) => (a.date < b.date ? -1 : 1))
  smartAddDate[p.work_order_no] = ''
}
// 当日排班日产能（来自排班配置，0=休息日）
const ganttDayCap = (date: string) => Number(ganttDays.value?.days?.find((d: any) => d.date === date)?.daily_capacity ?? 0)
const isRestDay = (date: string) => ganttDayCap(date) <= 0
// 已确认 / 待审批 / 已完成工令不可调整产能
const isLocked = (o: any) => ['confirmed', 'pending_approval', 'completed'].includes(o.status)
// 校验未通过的工令集合（用于高亮）
const ganttErrOrders = ref<Set<string>>(new Set())
// 甘特列样式：仅休息日（0 产能）灰色；有产能的周六日按正常上班日显示
const dayCellClass = (date: string) => (isRestDay(date) ? 'rest' : '')

async function loadGanttDays() {
  try {
    ganttDays.value = await getGanttDays({ line_code: lineCode.value, month: month.value })
    ganttDirty.value = false
    ganttErrOrders.value = new Set()
  } catch (e: any) { ElMessage.error(e.message) }
}

function updateGanttCell(wo: string, date: string, qty: number) {
  const o = ganttDays.value.orders.find((x: any) => x.work_order_no === wo)
  if (!o) return
  if (qty <= 0) delete o.daily[date]
  else o.daily[date] = qty
  ganttDirty.value = true
}

async function saveGantt() {
  // 校验（仅非"已完成"/"已确认"工令）：每条工令排产数量总和不得超过该工令总数量
  const errs = new Set<string>()
  for (const o of ganttDays.value?.orders ?? []) {
    if (isLocked(o)) continue            // 锁定工令不参与校验，也不参与调整
    const sum = Object.values(o.daily ?? {}).reduce((a: number, q: any) => a + (Number(q) || 0), 0)
    if (sum > o.quantity) {
      errs.add(o.work_order_no)
      ElMessage.error(`工令 ${o.work_order_no} 排产合计 ${sum} 台超过工令总数量 ${o.quantity} 台`)
    }
  }
  ganttErrOrders.value = errs
  if (errs.size) return                  // 有校验不通过的工令，保留高亮，不保存

  ganttSaving.value = true
  try {
    const items = (ganttDays.value?.orders ?? [])
      .filter((o: any) => !isLocked(o) && Object.keys(o.daily ?? {}).length)
      .map((o: any) => ({ work_order_no: o.work_order_no, daily: o.daily }))
    await saveGanttDays(lineCode.value, items)
    ElMessage.success('按天排产已保存')
    ganttDirty.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) } finally { ganttSaving.value = false }
}

function switchView(v: 'calendar' | 'gantt' | 'table') {
  view.value = v
  if (v === 'gantt') nextTick(loadGanttDays)
}

// ---- 智能排产（支持单选工令 / 手工调整日期 / 调整后智能建议）----
const smartVisible = ref(false)
const smartLoading = ref(false)
const smartResult = ref<any>(null)
const smartMode = ref<'all' | 'single'>('all')        // 批量 or 单选工令
const smartWo = ref('')                                // 选中的工令
const smartCandidate = ref<any[]>([])                  // 可选工令（草稿/待审批）
// 调整后智能建议
const smartAdviceLoading = ref(false)
const smartAdvice = ref<any>(null)
// 月内日期（用于增删排产日）
const smartDaysOfMonth = ref<any[]>([])

// ---- 产线排班配置（每日日产能，0=休息日）----
const shiftVisible = ref(false)
const shiftLoading = ref(false)
const shiftSaving = ref(false)
const shiftDays = ref<any[]>([])     // [{date, day, dow, is_weekend, capacity}]
const shiftBaseCap = ref(0)          // 产线默认日产能

async function openShift() {
  shiftVisible.value = true
  shiftLoading.value = true
  try {
    const caps = await getGanttDays({ line_code: lineCode.value, month: month.value })
    const calDays: any[] = await getCalendar({ line_code: lineCode.value, month: month.value })
    // 取产线默认日产能（未配置的用默认工作日产能填充）——取日历接口中某工作日的 daily_capacity
    const workCaps = calDays.filter((c: any) => (c.daily_capacity ?? 0) > 0)
    shiftBaseCap.value = workCaps.length ? workCaps[0].daily_capacity : 180
    const capByDate: Record<string, number> = {}
    for (const c of calDays) capByDate[c.date] = c.daily_capacity ?? 0
    shiftDays.value = (caps.days ?? []).map((d: any) => ({
      date: d.date, day: d.day, dow: d.dow, is_weekend: d.is_weekend,
      capacity: capByDate[d.date] ?? 0,
    }))
  } catch (e: any) { ElMessage.error(e.message) } finally { shiftLoading.value = false }
}

// 一键填充：工作日设为默认产能，周末/休息置 0
function fillDefaultShift() {
  shiftDays.value.forEach((d: any) => {
    d.capacity = d.is_weekend ? 0 : shiftBaseCap.value
  })
}

async function saveShift() {
  shiftSaving.value = true
  try {
    await saveCalendarBatch(lineCode.value, shiftDays.value.map((d: any) => ({
      date: d.date, daily_capacity: Math.max(Number(d.capacity) || 0, 0),
    })))
    ElMessage.success('排班配置已保存')
    shiftVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) } finally { shiftSaving.value = false }
}

// 收集候选工令（仅草稿；待审批/已确认等不可参与智能排产）
function collectCandidates() {
  const all: any[] = data.value?.orders ?? []
  smartCandidate.value = all.filter((o: any) => o.status === 'draft')
}

async function loadMonthDays() {
  try {
    const cal: any[] = await getGanttDays({ line_code: lineCode.value, month: month.value })
    smartDaysOfMonth.value = cal.days ?? []
  } catch { smartDaysOfMonth.value = [] }
}

async function openSmart() {
  smartVisible.value = true
  smartLoading.value = true
  smartResult.value = null
  smartAdvice.value = null
  smartAdviceLoading.value = false
  smartMode.value = 'all'
  smartWo.value = ''
  collectCandidates()
  await loadMonthDays()
  await loadGanttDays()
  try {
    smartResult.value = await smartPlan({ line_code: lineCode.value, month: month.value, apply: false })
  } catch (e: any) { ElMessage.error(e.message) } finally { smartLoading.value = false }
}

// 仅对选中工令进行排产
async function runSmartForSelected() {
  if (!smartWo.value) { ElMessage.warning('请先选择工令'); return }
  smartLoading.value = true
  smartResult.value = null
  smartAdvice.value = null
  try {
    smartResult.value = await smartPlan({ line_code: lineCode.value, month: month.value, apply: false, work_order_no: smartWo.value })
  } catch (e: any) { ElMessage.error(e.message) } finally { smartLoading.value = false }
}

function removeProposalDay(p: any, idx: number) { p.daily_schedule.splice(idx, 1) }

// 调整后获取智能建议
async function analyzeAdjusted(p: any) {
  smartAdviceLoading.value = true
  smartAdvice.value = null
  try {
    smartAdvice.value = await smartAnalyzeAdjusted({
      line_code: lineCode.value, work_order_no: p.work_order_no, daily_schedule: p.daily_schedule,
    })
  } catch (e: any) { ElMessage.error(e.message) } finally { smartAdviceLoading.value = false }
}

async function applySmart() {
  // 校验：排产日当天"已排 + 当前排产建议"的排产量合计（台，与甘特列表每日合计一致）不得超过排班配置的日产能
  const dayQty: Record<string, number> = {}
  for (const row of smartGanttRows.value) {
    for (const d of smartDaysOfMonth.value) {
      const q = smartRowCell(row, d.date)
      if (q > 0) dayQty[d.date] = (dayQty[d.date] ?? 0) + q
    }
  }
  for (const d of smartDaysOfMonth.value) {
    const cap = Number(d.daily_capacity ?? 0)
    const total = dayQty[d.date] ?? 0
    if (cap <= 0 && total > 0) { ElMessage.error(`${d.date} 为休息日（日产能 0），不可排产`); return }
    if (cap > 0 && total > cap) { ElMessage.error(`${d.date} 当日排产量合计（含已排）${total} 台超过日产能 ${cap} 台`); return }
  }
  try {
    // 提交前端手工调整后的每日排产建议
    const proposals = (smartResult.value?.proposals ?? []).map((p: any) => ({
      plan_id: p.plan_id, work_order_no: p.work_order_no, customer: p.customer,
      box_type: p.box_type, quantity: p.quantity, teu: p.teu,
      suggested_start: p.daily_schedule[0]?.date ?? p.suggested_start,
      suggested_end: p.daily_schedule[p.daily_schedule.length - 1]?.date ?? p.suggested_end,
      daily_schedule: p.daily_schedule, reason: p.reason, confidence: p.confidence,
      feasibility: p.feasibility,
    }))
    await smartPlan({ line_code: lineCode.value, month: month.value, apply: true, proposals })
    ElMessage.success('排产建议已应用')
    smartVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

// ---- 添加工令 ----
const formVisible = ref(false)
const form = reactive({
  line_code: '', customer: '', box_type: '', quantity: 60,
  start_date: '', end_date: '', delivery_location: '上海', remark: '',
})

function openForm() {
  const [y, m] = month.value.split('-').map(Number)
  const today = new Date()
  const start = new Date(Math.max(today.getTime(), new Date(y, m - 1, 1).getTime()))
  const end = new Date(start.getTime() + 4 * 86400000)
  form.line_code = lineCode.value
  form.customer = ''; form.box_type = boxTypes.value[0]?.code ?? '20GP'
  form.quantity = 60; form.delivery_location = '上海'; form.remark = ''
  form.start_date = start.toISOString().slice(0, 10)
  form.end_date = end.toISOString().slice(0, 10)
  formVisible.value = true
}

async function submitForm() {
  if (!form.customer || !form.box_type) { ElMessage.warning('请填写客户并选择箱型'); return }
  try {
    await createWorkOrder({ ...form, work_order_no: '' })
    ElMessage.success('工令已创建（草稿）')
    formVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function onConfirm(row: any) {
  try {
    await ElMessageBox.confirm(`确认工令 ${row.work_order_no} 的排产方案？确认后将生成审批单。`, '确认排产', { type: 'warning' })
    await confirmSchedule(row.id, '李计划')
    ElMessage.success('已提交审批')
    load()
  } catch { /* cancel */ }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除工令 ${row.work_order_no}？`, '删除', { type: 'error' })
    await deleteSchedule(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancel */ }
}

function onResize() { ganttChart?.resize() }

onMounted(async () => {
  boxTypes.value = await getBoxTypes() as any
  const now = new Date()
  month.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  await load()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => { window.removeEventListener('resize', onResize); ganttChart?.dispose() })
</script>

<template>
  <div class="planning-wrap" v-loading="loading">
    <!-- 工具栏 -->
    <section class="toolbar">
      <div class="toolbar-left">
        <el-date-picker v-model="month" type="month" placeholder="选择月份" format="YYYY年MM月"
                        value-format="YYYY-MM" style="width: 140px" @change="load" />
        <select v-model="lineCode" class="line-select" @change="load">
          <option v-for="l in lines" :key="l.code" :value="l.code">{{ l.label }}</option>
        </select>
        <div class="view-switch">
          <button v-for="v in (['calendar','gantt','table'] as const)" :key="v"
                  :class="{ active: view === v }" @click="switchView(v)">
            {{ v === 'calendar' ? '日历' : v === 'gantt' ? '甘特' : '表格' }}
          </button>
        </div>
      </div>
      <div class="toolbar-right">
        <button class="btn-ghost" @click="openShift"><CalendarDays :size="15" /> 排班配置</button>
        <button class="btn-primary" @click="openSmart"><Sparkles :size="15" /> 智能排产</button>
      </div>
    </section>

    <!-- 摘要卡 -->
    <section class="summary-row">
      <div class="summary-card"><p>本月计划 TEU</p><p class="num">{{ (data?.summary?.plan_teu ?? 0).toLocaleString() }}</p></div>
      <div class="summary-card"><p>已排 TEU</p><p class="num">{{ (data?.summary?.scheduled_teu ?? 0).toLocaleString() }}</p></div>
      <div class="summary-card"><p>剩余空位</p><p class="num text-success">{{ (data?.summary?.remaining_teu ?? 0).toLocaleString() }}</p></div>
      <div class="summary-card"><p>冲突数量</p><p class="num text-error">{{ data?.summary?.conflict_days ?? 0 }}</p></div>
      <div class="summary-card"><p>待审批变更</p><p class="num text-warning">{{ data?.pending_approvals ?? 0 }}</p></div>
    </section>

    <!-- AI 建议条 -->
    <section class="ai-bar">
      <div class="ai-left">
        <div class="ai-badge"><Sparkles :size="14" /></div>
        <div>
          <p class="ai-title">AI 建议</p>
          <p class="ai-text">将 <code>DFQD-2026-285-DS</code> 提前 2 天以避开物料缺口；点击「智能排产」查看本月完整建议</p>
        </div>
      </div>
      <div class="ai-actions">
        <button v-if="perm.schedule" class="btn-primary btn-xs" @click="openSmart">查看建议</button>
      </div>
    </section>

    <!-- 日历视图 -->
    <section v-if="view === 'calendar'" class="cm-card">
      <div class="section-head">
        <h2 class="cm-heading">{{ monthLabel }} 产能日历</h2>
        <div class="legend">
          <span><i class="dot" style="background:var(--cm-primary)"></i>正常</span>
          <span><i class="dot" style="background:var(--cm-state-warning)"></i>紧张</span>
          <span><i class="dot" style="background:var(--cm-state-error)"></i>冲突</span>
          <span><i class="dot" style="background:var(--cm-slate-300)"></i>休息日</span>
        </div>
      </div>
      <div class="dow-row">
        <div v-for="d in ['日','一','二','三','四','五','六']" :key="d">{{ d }}</div>
      </div>
      <div class="cm-calendar-grid">
        <template v-for="cell in calendarCells" :key="cell.key">
          <div v-if="cell.blank" class="cm-calendar-cell muted" />
          <div v-else class="cm-calendar-cell" :class="{ muted: !cell.is_workday }">
            <span class="cell-day">{{ cell.day }}</span>
            <div class="cell-hours">{{ cell.hours }}h</div>
            <div class="cell-bar-bg">
              <!-- 按每个订单产能量分段展示 -->
              <div v-for="it in cell.orders" :key="it.work_order_no" class="cell-seg"
                   :style="{ width: Math.min(it.pct, 100) + '%', background: orderColor(it.work_order_no) }"
                   :title="`${it.work_order_no} · ${it.qty}台 / ${it.teu}TEU · 占产能 ${it.pct}%`"></div>
            </div>
            <el-tooltip v-if="cell.orders?.length" placement="top" :show-after="200">
              <template #content>
                <div v-for="it in cell.orders" :key="it.work_order_no" class="tip-order">
                  <span class="tip-swatch" :style="{ background: orderColor(it.work_order_no) }"></span>
                  {{ it.work_order_no }} · {{ it.qty }}台 / {{ it.teu }}TEU · {{ it.pct }}%
                </div>
              </template>
              <div class="cell-items">{{ cell.orders.length }} 单</div>
            </el-tooltip>
            <div class="cell-cap"><span class="cap-booked">已排 {{ cell.booked_teu ?? 0 }}</span><span class="cap-free">空闲 {{ (cell.daily_capacity ?? 0) - (cell.booked_teu ?? 0) }}</span></div>
            <div v-if="cell.status === 'conflict'" class="cell-conflict"><i class="dot" style="background:var(--cm-state-error)"></i>冲突</div>
          </div>
        </template>
      </div>
    </section>

    <!-- 甘特按天矩阵视图 -->
    <section v-if="view === 'gantt'" class="cm-card">
      <div class="section-head">
        <h2 class="cm-heading">工令甘特 · 按天产能</h2>
        <div class="gantt-head-right">
          <span class="text-muted small">在日期格中直接输入每天排产量，实时统计每天合计</span>
          <button v-if="ganttDirty && perm.schedule" class="btn-primary btn-xs" :loading="ganttSaving" @click="saveGantt">
            <Save :size="14" /> 保存按天排产
          </button>
        </div>
      </div>
      <div class="gantt-wrap">
        <div v-if="!(ganttDays?.orders ?? []).length" class="empty">当月暂无排产工令</div>
        <table v-else class="gantt-days-table">
          <thead>
            <tr>
              <th class="gantt-wo-col">工令号</th>
              <th v-for="d in ganttDays.days" :key="d.date" class="gantt-day-col" :class="dayCellClass(d.date)">
                <span class="gd-dow">{{ d.dow }}</span>
                <span class="gd-num">{{ d.day }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in ganttDays.orders" :key="o.work_order_no"
                :class="{ 'gantt-row-error': ganttErrOrders.has(o.work_order_no) }">
              <td class="gantt-wo-col">
                <div class="gantt-wo">
                  <span class="wo-dot" :style="{ background: o.color }"></span>
                  <div>
                    <b class="mono">{{ o.work_order_no }}</b>
                    <span class="text-muted small">{{ o.box_type }} × {{ o.quantity }} · {{ o.status_cn }}</span>
                    <span class="text-muted small"> · 已排 <b class="mono">{{ scheduledTotal(o) }}</b></span>
                  </div>
                </div>
              </td>
              <td v-for="d in ganttDays.days" :key="d.date" class="gantt-day-col" :class="dayCellClass(d.date)">
                <input class="gantt-input" type="number" min="0" :value="ganttCell(o.work_order_no, d.date)"
                       :disabled="isRestDay(d.date) || isLocked(o) || !perm.schedule"
                       :title="isRestDay(d.date) ? '休息日，不可排产' : (isLocked(o) ? '已确认/待审批/已完成工令不可调整' : (!perm.schedule ? '当前角色无排产权限，仅可查看' : ''))"
                       @input="updateGanttCell(o.work_order_no, d.date, Number(($event.target as any).value))" />
              </td>
            </tr>
            <tr class="gantt-avail-row">
              <td class="gantt-wo-col"><b>可分配产能量</b></td>
              <td v-for="d in ganttDays.days" :key="d.date" class="gantt-day-col" :class="dayCellClass(d.date)">
                <b class="gd-avail" :class="{ 'gd-avail-neg': (ganttDayCap(d.date) - (ganttTotal[d.date] ?? 0)) < 0 }">{{ ganttDayCap(d.date) - (ganttTotal[d.date] ?? 0) }}</b>
              </td>
            </tr>
            <tr class="gantt-total-row">
              <td class="gantt-wo-col"><b>每日合计</b></td>
              <td v-for="d in ganttDays.days" :key="d.date" class="gantt-day-col" :class="dayCellClass(d.date)">
                <b class="gd-total">{{ ganttTotal[d.date] ?? 0 }}</b>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 工令明细表 -->
    <section class="cm-card">
      <div class="section-head">
        <h2 class="cm-heading">工令明细</h2>
        <button v-if="perm.add" class="btn-ghost" @click="openForm"><Plus :size="15" /> 添加工令</button>
      </div>
      <div class="table-scroll">
        <table class="cm-wo-table">
          <thead>
            <tr>
              <th>产线</th><th>工令号</th><th>客户</th><th>箱型</th>
              <th>数量</th><th>TEU</th><th>开始日期</th><th>结束日期</th>
              <th>日计划排产量</th><th>日产能</th><th>状态</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in data?.orders ?? []" :key="o.id">
              <td>{{ o.line_code }}</td>
              <td class="mono">{{ o.work_order_no }}</td>
              <td>{{ o.customer }}</td>
              <td>{{ o.box_type }}</td>
              <td class="cm-tabular">{{ o.quantity }}</td>
              <td class="cm-tabular">{{ o.teu }}</td>
              <td class="cm-tabular">{{ o.start_date }}</td>
              <td class="cm-tabular">{{ o.end_date }}</td>
              <td class="cm-tabular">{{ o.daily_planned_qty }}</td>
              <td class="cm-tabular">{{ o.daily_capacity }}</td>
              <td><span class="cm-tag" :class="statusTag[o.status]?.cls ?? 'cm-tag-muted'">{{ o.status_cn }}</span></td>
              <td>
                <div class="row-actions">
                  <el-tooltip v-if="perm.schedule && o.status === 'draft'" content="确认排产（生成审批单）"><button class="icon-btn" @click="onConfirm(o)"><CheckCircle2 :size="14" /></button></el-tooltip>
                  <el-tooltip v-if="perm.manage && !isLocked(o)" content="编辑"><button class="icon-btn" @click="openForm"><Pencil :size="14" /></button></el-tooltip>
                  <el-tooltip v-if="perm.manage && !isLocked(o)" content="删除"><button class="icon-btn" @click="onDelete(o)"><Trash2 :size="14" /></button></el-tooltip>
                </div>
              </td>
            </tr>
            <tr v-if="!(data?.orders ?? []).length"><td colspan="12" class="empty">当月暂无工令</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 查看建议弹窗（按工令选择排产 / 增删排产日 / 调整后智能建议） -->
    <el-dialog v-model="smartVisible" title="智能排产 · 按工令排产，可手工调整每日排产量" width="900px" top="4vh">
      <div v-loading="smartLoading" class="smart-body">
        <!-- 工令选择：批量 vs 单选 -->
        <div class="smart-select-row">
          <div class="smart-mode-switch">
            <button :class="{ active: smartMode === 'all' }" @click="smartMode = 'all'; openSmart()">全部工令</button>
            <button :class="{ active: smartMode === 'single' }" @click="smartMode = 'single'">单选工令</button>
          </div>
          <template v-if="smartMode === 'single'">
            <el-select v-model="smartWo" placeholder="选择工令" filterable style="width: 280px" size="default">
              <el-option v-for="c in smartCandidate" :key="c.work_order_no" :value="c.work_order_no"
                         :label="`${c.work_order_no} · ${c.box_type} × ${c.quantity}台`" />
            </el-select>
            <button class="btn-primary btn-xs" :disabled="smartLoading" @click="runSmartForSelected">对选中工令排产</button>
          </template>
        </div>

        <template v-if="smartResult">
          <div class="smart-summary">
            <span>月度计划：<b>{{ smartResult.summary?.plan_teu }}</b> TEU</span>
            <span>已排：<b>{{ smartResult.summary?.scheduled_teu }}</b> TEU</span>
            <span>剩余：<b class="text-success">{{ smartResult.summary?.remaining_teu }}</b> TEU</span>
            <span>冲突日：<b class="text-error">{{ smartResult.summary?.conflict_days }}</b> 天</span>
          </div>

          <div v-for="(p, i) in smartResult.proposals ?? []" :key="p.work_order_no" class="proposal">
            <div class="proposal-head">
              <span class="cm-tag cm-tag-info">建议</span>
              <span class="mono">{{ p.work_order_no }}</span>
              <span class="text-muted small">{{ p.box_type }} × {{ p.quantity }}台 ·
                {{ p.daily_schedule[0]?.date ?? p.suggested_start }} ~ {{ p.daily_schedule[p.daily_schedule.length - 1]?.date ?? p.suggested_end }}</span>
              <span class="proposal-feas" :class="p.feasibility === 'feasible' ? 'text-success' : p.feasibility === 'tight' ? 'text-warning' : 'text-error'">
                {{ { feasible: '可行', tight: '紧张', infeasible: '不可行' }[p.feasibility] ?? p.feasibility }}
              </span>
            </div>
            <p class="proposal-text text-muted small">{{ p.reason }}</p>

            <!-- 每日排产量编辑：可增删排产日 -->
            <div class="daily-edit">
              <div class="daily-rows">
                <div v-for="(s, idx) in p.daily_schedule" :key="s.date" class="daily-row">
                  <span class="daily-date">{{ s.date }}</span>
                  <div class="daily-qty">
                    <button class="mini-btn" @click="s.qty = Math.max(0, s.qty - 10)">−</button>
                    <input class="daily-input" type="number" min="0" :value="s.qty"
                           @input="s.qty = Math.max(0, Number(($event.target as any).value))" />
                    <button class="mini-btn" @click="s.qty += 10">＋</button>
                  </div>
                  <button class="mini-btn danger" @click="removeProposalDay(p, idx)">
                    <Trash2 :size="13" />
                  </button>
                </div>
              </div>
              <button class="btn-ghost btn-xs" @click="addProposalDay(p)"><Plus :size="13" /> 增加排产日</button>
              <el-select v-model="smartAddDate[p.work_order_no]" placeholder="选择日期" size="small" clearable style="width: 160px">
                <el-option v-for="d in availableDays(p)" :key="d.date" :value="d.date"
                           :label="`${d.date} ${d.dow}`" :disabled="smartRestDay(d.date)" />
              </el-select>
              <button class="btn-primary btn-xs" :loading="smartAdviceLoading" @click="analyzeAdjusted(p)">
                <Sparkles :size="13" /> 调整后智能分析
              </button>
            </div>

            <!-- 调整后智能建议 -->
            <div v-if="smartAdvice && smartAdvice.work_order_no === p.work_order_no" class="advice-box"
                 :class="smartAdvice.risk_level === 'high' ? 'advice-error' : smartAdvice.risk_level === 'medium' ? 'advice-warn' : 'advice-ok'">
              <div class="advice-head">
                <Sparkles :size="14" />
                <b>智能分析</b>
                <span class="advice-risk" :class="smartAdvice.risk_level">
                  交期风险 {{ { high: '高', medium: '中', low: '低' }[smartAdvice.risk_level] ?? smartAdvice.risk_level }}
                </span>
              </div>
              <div class="advice-meta">
                <span>合计 <b>{{ smartAdvice.planned_qty }}</b> / {{ smartAdvice.quantity }} 台</span>
                <span>预计交付 <b>{{ smartAdvice.delivery_assess?.estimated_delivery }}</b></span>
                <span>最高日产能 <b>{{ smartAdvice.max_daily_qty }}</b> 台</span>
              </div>
              <ul class="advice-list">
                <li v-for="(sug, j) in smartAdvice.suggestions ?? []" :key="j">{{ sug }}</li>
              </ul>
            </div>
          </div>
          <p v-if="!(smartResult.proposals ?? []).length" class="empty">
            {{ smartMode === 'single' ? '该工令无可排产建议，请检查工令状态或交期' : '本月排产良好，暂无优化建议' }}
          </p>

          <!-- 智能排产甘特 · 按天调整（可直接在单元格填数量改动排产日期） -->
          <div v-if="(smartResult.proposals ?? []).length" class="smart-gantt">
            <div class="smart-gantt-title">
              <Sparkles :size="14" /> 智能排产甘特 · 按天调整
              <span class="text-muted small">（在单元格填入数量即可把排产量排到该日期，清空即撤下该日）</span>
            </div>
            <div class="smart-gantt-scroll">
              <table class="gantt-days-table smart-gantt-table">
                <thead>
                  <tr>
                    <th class="gantt-wo-col">工令</th>
                    <th v-for="d in smartDaysOfMonth" :key="d.date" class="gantt-day-col" :class="smartRestDay(d.date) ? 'rest' : ''">
                      <span class="gd-dow">{{ d.dow }}</span>
                      <span class="gd-num">{{ d.day }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in smartGanttRows" :key="row.work_order_no"
                      :class="{ 'smart-row-active': row.isSmart }">
                    <td class="gantt-wo-col">
                      <div class="gantt-wo">
                        <div>
                          <b class="mono">{{ row.work_order_no }}</b>
                          <span class="text-muted small">{{ row.box_type }} × {{ row.quantity }}{{ row.isSmart ? ' · 智能排产' : '' }}</span>
                        </div>
                      </div>
                    </td>
                    <td v-for="d in smartDaysOfMonth" :key="d.date" class="gantt-day-col" :class="smartRestDay(d.date) ? 'rest' : ''">
                      <input class="gantt-input" type="number" min="0" :value="smartRowCell(row, d.date)"
                             :disabled="smartRestDay(d.date) || !row.isSmart"
                             :title="smartRestDay(d.date) ? '休息日，不可排产' : (!row.isSmart ? '已排工令仅展示，请在上方列表调整' : '')"
                             @input="updateSmartRowCell(row, d.date, Number(($event.target as any).value))" />
                    </td>
                  </tr>
                  <tr class="gantt-avail-row">
                    <td class="gantt-wo-col"><b>可分配产能量</b></td>
                    <td v-for="d in smartDaysOfMonth" :key="d.date" class="gantt-day-col" :class="smartRestDay(d.date) ? 'rest' : ''">
                      <b class="gd-avail" :class="{ 'gd-avail-neg': (smartDayCap(d.date) - smartTotal(d.date)) < 0 }">{{ smartDayCap(d.date) - smartTotal(d.date) }}</b>
                    </td>
                  </tr>
                  <tr class="gantt-total-row">
                    <td class="gantt-wo-col"><b>每日合计</b></td>
                    <td v-for="d in smartDaysOfMonth" :key="d.date" class="gantt-day-col" :class="smartRestDay(d.date) ? 'rest' : ''">
                      <b class="gd-total">{{ smartTotal(d.date) }}</b>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="smartVisible = false">关闭</button>
        <button class="btn-primary" :disabled="smartLoading || !(smartResult?.proposals ?? []).length" @click="applySmart">应用调整后的建议</button>
      </template>
    </el-dialog>

    <!-- 产线排班配置弹窗（每日日产能，0=休息日） -->
    <el-dialog v-model="shiftVisible" title="产线排班配置 · 每日产能（TEU）" width="780px" top="4vh">
      <div v-loading="shiftLoading" class="shift-body">
        <div class="shift-header">
          <div class="shift-actions">
            <button class="btn-ghost btn-xs" @click="fillDefaultShift">
              <RefreshCw :size="13" /> 一键填充默认产能
            </button>
            <div class="shift-hint">
              <span>默认产能：</span>
              <el-input-number v-model="shiftBaseCap" :min="0" :max="500" size="small" style="width: 100px" />
              <span class="text-muted small"> TEU/天（工作日默认值）</span>
            </div>
          </div>
        </div>
        <div class="shift-grid" v-if="shiftDays.length">
          <div class="shift-row" v-for="(week, i) in Math.ceil(shiftDays.length / 7)" :key="i">
            <div class="shift-cell" v-for="d in shiftDays.slice(i*7, (i+1)*7)" :key="d.date">
              <div class="shift-date" :class="{ weekend: d.is_weekend }">
                <span class="day">{{ d.day }}</span>
                <span class="dow">{{ d.dow }}</span>
              </div>
              <el-input v-model.number="d.capacity" type="number" min="0" :max="500" size="small"
                        :class="{ zero: d.capacity === 0 && !d.is_weekend }" />
            </div>
          </div>
        </div>
        <div class="shift-note">
          <p class="text-muted small">
            <i class="dot weekend-dot" /> 周末默认填充 0（休息日） |
            <i class="dot zero-dot" /> 工作日填 0 表示设置为休息日 |
            产能单位：TEU/天
          </p>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="shiftVisible = false">取消</button>
        <button class="btn-primary" :loading="shiftSaving" @click="saveShift">保存排班配置</button>
      </template>
    </el-dialog>

    <!-- 添加工令弹窗 -->
    <el-dialog v-model="formVisible" title="添加工令" width="520px">
      <el-form label-width="92px">
        <el-form-item label="产线" required>
          <el-select v-model="form.line_code" style="width: 100%">
            <el-option v-for="l in lines" :key="l.code" :value="l.code" :label="`${l.code} · ${l.label}`" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户" required><el-input v-model="form.customer" placeholder="如：中远海运" /></el-form-item>
        <el-form-item label="箱型" required>
          <el-select v-model="form.box_type" filterable style="width: 100%">
            <el-option v-for="b in boxTypes" :key="b.code" :value="b.code" :label="`${b.code} · ${b.name}（日产能 ${b.daily_capacity_std}）`" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量（台）" required><el-input-number v-model="form.quantity" :min="1" :max="5000" style="width: 100%" /></el-form-item>
        <el-form-item label="开始日期" required><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        <el-form-item label="结束日期" required><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        <el-form-item label="交付地点"><el-input v-model="form.delivery_location" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="formVisible = false">取消</button>
        <button class="btn-primary" @click="submitForm">创建（草稿）</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.planning-wrap { padding: 20px 24px 28px; display: flex; flex-direction: column; gap: 16px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  border: 1px solid var(--cm-border); background: var(--cm-card); border-radius: 12px; padding: 14px 16px; }
.toolbar-left { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.line-select { border: 1px solid var(--cm-border); background: var(--cm-background); color: var(--cm-foreground);
  border-radius: 6px; padding: 6px 10px; font-size: 13px; outline: none; cursor: pointer; }
.view-switch { display: inline-flex; border: 1px solid var(--cm-border); border-radius: 6px; padding: 3px; background: var(--cm-background); }
.view-switch button { border: none; background: transparent; padding: 5px 14px; font-size: 12px; font-weight: 500;
  color: var(--cm-muted-foreground); border-radius: 4px; cursor: pointer; }
.view-switch button.active { background: var(--cm-primary); color: #fff; }
.btn-primary { display: inline-flex; align-items: center; gap: 6px; border: none; cursor: pointer;
  background: var(--cm-primary); color: #fff; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 600; }
.btn-primary:hover { background: var(--cm-primary-700); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; background: var(--cm-card);
  color: var(--cm-foreground); border: 1px solid var(--cm-border); border-radius: 6px; padding: 8px 14px; font-size: 13px; font-weight: 500; }
.btn-ghost:hover { background: var(--cm-muted); }
.btn-xs { padding: 6px 12px; font-size: 12px; }
.summary-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.summary-card { border: 1px solid var(--cm-border); background: var(--cm-card); border-radius: 12px; padding: 14px 16px; box-shadow: var(--cm-shadow-1); }
.summary-card p { margin: 0; }
.summary-card p:first-child { font-size: 12px; color: var(--cm-muted-foreground); }
.summary-card .num { font-size: 24px; font-weight: 600; margin-top: 4px; font-variant-numeric: tabular-nums; }
.ai-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px;
  border: 1px solid var(--cm-primary-200); background: var(--cm-primary-50); border-radius: 8px; padding: 14px 16px; }
.ai-left { display: flex; align-items: flex-start; gap: 12px; }
.ai-badge { width: 24px; height: 24px; border-radius: 999px; background: var(--cm-primary); color: #fff;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 2px; }
.ai-title { margin: 0; font-size: 14px; font-weight: 600; }
.ai-text { margin: 2px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.ai-text code { font-family: var(--cm-font-mono); color: var(--cm-foreground); font-weight: 500; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.section-head h2 { margin: 0; font-size: 15px; }
.small { font-size: 12px; }
.text-muted { color: var(--cm-muted-foreground); }
.legend { display: flex; gap: 14px; font-size: 12px; color: var(--cm-muted-foreground); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 8px; height: 8px; border-radius: 999px; display: inline-block; }
.dow-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }
.dow-row > div { background: var(--cm-muted); text-align: center; padding: 6px 0; font-size: 12px; font-weight: 500; color: var(--cm-muted-foreground); border-radius: 4px; }
.cm-calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.cm-calendar-cell { min-height: 92px; border: 1px solid var(--cm-border); border-radius: 8px; background: var(--cm-card); padding: 8px; }
.cm-calendar-cell.muted { background: var(--cm-slate-100); }
.cell-day { font-size: 12px; font-weight: 600; }
.cell-hours { font-size: 11px; color: var(--cm-muted-foreground); margin-top: 6px; }
.cell-bar-bg { height: 6px; border-radius: 999px; background: var(--cm-slate-100); margin-top: 5px; overflow: hidden; display: flex; }
.cell-seg { height: 100%; }
.cell-items { font-size: 10px; color: var(--cm-primary); margin-top: 4px; cursor: default; }
.cell-cap { display: flex; justify-content: space-between; gap: 4px; margin-top: 3px; font-size: 10px; }
.cap-booked { color: var(--cm-primary); }
.cap-free { color: var(--cm-muted-foreground); }
.tip-order { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.tip-swatch { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.cell-conflict { display: flex; align-items: center; gap: 4px; font-size: 10px; color: var(--cm-state-error); margin-top: 3px; }
.gantt-wrap { width: 100%; overflow-x: auto; }
.gantt-head-right { display: flex; align-items: center; gap: 12px; }
.gantt-days-table { border-collapse: separate; border-spacing: 0; min-width: 100%; }
.gantt-days-table th, .gantt-days-table td { border-bottom: 1px solid var(--cm-border); border-right: 1px solid var(--cm-border); padding: 4px; text-align: center; vertical-align: middle; }
.gantt-days-table thead th { background: var(--cm-slate-50); font-weight: 600; position: sticky; top: 0; z-index: 2; }
.gantt-days-table th.gantt-day-col, .gantt-days-table td.gantt-day-col { min-width: 44px; }
.gantt-days-table th.gantt-day-col.weekend, .gantt-days-table td.gantt-day-col.weekend { background: var(--cm-slate-100); }
.gantt-days-table th.gantt-day-col.rest, .gantt-days-table td.gantt-day-col.rest { background: var(--cm-slate-200); opacity: 0.6; }
.gantt-days-table td.gantt-day-col.rest .gantt-input { color: var(--cm-slate-400); cursor: not-allowed; }
.gantt-days-table td.gantt-day-col.rest .gantt-input:hover, .gantt-days-table td.gantt-day-col.rest .gantt-input:focus { border-color: transparent; background: transparent; }
.gantt-days-table tr.gantt-row-error td { background: var(--cm-state-error-bg); }
.gantt-days-table tr.gantt-row-error td.gantt-day-col.rest { background: var(--cm-state-error-bg); opacity: 1; }
.gantt-days-table tr.gantt-row-error .gantt-input { border-color: var(--cm-state-error); }
.gantt-days-table thead th:first-child, .gantt-days-table td:first-child { position: sticky; left: 0; z-index: 1; background: var(--cm-card); }
.gantt-days-table thead th:first-child { z-index: 3; }
.gd-dow { display: block; font-size: 10px; color: var(--cm-muted-foreground); }
.gd-num { font-size: 12px; font-weight: 600; }
.gantt-wo-col { min-width: 200px; text-align: left !important; padding: 6px 10px !important; }
.gantt-wo { display: flex; align-items: center; gap: 8px; }
.gantt-wo > div { display: flex; flex-direction: column; gap: 2px; }
.wo-dot { width: 8px; height: 8px; border-radius: 999px; flex-shrink: 0; }
.gantt-input { width: 100%; height: 26px; border: 1px solid transparent; border-radius: 4px; text-align: center; font-size: 12px; font-variant-numeric: tabular-nums; background: transparent; color: var(--cm-foreground); outline: none; }
.gantt-input:hover { border-color: var(--cm-border); background: var(--cm-card); }
.gantt-input:focus { border-color: var(--cm-primary); background: var(--cm-primary-50); }
.gantt-total-row td { background: var(--cm-primary-50); }
.gantt-total-row .gd-total { color: var(--cm-primary); font-size: 12px; font-variant-numeric: tabular-nums; }
.gantt-avail-row td { background: var(--cm-slate-100); }
.gantt-avail-row .gd-avail { color: var(--cm-success, #10b981); font-size: 12px; font-variant-numeric: tabular-nums; }
.gantt-avail-row .gd-avail.gd-avail-neg { color: var(--cm-state-error); }
/* 锁定可分配/合计行：垂直滚动时固定在底部（合计最底，可分配紧贴其上） */
.gantt-days-table tr.gantt-avail-row td, .gantt-days-table tr.gantt-total-row td { position: sticky; bottom: 0; z-index: 2; box-shadow: inset 0 1px 0 var(--cm-border); }
.gantt-days-table tr.gantt-avail-row td { bottom: 22px; }
.gantt-days-table tr.gantt-avail-row td.gantt-wo-col, .gantt-days-table tr.gantt-total-row td.gantt-wo-col { left: auto; }
.daily-table { margin-top: 8px; overflow-x: auto; border: 1px solid var(--cm-border); border-radius: 6px; }
.daily-table table { border-collapse: collapse; }
.daily-table th, .daily-table td { border: 1px solid var(--cm-border); padding: 4px 8px; font-size: 12px; white-space: nowrap; }
.daily-table thead th { background: var(--cm-slate-50); font-weight: 600; color: var(--cm-muted-foreground); }
.daily-input { width: 56px; height: 26px; border: 1px solid var(--cm-border); border-radius: 4px; text-align: center; font-size: 12px; font-variant-numeric: tabular-nums; color: var(--cm-foreground); outline: none; }
.daily-input:focus { border-color: var(--cm-primary); background: var(--cm-primary-50); }
.proposal-feas { margin-left: auto; font-size: 12px; font-weight: 600; }
.text-success { color: var(--cm-state-success); }
.text-warning { color: var(--cm-state-warning); }
.text-error { color: var(--cm-state-error); }
.smart-select-row { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
.smart-mode-switch { display: inline-flex; border: 1px solid var(--cm-border); border-radius: 6px; padding: 3px; background: var(--cm-slate-50); }
.smart-mode-switch button { border: none; background: transparent; padding: 6px 14px; font-size: 12px; font-weight: 500; color: var(--cm-muted-foreground); border-radius: 4px; cursor: pointer; }
.smart-mode-switch button.active { background: var(--cm-primary); color: #fff; }
.daily-edit { margin-top: 8px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.daily-rows { display: flex; flex-wrap: wrap; gap: 6px; flex: 1; }
.daily-row { display: flex; align-items: center; gap: 4px; border: 1px solid var(--cm-border); border-radius: 6px; padding: 3px 6px; background: var(--cm-slate-50); }
.daily-date { font-size: 11px; color: var(--cm-muted-foreground); font-variant-numeric: tabular-nums; }
.daily-qty { display: flex; align-items: center; gap: 2px; }
.mini-btn { width: 22px; height: 22px; border: none; background: transparent; color: var(--cm-muted-foreground); border-radius: 4px; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; font-size: 14px; }
.mini-btn:hover { background: var(--cm-muted); }
.mini-btn.danger:hover { color: var(--cm-state-error); }
.advice-box { margin-top: 10px; border-radius: 8px; padding: 10px 12px; border: 1px solid; }
.advice-box.advice-ok { background: var(--cm-state-success-bg); border-color: var(--cm-state-success); }
.advice-box.advice-warn { background: var(--cm-state-warning-bg); border-color: var(--cm-state-warning); }
.advice-box.advice-error { background: var(--cm-state-error-bg); border-color: var(--cm-state-error); }
.advice-head { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
.advice-head b { color: var(--cm-foreground); }
.advice-risk { margin-left: auto; font-size: 11px; padding: 1px 8px; border-radius: 999px; font-weight: 500; }
.advice-risk.low { background: var(--cm-state-success); color: #fff; }
.advice-risk.medium { background: var(--cm-state-warning); color: #fff; }
.advice-risk.high { background: var(--cm-state-error); color: #fff; }
.advice-meta { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--cm-muted-foreground); margin-top: 6px; }
.advice-meta b { color: var(--cm-foreground); font-variant-numeric: tabular-nums; }
.advice-list { margin: 6px 0 0; padding-left: 18px; font-size: 12px; color: var(--cm-slate-600); line-height: 1.6; }
.table-scroll { overflow-x: auto; border: 1px solid var(--cm-border); border-radius: 8px; }
.cm-wo-table { width: 100%; min-width: 1040px; border-collapse: separate; border-spacing: 0; }
.cm-wo-table th, .cm-wo-table td { border-bottom: 1px solid var(--cm-border); padding: 10px 14px; text-align: left; vertical-align: middle; font-size: 13px; }
.cm-wo-table thead th { background: var(--cm-slate-50); font-weight: 600; white-space: nowrap; }
.cm-wo-table tbody tr:hover td { background: var(--cm-slate-50); }
.mono { font-family: var(--cm-font-mono); font-size: 12px; }
.row-actions { display: flex; gap: 6px; }
.icon-btn { border: none; background: transparent; color: var(--cm-muted-foreground); width: 28px; height: 28px;
  border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; }
.icon-btn:hover { background: var(--cm-muted); color: var(--cm-foreground); }
.empty { text-align: center; color: var(--cm-muted-foreground); padding: 24px 0 !important; }
.smart-body { min-height: 120px; }
.smart-summary { display: flex; gap: 20px; flex-wrap: wrap; font-size: 13px; color: var(--cm-muted-foreground);
  background: var(--cm-slate-50); border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; }
.smart-summary b { color: var(--cm-foreground); font-size: 15px; }
.proposal { border: 1px solid var(--cm-border); border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }
.proposal-head { display: flex; align-items: center; gap: 10px; }
.proposal-text { margin: 6px 0 0; font-size: 13px; color: var(--cm-slate-600); line-height: 1.6; }
.smart-gantt { margin-top: 16px; border-top: 1px solid var(--cm-border); padding-top: 12px; }
.smart-gantt-title { display: flex; align-items: center; gap: 8px; font-weight: 600; margin-bottom: 10px; }
.smart-gantt-scroll { overflow-x: auto; max-height: 320px; overflow-y: auto; border: 1px solid var(--cm-border); border-radius: 8px; }
.smart-gantt-table { border-collapse: separate; border-spacing: 0; width: 100%; }
/* 智能排产日期格加宽，容纳4位数字（如 >99 的排产量） */
.smart-gantt-table th.gantt-day-col, .smart-gantt-table td.gantt-day-col { min-width: 64px; }
.smart-gantt-table .gantt-input { width: 100%; }
.smart-gantt-table th, .smart-gantt-table td { border-bottom: 1px solid var(--cm-border); border-right: 1px solid var(--cm-border); text-align: center; }
.smart-gantt-table thead th:first-child, .smart-gantt-table td:first-child { position: sticky; left: 0; z-index: 1; background: var(--cm-card); }
.smart-gantt-table thead th:first-child { z-index: 3; }
.smart-gantt-table tr.gantt-total-row td { position: sticky; bottom: 0; background: var(--cm-slate-100); z-index: 3; box-shadow: inset 0 1px 0 var(--cm-border); }
.smart-gantt-table tr.gantt-avail-row td, .smart-gantt-table tr.gantt-total-row td { position: sticky; bottom: 0; }
.smart-gantt-table tr.gantt-avail-row td { background: var(--cm-primary-50); bottom: 22px; z-index: 2; }
/* 可分配产能量/每日合计 首列标签锁定：横向滚动时不移动 */
.smart-gantt-table tr.gantt-avail-row td.gantt-wo-col,
.smart-gantt-table tr.gantt-total-row td.gantt-wo-col { position: sticky; left: 0; z-index: 4; }
.smart-gantt-table tr.gantt-avail-row td.gantt-wo-col { background: var(--cm-primary-50); }
.smart-gantt-table tr.gantt-total-row td.gantt-wo-col { background: var(--cm-slate-100); }
.smart-gantt-table tr.smart-row-active td { background: var(--cm-state-info-bg); }
.smart-gantt-table tr.smart-row-active td.gantt-wo-col { background: var(--cm-state-info-bg); }
.smart-gantt-table tr.smart-row-active td.gantt-day-col.rest { background: var(--cm-state-info-bg); opacity: 1; }
.smart-gantt-table tr.smart-row-active .gantt-input { border-color: var(--cm-primary); }
/* 排班配置弹窗 */
.toolbar-right { display: flex; align-items: center; gap: 10px; }
.shift-body { min-height: 120px; }
.shift-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.shift-actions { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.shift-hint { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--cm-muted-foreground); }
.shift-hint .el-input-number { width: 100px; }
.shift-grid { display: flex; flex-direction: column; gap: 8px; }
.shift-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; }
.shift-cell { border: 1px solid var(--cm-border); border-radius: 8px; padding: 8px; display: flex; flex-direction: column; gap: 6px; }
.shift-date { display: flex; align-items: center; justify-content: space-between; font-size: 12px; }
.shift-date .day { font-weight: 600; }
.shift-date .dow { color: var(--cm-muted-foreground); }
.shift-date.weekend .day { color: var(--cm-state-warning); }
.shift-cell .el-input--small input.zero { color: var(--cm-state-error); }
.shift-note { margin-top: 12px; }
.shift-note p { margin: 0; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 999px; margin-right: 4px; }
.weekend-dot { background: var(--cm-state-warning); }
.zero-dot { background: var(--cm-state-error); }
</style>
