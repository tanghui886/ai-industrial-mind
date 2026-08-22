<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { showFailToast } from 'vant'
import {
  ChevronLeft, ChevronRight, Building2, ChevronDown, Container, Info,
  AlertTriangle, CalendarDays,
} from 'lucide-vue-next'
import { getCapacityBrief, getDayOrders, getFactories } from '@/api'

const month = ref('2026-08')
const lineCode = ref('PD-D')
const loading = ref(false)
const brief = ref<any>(null)
const factories = ref<any[]>([])
const selectedDay = ref<string>('')
const dayOrders = ref<any[]>([])

const lineName = computed(() => {
  for (const f of factories.value)
    for (const l of f.lines)
      if (l.line_code === lineCode.value) return `${f.factory_name} ${l.line_name}`
  return lineCode.value
})

/** 周历：以今天（或选中日）所在周为基准 */
const weekDays = computed(() => {
  const days = brief.value?.days ?? []
  if (!days.length) return []
  const base = selectedDay.value
    ? new Date(selectedDay.value)
    : new Date()
  const dayMs = 86400000
  const monday = new Date(base)
  monday.setDate(base.getDate() - ((base.getDay() + 6) % 7))
  const out = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday.getTime() + i * dayMs)
    const iso = d.toISOString().slice(0, 10)
    const day = days.find((x: any) => x.date === iso)
    out.push({
      iso, dow: ['一', '二', '三', '四', '五', '六', '日'][i],
      num: d.getDate(),
      util: day?.utilization ?? 0,
      isToday: iso === new Date().toISOString().slice(0, 10),
    })
  }
  return out
})

function shiftMonth(delta: number) {
  const [y, m] = month.value.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  month.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    brief.value = await getCapacityBrief({ line_code: lineCode.value, month: month.value })
    const days: any[] = brief.value.days ?? []
    if (!selectedDay.value || !days.some((d) => d.date === selectedDay.value)) {
      const todayIso = new Date().toISOString().slice(0, 10)
      const inMonth = days.find((d) => d.date === todayIso)
      selectedDay.value = inMonth?.date ?? days.find((d) => d.is_workday)?.date ?? days[0]?.date ?? ''
    }
    await loadDayOrders()
  } catch (e: any) {
    showFailToast(e.message)
  } finally { loading.value = false }
}

async function loadDayOrders() {
  if (!selectedDay.value) { dayOrders.value = []; return }
  try {
    dayOrders.value = await getDayOrders(selectedDay.value, lineCode.value)
  } catch { dayOrders.value = [] }
}

function selectDay(iso: string) {
  if (!iso) return
  selectedDay.value = iso
  loadDayOrders()
}

function utilClass(u: number, isWorkday: boolean) {
  if (!isWorkday) return 'rest'
  if (u >= 100) return 'over'
  if (u >= 90) return 'warn'
  return 'ok'
}

const selectedInfo = computed(() => {
  const days: any[] = brief.value?.days ?? []
  return days.find((d) => d.date === selectedDay.value)
})

const linesFlat = computed(() => factories.value.flatMap((f: any) => f.lines))

onMounted(async () => {
  try { factories.value = await getFactories() } catch { /* ignore */ }
  await load()
})

watch(month, load)

/** 工厂切换 ActionSheet */
const showLineSheet = ref(false)
</script>

