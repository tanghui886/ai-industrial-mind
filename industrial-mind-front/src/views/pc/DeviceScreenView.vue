<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import { getDeviceScreen } from '@/api'
import {
  Cpu, Activity, AlertTriangle, AlertOctagon, HeartPulse, BarChart3, BellRing,
} from 'lucide-vue-next'

const loading = ref(true)
const data = ref<any>(null)
let trendChart: echarts.ECharts | null = null
let typeChart: echarts.ECharts | null = null

const statusTag: Record<string, string> = { 正常: 'cm-tag-success', 预警: 'cm-tag-warning', 警告: 'cm-tag-warning', 故障: 'cm-tag-error' }

async function load() {
  loading.value = true
  try {
    data.value = await getDeviceScreen()
    setTimeout(renderCharts, 0)
  } finally { loading.value = false }
}

function renderCharts() {
  renderTrend()
  renderType()
}

function renderTrend() {
  const el = document.getElementById('deviceTrendChart')
  if (!el || !data.value?.trend) return
  trendChart = trendChart || echarts.init(el)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: data.value.trend.map((t: any) => t.time), boundaryGap: false, axisLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b', interval: 3 } },
    yAxis: { type: 'value', name: '条', nameTextStyle: { color: '#64748b' }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#64748b' } },
    series: [{
      name: '异常告警', type: 'line', data: data.value.trend.map((t: any) => t.count),
      smooth: true, symbol: 'none', lineStyle: { width: 3, color: '#ef4444' },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(239,68,68,.25)' }, { offset: 1, color: 'rgba(239,68,68,0)' }] } },
    }],
  })
}

function renderType() {
  const el = document.getElementById('deviceTypeChart')
  if (!el || !data.value?.abnormal_types) return
  typeChart = typeChart || echarts.init(el)
  typeChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 次' },
    xAxis: { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'category', data: data.value.abnormal_types.map((t: any) => t.type).reverse(), axisLine: { show: false }, axisLabel: { color: '#475569' } },
    series: [{
      type: 'bar', data: data.value.abnormal_types.map((t: any) => t.count).reverse(),
      barWidth: 14, itemStyle: { color: '#f97316', borderRadius: [0, 7, 7, 0] }, label: { show: true, position: 'right', color: '#64748b' },
    }],
  })
}

function onResize() { trendChart?.resize(); typeChart?.resize() }

onMounted(() => { load(); window.addEventListener('resize', onResize) })
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose(); typeChart?.dispose()
})
</script>

<template>
  <div v-loading="loading">
    <section class="cm-kpi-row">
      <article class="cm-kpi-card">
        <div class="kpi-label">设备总数</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.kpi?.total ?? '-' }}</span><span class="kpi-unit">台</span></div>
        <div class="kpi-trend text-muted">覆盖 5 条产线</div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">运行正常</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-success">{{ data?.kpi?.online ?? '-' }}</span><span class="kpi-unit">台</span></div>
        <div class="kpi-trend text-success"><Activity :size="13" /><span>在线率 {{ ((data?.kpi?.online / (data?.kpi?.total || 1)) * 100).toFixed(1) }}%</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">预警 / 警告</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-warning">{{ data?.kpi?.warn ?? '-' }}</span><span class="kpi-unit">台</span></div>
        <div class="kpi-trend text-warning"><AlertTriangle :size="13" /><span>需关注</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">故障设备</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-error">{{ data?.kpi?.fault ?? '-' }}</span><span class="kpi-unit">台</span></div>
        <div class="kpi-trend text-error"><AlertOctagon :size="13" /><span>需立即处理</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">平均健康度</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-primary">{{ data?.kpi?.avg_health ?? '-' }}</span><span class="kpi-unit text-primary">分</span></div>
        <div class="kpi-trend text-muted"><HeartPulse :size="13" /><span>综合健康指数</span></div>
      </article>
    </section>

    <main class="cm-sgrid">
      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><Cpu :size="18" class="text-primary" /><h2>各产线设备状态分布</h2></div>
        </div>
        <div class="cm-line-list">
          <div v-for="l in data?.by_line ?? []" :key="l.line_code" class="cm-line-card">
            <div class="line-head">
              <span class="line-code">{{ l.line_code }}</span>
              <span class="text-muted small">{{ l.line_name }}</span>
            </div>
            <div class="cm-line-card-stats">
              <div><div class="text-muted small">共</div><div class="cm-tabular num-strong">{{ l.total }}</div></div>
              <div><div class="text-muted small">正常</div><div class="cm-tabular num-strong text-success">{{ l.normal }}</div></div>
              <div><div class="text-muted small">预警</div><div class="cm-tabular num-strong text-warning">{{ l.warn }}</div></div>
              <div><div class="text-muted small">故障</div><div class="cm-tabular num-strong text-error">{{ l.fault }}</div></div>
            </div>
          </div>
        </div>
      </section>

      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><BarChart3 :size="18" class="text-primary" /><h2>24 小时异常告警趋势</h2></div>
        </div>
        <div id="deviceTrendChart" style="width:100%; height:260px;"></div>
      </section>

      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><Activity :size="18" class="text-primary" /><h2>异常类型分布</h2></div>
        </div>
        <div id="deviceTypeChart" style="width:100%; height:260px;"></div>
      </section>

      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><BellRing :size="18" class="text-primary" /><h2>实时异常告警</h2></div>
          <span class="text-error small fw500">{{ data?.alerts?.length ?? 0 }} 条</span>
        </div>
        <div class="cm-alert-list">
          <div v-for="(a, i) in data?.alerts ?? []" :key="i" class="cm-alert-item">
            <span class="cm-tag" :class="a.level==='严重'?'cm-tag-error':a.level==='警告'?'cm-tag-warning':'cm-tag-info'">{{ a.level }}</span>
            <div class="flex-1">
              <div class="alert-title">{{ a.message }}</div>
              <div class="cm-alert-meta">
                <span>{{ a.line_code }}</span><span>·</span>
                <span class="mono">{{ a.device_id }}</span><span>·</span>
                <span>{{ a.time }}</span><span>·</span>
                <span class="text-muted">{{ a.status }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.cm-kpi-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; padding: 16px 24px 0; }
