<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getCostAnalysisRecords, getCostOptions, getCostAnalysisSummary } from '@/api'
import { Search, RefreshCw, Clock, AlertTriangle, Sparkles } from 'lucide-vue-next'

const loading = ref(false)
const records = ref<any[]>([])
const options = ref<any>({ work_orders: [], customers: [], box_types: [] })
const query = ref({ work_order_no: '', customer: '', box_type: '' })
const summary = ref<any>(null)

const DIM_COLORS: Record<string, string> = {
  采购: '#0891b2', 直接材料: '#2563eb', 人工成本: '#7c3aed', 制造费用: '#f97316', 交付成本: '#16a34a',
}
const dimColor = (d: string) => DIM_COLORS[d] || '#64748b'

async function load() {
  loading.value = true
  try {
    const params: any = {}
    if (query.value.work_order_no) params.work_order_no = query.value.work_order_no
    if (query.value.customer) params.customer = query.value.customer
    if (query.value.box_type) params.box_type = query.value.box_type
    records.value = await getCostAnalysisRecords(params)
  } finally { loading.value = false }
}

async function loadSummary() {
  try { summary.value = await getCostAnalysisSummary() } catch { /* 忽略 */ }
}

function reset() {
  query.value = { work_order_no: '', customer: '', box_type: '' }
  load()
}

onMounted(async () => {
  options.value = await getCostOptions()
  load()
  loadSummary()
})
</script>