<template>
  <div class="page">
    <!-- 顶部 -->
    <header class="m-header">
      <div class="brand">
        <span class="brand-logo">CM</span>
        <div>
          <div class="brand-name sm">ContainerMind</div>
          <div class="brand-title">排产查看</div>
        </div>
      </div>
      <button class="line-btn" @click="showLineSheet = true">
        <Building2 :size="14" />
        <span>{{ lineName }}</span>
        <ChevronDown :size="13" />
      </button>
    </header>

    <main class="content">
      <!-- 月份选择器 -->
      <section class="month-bar">
        <button class="round" @click="shiftMonth(-1)"><ChevronLeft :size="16" /></button>
        <b>{{ month.replace('-', ' 年 ') }} 月</b>
        <button class="round" @click="shiftMonth(1)"><ChevronRight :size="16" /></button>
      </section>

      <!-- KPI 概览 -->
      <section class="kpi-card">
        <div class="kpi-row">
          <div class="kpi">
            <label>本月计划</label>
            <b>{{ brief?.plan_teu?.toLocaleString() ?? '—' }} <i>TEU</i></b>
          </div>
          <div class="kpi">
            <label>已排</label>
            <b class="primary">{{ brief?.scheduled_teu?.toLocaleString() ?? '—' }} <i>TEU</i></b>
          </div>
        </div>
        <div class="kpi-main">
          <span class="big">{{ brief?.utilization_rate ?? 0 }}%</span>
          <div class="kpi-side">
            <label>产能利用率</label>
            <span>剩余空位 {{ brief?.remaining_teu?.toLocaleString() ?? '—' }} TEU</span>
          </div>
        </div>
        <div class="progress">
          <div class="progress-fill" :style="{ width: Math.min(brief?.utilization_rate ?? 0, 100) + '%' }" />
        </div>
        <div class="kpi-foot">
          <span>工作日 {{ brief?.workdays ?? '—' }} 天</span>
          <span v-if="brief?.conflict_days" class="warn-text">
            <AlertTriangle :size="12" /> 冲突 {{ brief.conflict_days }} 天
          </span>
        </div>
      </section>

      <!-- 周历 -->
      <section v-if="weekDays.length">
        <div class="sec-title">本周概览</div>
        <div class="week-strip">
          <button v-for="d in weekDays" :key="d.iso" class="week-day"
                  :class="{ today: d.isToday, selected: d.iso === selectedDay }"
                  @click="selectDay(d.iso)">
            <span class="dow">{{ d.dow }}</span>
            <span class="num">{{ d.num }}</span>
            <span class="bar"><i :style="{ width: Math.min(d.util, 100) + '%' }" /></span>
          </button>
        </div>
      </section>

      <!-- 日历列表 -->
      <section>
        <div class="sec-title row">
          <span>{{ month.slice(5) }} 月排产日历</span>
          <span class="muted small">计划工时默认 8h</span>
        </div>
        <div v-if="loading" class="loading">加载中…</div>
        <div v-else class="day-list">
          <button v-for="d in brief?.days ?? []" :key="d.date" class="day-item"
                  :class="{ selected: d.date === selectedDay, today: d.date === new Date().toISOString().slice(0, 10) }"
                  @click="selectDay(d.date)">
            <div class="d-left">
              <b class="d-num">{{ d.day }}</b>
              <span class="d-dow">{{ d.day_of_week }}</span>
            </div>
            <span class="m-badge" :class="d.is_workday ? 'primary' : 'muted'">{{ d.is_workday ? '班' : '休' }}</span>
            <span class="d-hours">{{ d.is_workday ? d.hours + 'h' : '—' }}</span>
            <div class="d-bar">
              <i :class="utilClass(d.utilization, d.is_workday)"
                 :style="{ width: Math.min(d.utilization, 100) + '%' }" />
            </div>
            <span class="d-util" :class="utilClass(d.utilization, d.is_workday)">
              <AlertTriangle v-if="d.utilization >= 95" :size="11" />
              {{ d.utilization }}%
            </span>
          </button>
        </div>
      </section>

      <!-- 选中日工令 -->
      <section v-if="selectedDay" class="detail-card">
        <div class="dc-head">
          <div>
            <div class="dc-title">{{ selectedDay }} 工令</div>
            <div class="dc-sub">已选日期 · {{ selectedInfo?.day_of_week ?? '' }} · 计划 {{ selectedInfo?.hours ?? 11 }}h</div>
          </div>
          <span class="m-badge primary">已确认</span>
        </div>
        <div v-if="!dayOrders.length" class="dc-empty">
          <CalendarDays :size="20" />
          <span>当日暂无排产工令</span>
        </div>
        <div v-for="o in dayOrders" :key="o.work_order_no" class="wo">
          <Container :size="15" class="wo-icon" />
          <div class="wo-main">
            <b>{{ o.work_order_no }}</b>
            <span>{{ o.qty }} 台 · {{ o.teu }} TEU</span>
          </div>
        </div>
      </section>

      <!-- 只读提示 -->
      <div class="readonly-hint">
        <Info :size="13" />
        <span>移动端仅可查看，编辑请使用 PC 端排产工作台。</span>
      </div>
    </main>

    <!-- 产线切换 -->
    <van-action-sheet v-model:show="showLineSheet" title="切换产线" :actions="linesFlat.map((l: any) => ({ name: `${l.line_code} · ${l.line_name}`, value: l.line_code }))" @select="(a: any) => { lineCode = a.value; showLineSheet = false; selectedDay = ''; load() }" />
  </div>
</template>

<style scoped>
@import '@/styles/mobile.css';

.page { padding-top: 56px; }
.content { padding: 16px; display: flex; flex-direction: column; gap: 20px; }

.brand-name.sm { font-size: 10px; font-weight: 500; color: var(--cm-slate-400); line-height: 1.2; }
.brand-title { font-size: 15px; font-weight: 600; color: var(--cm-slate-800); line-height: 1.3; }
.line-btn {
  display: flex; align-items: center; gap: 4px; padding: 6px 10px; border-radius: 9999px;
  border: 1px solid var(--cm-border); background: var(--cm-card);
  font-size: 12px; color: var(--cm-slate-600); cursor: pointer;
}

/* 月份 */
.month-bar { display: flex; align-items: center; justify-content: center; gap: 16px; }
.month-bar b { font-size: 16px; font-weight: 600; color: var(--cm-slate-800); font-variant-numeric: tabular-nums; }
.round {
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--cm-border); background: var(--cm-card); color: var(--cm-slate-500); cursor: pointer;
}

