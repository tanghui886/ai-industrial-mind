<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import { getDashboard } from '@/api'
import {
  Activity, BarChart3, HeartPulse, BellRing, TrendingUp, AlertCircle, Bell,
  AlertOctagon, AlertTriangle, Info,
} from 'lucide-vue-next'

const loading = ref(true)
const data = ref<any>(null)
const refreshedAt = ref('')
let chart: echarts.ECharts | null = null

const statusClass: Record<string, string> = {
  '运行': 'cm-status-running', '降速': 'cm-status-slow',
  '检修': 'cm-status-maint', '停机': 'cm-status-stop',
}
const healthColor = (h: number) => (h >= 85 ? 'bg-success' : h >= 70 ? 'bg-warning' : 'bg-error')
const healthText = (h: number) => (h >= 85 ? 'text-success' : h >= 70 ? 'text-warning' : 'text-error')
const levelIcon: Record<string, any> = { '严重': AlertOctagon, '警告': AlertTriangle, '提示': Info }
const levelColor: Record<string, string> = { '严重': 'text-error', '警告': 'text-warning', '提示': 'text-info' }
const statusColor: Record<string, string> = { '处理中': 'text-error', '待确认': 'text-warning', '已关闭': 'text-muted' }

async function load() {
  loading.value = true
  try {
    data.value = await getDashboard('PD-D')
    refreshedAt.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    setTimeout(renderChart, 0)
  } finally {
    loading.value = false
  }
}

function renderChart() {
  const el = document.getElementById('capacityChart')
  if (!el || !data.value) return
  chart = chart || echarts.init(el)
  const c = data.value.capacity_chart
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['计划产量', '实际产量'], bottom: 0, textStyle: { color: '#475569' } },
    grid: { left: '3%', right: '4%', bottom: '14%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: c.labels, axisLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', name: 'TEU', nameTextStyle: { color: '#64748b' }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#64748b' } },
    series: [
      { name: '计划产量', type: 'bar', data: c.plan, itemStyle: { color: '#cbd5e1', borderRadius: [4, 4, 0, 0] }, barWidth: '40%' },
      { name: '实际产量', type: 'line', data: c.actual, itemStyle: { color: '#0891b2' }, lineStyle: { width: 3 }, symbolSize: 6 },
    ],
  })
}

function onResize() { chart?.resize() }

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
})
</script>

<template>
  <div v-loading="loading">
    <!-- KPI 行 -->
    <section class="cm-kpi-row" aria-label="关键指标">
      <article class="cm-kpi-card">
        <div class="kpi-label">今日计划产量</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.kpi?.today_plan_teu ?? '-' }}</span><span class="kpi-unit">TEU</span></div>
        <div class="kpi-trend text-success"><TrendingUp :size="13" /><span>较昨日 +5.0%</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">实际产量</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.kpi?.today_actual_teu ?? '-' }}</span><span class="kpi-unit">TEU</span></div>
        <div class="kpi-trend text-warning"><AlertCircle :size="13" /><span>落后计划 {{ (data?.kpi?.today_plan_teu ?? 0) - (data?.kpi?.today_actual_teu ?? 0) }} TEU</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">产能达成率</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-primary">{{ data?.kpi?.achievement_rate ?? '-' }}</span><span class="kpi-unit text-primary">%</span></div>
        <div class="kpi-trend text-muted">目标 95%</div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">OEE</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.kpi?.oee ?? '-' }}</span><span class="kpi-unit">%</span></div>
        <div class="kpi-trend text-success"><TrendingUp :size="13" /><span>较昨日 +1.2%</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">设备在线率</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.kpi?.device_online_rate ?? '-' }}</span><span class="kpi-unit">%</span></div>
        <div class="kpi-trend text-muted">{{ data?.kpi?.device_online_text ?? '' }}</div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">未关闭异常</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-error">{{ data?.kpi?.open_alerts ?? '-' }}</span><span class="kpi-unit">条</span></div>
        <div class="kpi-trend text-error"><Bell :size="13" /><span>{{ data?.kpi?.severe_alerts ?? 0 }} 条严重</span></div>
      </article>
    </section>

    <main class="cm-dashboard-grid">
      <div class="cm-left-column">
        <!-- 产线状态 -->
        <section class="cm-card">
          <div class="cm-section-title">
            <div class="title-with-icon"><Activity :size="18" class="text-primary" /><h2>产线状态</h2></div>
            <span class="text-muted small">实时刷新 {{ refreshedAt }}</span>
          </div>
          <div class="cm-line-list">
            <div v-for="l in data?.line_status ?? []" :key="l.line_code" class="cm-line-card">
              <div class="cm-line-card-main">
                <div class="line-head">
                  <span class="cm-status-badge" :class="statusClass[l.status] || 'cm-status-running'">
                    <span class="dot"></span>{{ l.status }}
                  </span>
                  <span class="line-code">{{ l.line_code }}</span>
                  <span class="text-muted small">{{ l.factory }}</span>
                </div>
                <div class="text-muted line-desc">{{ l.current_model }}</div>
              </div>
              <div class="cm-line-card-stats">
                <div><div class="text-muted small">计划</div><div class="cm-tabular num-strong">{{ l.plan }}</div></div>
                <div><div class="text-muted small">实际</div><div class="cm-tabular num-strong text-primary">{{ l.actual }}</div></div>
                <div><div class="text-muted small">达成</div><div class="cm-tabular num-strong">{{ l.achievement }}</div></div>
              </div>
            </div>
          </div>
        </section>

        <!-- 产能达成图表 -->
        <section class="cm-card">
          <div class="cm-section-title">
            <div class="title-with-icon"><BarChart3 :size="18" class="text-primary" /><h2>产能达成</h2></div>
            <div class="legend-row">
              <span><span class="legend-box" style="background:#cbd5e1"></span>计划</span>
              <span><span class="legend-line" style="background:#0891b2"></span>实际</span>
            </div>
          </div>
          <div id="capacityChart" style="width:100%; height:320px;"></div>
        </section>
      </div>

      <div class="cm-right-column">
        <!-- 设备健康 -->
        <section class="cm-card">
          <div class="cm-section-title">
            <div class="title-with-icon"><HeartPulse :size="18" class="text-primary" /><h2>设备健康</h2></div>
            <span class="text-muted small">{{ data?.devices?.length ?? 0 }} 台关键设备</span>
          </div>
          <div class="cm-equipment-list">
            <div v-for="d in data?.devices ?? []" :key="d.device_id" class="cm-equipment-item">
              <div class="cm-equipment-row">
                <span class="eq-name">{{ d.name }}</span>
                <span class="eq-right">
                  <span class="num-strong" :class="healthText(d.health)">{{ d.health }}%</span>
                  <span class="cm-tag" :class="d.status === '正常' ? 'cm-tag-success' : d.status === '预警' ? 'cm-tag-warning' : 'cm-tag-error'">{{ d.status }}</span>
                </span>
              </div>
              <div class="cm-progress-bg"><div class="cm-progress-fill" :class="healthColor(d.health)" :style="{ width: d.health + '%' }"></div></div>
              <div class="small" :class="d.rul_note ? 'text-warning' : 'text-muted'">RUL 剩余 {{ (d.rul_hours ?? 0).toLocaleString() }} 小时<template v-if="d.rul_note"> · {{ d.rul_note }}</template></div>
            </div>
          </div>
        </section>

        <!-- 异常告警 -->
        <section class="cm-card">
          <div class="cm-section-title">
            <div class="title-with-icon"><BellRing :size="18" class="text-primary" /><h2>异常告警</h2></div>
            <span class="text-error small fw500">{{ data?.kpi?.open_alerts ?? 0 }} 未关闭</span>
          </div>
          <div class="cm-alert-list">
            <div v-for="(a, i) in data?.alerts ?? []" :key="i" class="cm-alert-item">
              <div class="mt-2"><component :is="levelIcon[a.level] || Info" :size="18" :class="levelColor[a.level] || 'text-info'" /></div>
              <div class="flex-1">
                <div class="alert-title">{{ a.message }}</div>
                <div class="cm-alert-meta">
                  <span>{{ a.time }}</span><span>·</span>
                  <span>负责：{{ a.source_agent }}</span><span>·</span>
                  <span :class="statusColor[a.status] || 'text-muted'">{{ a.status }}</span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.cm-kpi-row { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 16px; padding: 16px 24px 0; }
