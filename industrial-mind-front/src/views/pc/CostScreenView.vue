<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import * as echarts from 'echarts'
import { getCostScreen, getCostOptions } from '@/api'
import { Wallet, Layers, TrendingUp, AlertTriangle, Boxes } from 'lucide-vue-next'

const loading = ref(true)
const data = ref<any>(null)
const options = ref<any>({ lines: [], work_orders: [] })
const screenQuery = ref({ line_code: '', work_order_no: '' })
let trendChart: echarts.ECharts | null = null

const DIM_COLORS: Record<string, string> = {
  采购: '#0891b2', 直接材料: '#2563eb', 人工成本: '#7c3aed', 制造费用: '#f97316', 交付成本: '#16a34a',
}
const dimColor = (d: string) => DIM_COLORS[d] || '#64748b'

async function load() {
  loading.value = true
  try {
    const params: any = {}
    if (screenQuery.value.line_code) params.line_code = screenQuery.value.line_code
    if (screenQuery.value.work_order_no) params.work_order_no = screenQuery.value.work_order_no
    data.value = await getCostScreen(params)
    setTimeout(renderTrend, 0)
  } finally { loading.value = false }
}

function renderTrend() {
  const el = document.getElementById('costTrendChart')
  if (!el || !data.value?.series) return
  trendChart = trendChart || echarts.init(el)
  const dims = Object.keys(data.value.series)
  trendChart.setOption({
    color: dims.map(dimColor),
    tooltip: { trigger: 'axis' },
    legend: { data: dims, bottom: 0, textStyle: { color: '#475569' } },
    grid: { left: '3%', right: '4%', bottom: '14%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: data.value.labels, axisLine: { lineStyle: { color: '#e2e8f0' } }, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', name: '万元', nameTextStyle: { color: '#64748b' }, axisLine: { show: false }, splitLine: { lineStyle: { color: '#f1f5f9' } }, axisLabel: { color: '#64748b' } },
    series: dims.map((d: string) => ({ name: d, type: 'line', smooth: true, symbolSize: 5, data: data.value.series[d] })),
  })
}

function onResize() { trendChart?.resize() }

onMounted(async () => {
  options.value = await getCostOptions()
  load()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  trendChart?.dispose()
})
</script>

<template>
  <div v-loading="loading">
    <section class="screen-filter">
      <el-select v-model="screenQuery.line_code" placeholder="全部产线" clearable style="width: 180px" @change="load">
        <el-option v-for="l in options.lines" :key="l.line_code" :label="`${l.line_code} ${l.line_name}`" :value="l.line_code" />
      </el-select>
      <el-select v-model="screenQuery.work_order_no" placeholder="全部工令号" clearable filterable style="width: 220px" @change="load">
        <el-option v-for="w in options.work_orders" :key="w" :label="w" :value="w" />
      </el-select>
      <span class="screen-scope" v-if="screenQuery.work_order_no || screenQuery.line_code">
        当前范围：{{ screenQuery.work_order_no || screenQuery.line_code || '全厂' }}
      </span>
    </section>

    <section class="cm-kpi-row">
      <article class="cm-kpi-card">
        <div class="kpi-label">单箱综合成本</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ (data?.total ?? 0).toLocaleString() }}</span><span class="kpi-unit">元/箱</span></div>
        <div class="kpi-trend text-muted"><Wallet :size="13" /><span>按分项汇总</span></div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">直接材料</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num text-primary">{{ data?.per_box?.[0]?.amount ?? '-' }}</span><span class="kpi-unit text-primary">元 · {{ data?.per_box?.[0]?.ratio }}</span></div>
        <div class="kpi-trend text-muted">物料单价×耗用量</div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">人工成本</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.per_box?.[1]?.amount ?? '-' }}</span><span class="kpi-unit">元 · {{ data?.per_box?.[1]?.ratio }}</span></div>
        <div class="kpi-trend text-muted">报工工时</div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">制造费用</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.per_box?.[2]?.amount ?? '-' }}</span><span class="kpi-unit">元 · {{ data?.per_box?.[2]?.ratio }}</span></div>
        <div class="kpi-trend text-muted">能源 / 折旧</div>
      </article>
      <article class="cm-kpi-card">
        <div class="kpi-label">交付成本</div>
        <div class="kpi-line"><span class="cm-kpi-value kpi-num">{{ data?.per_box?.[3]?.amount ?? '-' }}</span><span class="kpi-unit">元 · {{ data?.per_box?.[3]?.ratio }}</span></div>
        <div class="kpi-trend text-muted">堆存 / 运输 / 海运</div>
      </article>
    </section>

    <main class="cm-cgrid">
      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><Layers :size="18" class="text-primary" /><h2>单箱成本构成（元）</h2></div>
        </div>
        <div class="per-box-list">
          <div v-for="(c, i) in data?.per_box ?? []" :key="i" class="per-box-item">
            <div class="pb-head">
              <span class="pb-name">{{ c.item }}</span>
              <span class="pb-amount"><b>{{ c.amount.toLocaleString() }}</b> 元（{{ c.ratio }}）</span>
            </div>
            <div class="cm-progress-bg">
              <div class="cm-progress-fill" :style="{ width: c.ratio, background: dimColor(c.item) }"></div>
            </div>
            <div class="pb-driver text-muted small">动因：{{ c.driver }}</div>
          </div>
        </div>
      </section>

      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><TrendingUp :size="18" class="text-primary" /><h2>各维度成本月度趋势</h2></div>
        </div>
        <div id="costTrendChart" style="width:100%; height:300px;"></div>
      </section>

      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><Boxes :size="18" class="text-primary" /><h2>主要成本动因影响度</h2></div>
        </div>
        <div class="driver-list">
          <div v-for="(d, i) in data?.drivers ?? []" :key="i" class="driver-item">
            <div class="dr-head">
              <span class="dr-name">{{ d.name }}</span>
              <span class="dr-impact">
                <b>{{ d.impact }}%</b>
                <span class="cm-tag" :class="d.trend==='up'?'cm-tag-error':d.trend==='down'?'cm-tag-success':'cm-tag-muted'">
                  {{ d.trend==='up'?'↑ 上升':d.trend==='down'?'↓ 下降':'→ 平稳' }}
                </span>
              </span>
            </div>
            <div class="cm-progress-bg">
              <div class="cm-progress-fill" :style="{ width: (d.impact * 3) + '%', background: dimColor(d.dimension) }"></div>
            </div>
            <div class="text-muted small">维度：{{ d.dimension }}</div>
          </div>
        </div>
      </section>

      <section class="cm-card">
        <div class="cm-section-title">
          <div class="title-with-icon"><AlertTriangle :size="18" class="text-primary" /><h2>成本异常提示</h2></div>
        </div>
        <div class="cm-alert-list">
          <div v-for="(a, i) in data?.anomalies ?? []" :key="i" class="cm-alert-item">
            <span class="cm-tag" :class="a.level==='高'?'cm-tag-error':a.level==='中'?'cm-tag-warning':'cm-tag-info'">{{ a.level }}</span>
            <div class="flex-1 alert-title">{{ a.desc }}</div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.screen-filter { display: flex; align-items: center; gap: 12px; padding: 16px 24px 0; flex-wrap: wrap; }