/* KPI */
.kpi-card { background: linear-gradient(135deg, var(--cm-primary-700), var(--cm-primary-500)); border-radius: 14px; padding: 16px; color: #fff; }
.kpi-row { display: flex; gap: 24px; margin-bottom: 14px; }
.kpi label { display: block; font-size: 11px; opacity: 0.8; margin-bottom: 2px; }
.kpi b { font-size: 16px; font-weight: 600; font-variant-numeric: tabular-nums; }
.kpi b i { font-size: 10px; font-style: normal; opacity: 0.8; }
.kpi-main { display: flex; align-items: center; gap: 14px; }
.kpi-main .big { font-size: 36px; font-weight: 700; line-height: 1; font-variant-numeric: tabular-nums; }
.kpi-side { display: flex; flex-direction: column; gap: 3px; font-size: 11px; opacity: 0.85; }
.kpi-side label { font-size: 12px; }
.progress { height: 6px; border-radius: 9999px; background: rgba(255, 255, 255, 0.25); margin-top: 12px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 9999px; background: #fff; transition: width 0.4s; }
.kpi-foot { display: flex; justify-content: space-between; margin-top: 8px; font-size: 11px; opacity: 0.85; }
.warn-text { display: inline-flex; align-items: center; gap: 3px; }

/* 周历 */
.week-strip { display: flex; gap: 6px; overflow-x: auto; scrollbar-width: none; }
.week-strip::-webkit-scrollbar { display: none; }
.week-day {
  flex: 1; min-width: 44px; border-radius: 10px; padding: 8px 4px; text-align: center;
  background: var(--cm-card); border: 1px solid var(--cm-border); cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
}
.week-day.selected { border-color: var(--cm-primary); box-shadow: 0 0 0 2px var(--cm-primary-100); }
.week-day.today .num { background: var(--cm-primary); color: #fff; border-radius: 50%; width: 22px; height: 22px; line-height: 22px; }
.week-day .dow { font-size: 10px; color: var(--cm-slate-400); }
.week-day .num { font-size: 14px; font-weight: 600; color: var(--cm-slate-700); font-variant-numeric: tabular-nums; }
.week-day .bar { width: 100%; height: 3px; border-radius: 2px; background: var(--cm-slate-100); overflow: hidden; }
.week-day .bar i { display: block; height: 100%; background: var(--cm-primary-400); }

/* 日历列表 */
.sec-title.row { display: flex; justify-content: space-between; align-items: center; }
.loading { text-align: center; color: var(--cm-slate-400); font-size: 13px; padding: 20px 0; }
.day-list { display: flex; flex-direction: column; gap: 6px; }
.day-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px;
  background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 10px;
  cursor: pointer; text-align: left;
}
.day-item.selected { border-color: var(--cm-primary); box-shadow: 0 0 0 2px var(--cm-primary-100); }
.day-item.today .d-num { color: var(--cm-primary); }
.d-left { display: flex; align-items: baseline; gap: 4px; width: 56px; }
.d-num { font-size: 16px; font-weight: 600; color: var(--cm-slate-800); font-variant-numeric: tabular-nums; }
.d-dow { font-size: 10px; color: var(--cm-slate-400); }
.d-hours { font-size: 11px; color: var(--cm-slate-500); width: 28px; text-align: right; font-variant-numeric: tabular-nums; }
.d-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--cm-slate-100); overflow: hidden; }
.d-bar i { display: block; height: 100%; border-radius: 3px; }
.d-bar i.ok { background: var(--cm-primary-500); }
.d-bar i.warn { background: var(--cm-state-warning); }
.d-bar i.over { background: var(--cm-state-error); }
.d-bar i.rest { background: var(--cm-slate-300); }
.d-util { display: inline-flex; align-items: center; gap: 2px; width: 52px; justify-content: flex-end; font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
.d-util.ok { color: var(--cm-primary-600); }
.d-util.warn { color: var(--cm-state-warning); }
.d-util.over { color: var(--cm-state-error); }
.d-util.rest { color: var(--cm-slate-400); font-weight: 400; }

/* 详情卡 */
.detail-card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 12px; padding: 14px; }
.dc-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.dc-title { font-size: 15px; font-weight: 600; color: var(--cm-slate-800); font-variant-numeric: tabular-nums; }
.dc-sub { font-size: 11px; color: var(--cm-slate-400); margin-top: 2px; }
.dc-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 16px 0; color: var(--cm-slate-400); font-size: 12px; }
.wo { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: 8px; background: var(--cm-slate-50); }
.wo + .wo { margin-top: 8px; }
.wo-icon { color: var(--cm-primary); flex-shrink: 0; }
.wo-main { display: flex; flex-direction: column; gap: 2px; }
.wo-main b { font-size: 13px; font-weight: 600; color: var(--cm-slate-700); font-variant-numeric: tabular-nums; }
.wo-main span { font-size: 11px; color: var(--cm-slate-500); }

/* 只读提示 */
.readonly-hint {
  display: flex; align-items: center; gap: 6px; justify-content: center;
  font-size: 11px; color: var(--cm-slate-400); padding: 4px 0 8px;
}
.muted { color: var(--cm-slate-400); }
.small { font-size: 11px; font-weight: 400; }
</style>