.cm-kpi-card {
  background: var(--cm-card); border: 1px solid var(--cm-border);
  border-radius: var(--cm-radius-medium); padding: 16px; min-height: 96px;
  box-shadow: var(--cm-shadow-1);
}
.kpi-label { font-size: 13px; color: var(--cm-muted-foreground); margin-bottom: 4px; }
.kpi-line { display: flex; align-items: flex-end; gap: 8px; }
.kpi-num { font-size: 24px; }
.kpi-unit { font-size: 13px; color: var(--cm-muted-foreground); margin-bottom: 3px; }
.kpi-trend { margin-top: 8px; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.cm-dashboard-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 16px; padding: 16px 24px 24px; }
.cm-left-column, .cm-right-column { display: flex; flex-direction: column; gap: 16px; }
.title-with-icon { display: flex; align-items: center; gap: 8px; }
.small { font-size: 12px; }
.fw500 { font-weight: 500; }
.text-muted { color: var(--cm-muted-foreground); }
.legend-row { display: flex; align-items: center; gap: 16px; font-size: 12px; color: var(--cm-muted-foreground); }
.legend-row > span { display: flex; align-items: center; gap: 4px; }
.legend-box { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.legend-line { width: 12px; height: 3px; border-radius: 2px; display: inline-block; }
.cm-line-list { display: flex; flex-direction: column; gap: 12px; }
.cm-line-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; background: var(--cm-slate-50);
  border: 1px solid var(--cm-border); border-radius: var(--cm-radius-medium);
}
.line-head { display: flex; align-items: center; gap: 12px; }
.line-code { font-weight: 600; }
.dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; display: inline-block; }
.line-desc { font-size: 13px; margin-top: 4px; }
.cm-line-card-stats { display: flex; gap: 24px; text-align: right; flex-shrink: 0; }
.num-strong { font-weight: 600; }
.cm-equipment-list { display: flex; flex-direction: column; gap: 16px; }
.cm-equipment-item { display: flex; flex-direction: column; gap: 8px; }
.cm-equipment-row { display: flex; align-items: center; justify-content: space-between; }
.eq-name { font-size: 14px; font-weight: 500; }
.eq-right { display: flex; align-items: center; gap: 8px; }
.eq-right .cm-tag { font-size: 12px; padding: 1px 8px; }
.cm-alert-list { display: flex; flex-direction: column; }
.cm-alert-item { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--cm-border); }
.cm-alert-item:last-child { border-bottom: none; }
.alert-title { font-size: 14px; font-weight: 500; }
.cm-alert-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--cm-slate-500); margin-top: 4px; }
.flex-1 { flex: 1; min-width: 0; }
.mt-2 { margin-top: 2px; }
@media (max-width: 1279px) {
  .cm-kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .cm-dashboard-grid { grid-template-columns: 1fr; }
}
</style>