<template>
  <div class="records-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">成本动因分析明细</h1>
        <p class="page-sub">历史分析过的工令列表（按最小工令维度保存，支持过滤查看）</p>
      </div>
    </section>

    <div class="main-grid">
      <!-- 左侧：历史分析工令列表 -->
      <section class="card list-card">
        <div class="filter-bar">
          <el-select v-model="query.work_order_no" placeholder="工令号" clearable filterable style="width: 190px" @change="load">
            <el-option v-for="w in options.work_orders" :key="w" :label="w" :value="w" />
          </el-select>
          <el-select v-model="query.customer" placeholder="客户" clearable filterable style="width: 150px" @change="load">
            <el-option v-for="c in options.customers" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-model="query.box_type" placeholder="箱型" clearable style="width: 130px" @change="load">
            <el-option v-for="b in options.box_types" :key="b" :label="b" :value="b" />
          </el-select>
          <button class="btn primary" @click="load"><Search :size="14" /> 查询</button>
          <button class="btn" @click="reset"><RefreshCw :size="14" /> 重置</button>
          <span class="result-count">共 {{ records.length }} 条</span>
        </div>

        <el-table :data="records" style="width:100%" size="small"
                  :row-key="(r: any) => r.work_order_no">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-content">
                <div class="llm-box" v-if="row.llm_analysis">
                  <div class="llm-label">AI 分析总结</div>
                  <div class="llm-text" v-html="row.llm_analysis.replace(/\n/g, '<br>')"></div>
                </div>
                <el-table :data="row.deltas" size="small" style="width:100%">
                  <el-table-column label="动因大类" width="90" align="center">
                    <template #default="{ row: d }">
                      <span class="cm-tag" :style="{ background: dimColor(d.dimension) + '1a', color: dimColor(d.dimension) }">{{ d.dimension }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="业务场景" prop="scene" min-width="80" />
                  <el-table-column label="成本动因" prop="driver" min-width="130" />
                  <el-table-column label="实际值" prop="value" width="90" align="right" />
                  <el-table-column label="基准值" prop="baseline" width="90" align="right" />
                  <el-table-column label="差异" width="90" align="right">
                    <template #default="{ row: d }">
                      <span :class="d.delta > 0 ? 'text-error' : d.delta < 0 ? 'text-success' : ''">{{ d.delta > 0 ? '+' : '' }}{{ d.delta }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column label="差异率" width="90" align="right">
                    <template #default="{ row: d }">
                      <span :class="d.delta_pct > 0 ? 'text-error' : d.delta_pct < 0 ? 'text-success' : ''">{{ d.delta_pct > 0 ? '+' : '' }}{{ d.delta_pct }}%</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="工令号" width="170">
            <template #default="{ row }"><span class="mono">{{ row.work_order_no }}</span></template>
          </el-table-column>
          <el-table-column label="客户" width="110">
            <template #default="{ row }">{{ row.customer || '无客户' }}</template>
          </el-table-column>
          <el-table-column label="箱型" prop="box_type" width="100" />
          <el-table-column label="比对基准" width="130">
            <template #default="{ row }"><span class="tag-badge">{{ row.baseline_kind }}</span></template>
          </el-table-column>
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }">
              <span :class="row.above_flag === '超基准' ? 'text-error' : 'text-success'">{{ row.above_flag }}</span>
            </template>
          </el-table-column>
          <el-table-column label="主要动因" prop="top_driver" min-width="120" />
          <el-table-column label="Top差异率" width="100" align="right">
            <template #default="{ row }">
              <span :class="row.top_delta_pct > 0 ? 'text-error' : ''">{{ row.top_delta_pct > 0 ? '+' : '' }}{{ row.top_delta_pct }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="分析时间" width="150">
            <template #default="{ row }">
              <span class="mono"><Clock :size="12" /> {{ row.analyzed_at?.slice(0, 16) || '-' }}</span>
            </template>
          </el-table-column>
        </el-table>
        <p class="empty-tip" v-if="!records.length">暂无历史分析记录</p>
      </section>

      <!-- 右侧：异常动因分析汇总 -->
      <aside class="card summary-card">
        <div class="card-title">
          <AlertTriangle :size="16" class="text-error" /> 异常动因分析汇总
        </div>
        <p class="summary-sub">历史分析过工令中「超基准」异常动因的汇总统计</p>

        <template v-if="summary">
          <div class="stat-row">
            <div class="stat"><span class="stat-num">{{ summary.total_analyzed }}</span><span class="stat-label">已分析工令</span></div>
            <div class="stat"><span class="stat-num text-error">{{ summary.total_abnormal }}</span><span class="stat-label">异常工令</span></div>
            <div class="stat"><span class="stat-num">{{ summary.driver_summary?.length || 0 }}</span><span class="stat-label">异常动因</span></div>
          </div>

          <div class="summary-block" v-if="summary.llm_summary">
            <div class="sub-label"><Sparkles :size="13" class="text-primary" /> AI 分析汇总</div>
            <div class="llm-text" v-html="summary.llm_summary.replace(/\n/g, '<br>')"></div>
          </div>

          <div class="summary-block" v-if="summary.driver_summary?.length">
            <div class="sub-label">Top 异常动因</div>
            <div class="driver-list">
              <div v-for="(d, i) in summary.driver_summary" :key="d.driver" class="driver-item">
                <span class="driver-rank">{{ i + 1 }}</span>
                <div class="driver-main">
                  <span class="cm-tag" :style="{ background: dimColor(d.dimension) + '1a', color: dimColor(d.dimension) }">{{ d.dimension }}</span>
                  <span class="driver-name">{{ d.driver }}</span>
                  <span class="driver-meta">出现 {{ d.count }} 次 · 涉及 {{ d.orders?.length }} 工令</span>
                </div>
                <span class="driver-pct text-error">{{ d.count ? (d.sum_delta_pct / d.count).toFixed(1) : 0 }}%</span>
              </div>
            </div>
          </div>

          <p v-else class="empty-tip">暂无异常工令数据</p>
        </template>
        <p v-else class="empty-tip">加载中…</p>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.records-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.main-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.list-card { min-width: 0; }
.summary-card { padding: 16px; position: sticky; top: 12px; }
.card-title { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.summary-sub { font-size: 12px; color: var(--cm-muted-foreground); margin: 4px 0 14px; }
.filter-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 16px; border-bottom: 1px solid var(--cm-border); }
.result-count { margin-left: auto; font-size: 13px; color: var(--cm-muted-foreground); }
.expand-content { padding: 12px 24px; }
.llm-box { border: 1px dashed var(--cm-border); border-radius: 8px; padding: 12px; margin-bottom: 12px; background: var(--cm-slate-50); }
.llm-label { font-size: 12px; font-weight: 600; color: var(--cm-primary); margin-bottom: 6px; }
.llm-text { font-size: 13.5px; line-height: 1.7; white-space: pre-wrap; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.tag-badge { display: inline-block; padding: 2px 10px; background: var(--cm-primary-50, #e0f2fe); color: var(--cm-primary, #0891b2); border-radius: 6px; font-size: 12px; font-weight: 500; }
.mono { font-family: var(--cm-font-mono); font-size: 12px; }
.text-error { color: var(--cm-state-error, #dc2626); }
.text-success { color: var(--cm-state-success, #16a34a); }
.text-primary { color: var(--cm-primary); }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid var(--cm-border); background: var(--cm-card); }
.btn.primary { background: var(--cm-primary); color: #fff; border-color: transparent; }
.btn.primary:hover { background: var(--cm-primary-700); }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
.stat-row { display: flex; gap: 8px; margin-bottom: 14px; }
.stat { flex: 1; text-align: center; border: 1px solid var(--cm-border); border-radius: 8px; padding: 10px 4px; }
.stat-num { display: block; font-size: 22px; font-weight: 700; }
.stat-label { font-size: 12px; color: var(--cm-muted-foreground); }
.sub-label { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--cm-foreground); margin-bottom: 8px; }
.summary-block { margin-bottom: 16px; padding-top: 12px; border-top: 1px dashed var(--cm-border); }
.driver-list { display: flex; flex-direction: column; gap: 8px; }
.driver-item { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid var(--cm-border); border-radius: 8px; }
.driver-rank { width: 20px; height: 20px; border-radius: 50%; background: var(--cm-slate-100, #f1f5f9); color: var(--cm-slate-600); font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.driver-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.driver-name { font-size: 13px; font-weight: 500; }
.driver-meta { font-size: 11px; color: var(--cm-muted-foreground); }
.driver-pct { font-size: 14px; font-weight: 700; flex-shrink: 0; }
</style>