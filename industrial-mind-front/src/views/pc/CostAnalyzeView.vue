<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Sparkles, Layers, RefreshCw } from 'lucide-vue-next'
import { analyzeCost, getCostOptions } from '@/api'

const loading = ref(false)
const result = ref<any>(null)
const options = ref<any>({ work_orders: [], customers: [], box_types: [] })
const mode = ref<'work_order' | 'customer' | 'box_type' | 'all'>('work_order')
const form = ref({ work_order_no: '', customer: '', box_type: '' })

const DIM_COLORS: Record<string, string> = {
  采购: '#0891b2', 直接材料: '#2563eb', 人工成本: '#7c3aed', 制造费用: '#f97316', 交付成本: '#16a34a',
}
const dimColor = (d: string) => DIM_COLORS[d] || '#64748b'

const MODE_OPTIONS = [
  { value: 'work_order', label: '单个工令' },
  { value: 'customer', label: '单个客户全部工令' },
  { value: 'box_type', label: '按箱型全部工令' },
  { value: 'all', label: '全部工令' },
]

async function run(force = false) {
  if (mode.value === 'work_order' && !form.value.work_order_no) { ElMessage.warning('请选择工令号'); return }
  if (mode.value === 'customer' && !form.value.customer) { ElMessage.warning('请选择客户'); return }
  if (mode.value === 'box_type' && !form.value.box_type) { ElMessage.warning('请选择箱型'); return }
  if (force) {
    const scopeLabel = mode.value === 'work_order' ? `工令 ${form.value.work_order_no}`
      : mode.value === 'customer' ? `客户「${form.value.customer}」`
      : mode.value === 'box_type' ? `箱型「${form.value.box_type}」` : '全部工令'
    const ok = await ElMessageBox.confirm(
      `将清理「${scopeLabel}」范围内已分析的历史记录并重新分析，是否继续？`,
      '重新分析确认', { type: 'warning', confirmButtonText: '重新分析', cancelButtonText: '取消' }
    ).catch(() => false)
    if (!ok) return
  }
  loading.value = true
  result.value = null
  try {
    const params: any = { mode: mode.value, force }
    if (mode.value === 'work_order') params.work_order_no = form.value.work_order_no
    if (mode.value === 'customer') params.customer = form.value.customer
    if (mode.value === 'box_type') params.box_type = form.value.box_type
    result.value = await analyzeCost(params)
  } catch (e: any) { ElMessage.error(e.message) }
  finally { loading.value = false }
}

onMounted(async () => { options.value = await getCostOptions() })
</script>

<template>
  <div class="analyze-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">成本动因分析</h1>
        <p class="page-sub">按同客户 + 同箱型基准比对，支持多范围分析，结果按最小工令维度保存</p>
      </div>
    </section>

    <section class="card">
      <div class="analyze-form">
        <div class="mode-picker">
          <button v-for="m in MODE_OPTIONS" :key="m.value" class="mode-btn"
                  :class="{ active: mode === m.value }" @click="mode = m.value as any">{{ m.label }}</button>
        </div>
        <div class="input-bar">
          <el-select v-if="mode === 'work_order'" v-model="form.work_order_no" placeholder="选择工令号" filterable style="flex:1">
            <el-option v-for="w in options.work_orders" :key="w" :label="w" :value="w" />
          </el-select>
          <el-select v-if="mode === 'customer'" v-model="form.customer" placeholder="选择客户" filterable style="flex:1">
            <el-option v-for="c in options.customers" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-if="mode === 'box_type'" v-model="form.box_type" placeholder="选择箱型" style="flex:1">
            <el-option v-for="b in options.box_types" :key="b" :label="b" :value="b" />
          </el-select>
          <span v-if="mode === 'all'" class="text-muted">分析全部工令（不选择维度）</span>
          <button class="btn primary" @click="run(false)"><Search :size="15" /> 分析</button>
          <button class="btn" @click="run(true)"><RefreshCw :size="15" /> 重新分析</button>
        </div>
      </div>
    </section>

    <section v-if="result" class="result-grid">
      <!-- LLM 分析总结 -->
      <div class="card llm-card">
        <div class="card-title"><Sparkles :size="16" class="text-primary" /> AI 分析总结</div>
        <div class="llm-content" v-html="result.llm_analysis?.replace(/\n/g, '<br>')"></div>
      </div>

      <!-- 工令级结果列表 -->
      <div class="card table-card">
        <div class="card-title">
          <Layers :size="16" class="text-primary" /> 工令级分析结果
          <span class="title-meta">{{ result.scope_desc }} · 共 {{ result.items.length }} 个新工令 · 已保存 {{ result.saved_count }} 条 · 跳过 {{ result.skipped_count || 0 }} 个已分析工令<span v-if="result.force_note" class="force-note">{{ result.force_note }}</span></span>
        </div>
        <el-table :data="result.items" style="width:100%" size="small" :row-key="(r: any) => r.work_order_no">
          <el-table-column type="expand">
            <template #default="{ row }">
              <el-table :data="row.deltas" size="small" style="width:100%; padding: 0 12px;">
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
        </el-table>
        <p v-if="!result.items.length" class="empty-tip">该范围内工令均已分析过，可在「分析明细」查看历史结果</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.analyze-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 16px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.title-meta { font-size: 12px; font-weight: 400; color: var(--cm-muted-foreground); }
.force-note { margin-left: 8px; color: var(--cm-state-error, #dc2626); font-weight: 500; }
.analyze-form { display: flex; flex-direction: column; gap: 12px; }
.mode-picker { display: inline-flex; border: 1px solid var(--cm-border); border-radius: 8px; overflow: hidden; align-self: flex-start; }
.mode-btn { border: none; background: transparent; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; color: var(--cm-slate-600); }
.mode-btn.active { background: var(--cm-primary); color: #fff; }
.input-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.text-muted { color: var(--cm-muted-foreground); font-size: 13px; }
.result-grid { display: grid; gap: 16px; margin-top: 16px; }
.llm-card { grid-column: 1 / -1; }
.table-card { grid-column: 1 / -1; }
.llm-content { font-size: 14px; line-height: 1.75; color: var(--cm-foreground); white-space: pre-wrap; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.tag-badge { display: inline-block; padding: 2px 10px; background: var(--cm-primary-50, #e0f2fe); color: var(--cm-primary, #0891b2); border-radius: 6px; font-size: 12px; font-weight: 500; }
.mono { font-family: var(--cm-font-mono); font-size: 12px; }
.text-error { color: var(--cm-state-error, #dc2626); }
.text-success { color: var(--cm-state-success, #16a34a); }
.text-primary { color: var(--cm-primary); }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 24px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid var(--cm-border); background: var(--cm-card); }
.btn.primary { background: var(--cm-primary); color: #fff; border-color: transparent; }
.btn.primary:hover { background: var(--cm-primary-700); }
</style>