.cm-kpi-card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: var(--cm-radius-medium); padding: 16px; min-height: 92px; box-shadow: var(--cm-shadow-1); }
.kpi-label { font-size: 13px; color: var(--cm-muted-foreground); margin-bottom: 4px; }
.kpi-line { display: flex; align-items: flex-end; gap: 8px; }
.kpi-num { font-size: 24px; }
.kpi-unit { font-size: 13px; color: var(--cm-muted-foreground); margin-bottom: 3px; }
.kpi-trend { margin-top: 8px; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.cm-sgrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding: 16px 24px 24px; }
.title-with-icon { display: flex; align-items: center; gap: 8px; }
.small { font-size: 12px; }
.fw500 { font-weight: 500; }
.text-muted { color: var(--cm-muted-foreground); }
.cm-line-list { display: flex; flex-direction: column; gap: 12px; }
.cm-line-card { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: var(--cm-slate-50); border: 1px solid var(--cm-border); border-radius: var(--cm-radius-medium); }
.line-head { display: flex; align-items: center; gap: 12px; }
.line-code { font-weight: 600; }
.cm-line-card-stats { display: flex; gap: 24px; text-align: right; flex-shrink: 0; }
.num-strong { font-weight: 600; }
.cm-alert-list { display: flex; flex-direction: column; }
.cm-alert-item { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--cm-border); }
.cm-alert-item:last-child { border-bottom: none; }
.alert-title { font-size: 14px; font-weight: 500; }
.cm-alert-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--cm-slate-500); margin-top: 4px; }
.flex-1 { flex: 1; min-width: 0; }
.mono { font-family: var(--cm-font-mono); }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.cm-tag-success { background: var(--cm-state-success-bg, #e6f7ed); color: var(--cm-state-success, #16a34a); }
.cm-tag-warning { background: var(--cm-state-warning-bg, #fef3c7); color: var(--cm-state-warning, #d97706); }
.cm-tag-error { background: var(--cm-state-error-bg, #fee2e2); color: var(--cm-state-error, #dc2626); }
.cm-tag-info { background: var(--cm-primary-50, #e0f2fe); color: var(--cm-primary, #0891b2); }
.text-success { color: var(--cm-state-success, #16a34a); }
.text-warning { color: var(--cm-state-warning, #d97706); }
.text-error { color: var(--cm-state-error, #dc2626); }
.text-primary { color: var(--cm-primary); }
@media (max-width: 1279px) {
  .cm-kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .cm-sgrid { grid-template-columns: 1fr; }
}
</style>