.screen-scope { font-size: 13px; color: var(--cm-primary); font-weight: 500; }
.cm-kpi-row { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; padding: 16px 24px 0; }
.cm-kpi-card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: var(--cm-radius-medium); padding: 16px; min-height: 92px; box-shadow: var(--cm-shadow-1); }
.kpi-label { font-size: 13px; color: var(--cm-muted-foreground); margin-bottom: 4px; }
.kpi-line { display: flex; align-items: flex-end; gap: 8px; }
.kpi-num { font-size: 24px; }
.kpi-unit { font-size: 13px; color: var(--cm-muted-foreground); margin-bottom: 3px; }
.kpi-trend { margin-top: 8px; font-size: 12px; display: flex; align-items: center; gap: 4px; }
.cm-cgrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding: 16px 24px 24px; }
.title-with-icon { display: flex; align-items: center; gap: 8px; }
.small { font-size: 12px; }
.text-muted { color: var(--cm-muted-foreground); }
.text-primary { color: var(--cm-primary); }
.per-box-list, .driver-list { display: flex; flex-direction: column; gap: 16px; }
.per-box-item, .driver-item { display: flex; flex-direction: column; gap: 6px; }
.pb-head, .dr-head { display: flex; align-items: center; justify-content: space-between; }
.pb-name, .dr-name { font-size: 14px; font-weight: 500; }
.pb-amount { font-size: 13px; color: var(--cm-muted-foreground); }
.pb-amount b, .dr-impact b { color: var(--cm-foreground); font-size: 15px; }
.dr-impact { display: flex; align-items: center; gap: 8px; }
.cm-progress-bg { height: 8px; border-radius: 999px; background: var(--cm-slate-100); overflow: hidden; }
.cm-progress-fill { height: 100%; border-radius: 999px; }
.cm-alert-list { display: flex; flex-direction: column; }
.cm-alert-item { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--cm-border); align-items: flex-start; }
.cm-alert-item:last-child { border-bottom: none; }
.flex-1 { flex: 1; min-width: 0; }
.alert-title { font-size: 14px; line-height: 1.5; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.cm-tag-success { background: var(--cm-state-success-bg, #e6f7ed); color: var(--cm-state-success, #16a34a); }
.cm-tag-warning { background: var(--cm-state-warning-bg, #fef3c7); color: var(--cm-state-warning, #d97706); }
.cm-tag-error { background: var(--cm-state-error-bg, #fee2e2); color: var(--cm-state-error, #dc2626); }
.cm-tag-info { background: var(--cm-primary-50, #e0f2fe); color: var(--cm-primary, #0891b2); }
@media (max-width: 1279px) {
  .cm-kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .cm-cgrid { grid-template-columns: 1fr; }
}
</style>