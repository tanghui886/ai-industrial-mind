<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Pencil, Trash2, Wand2, Save, RefreshCw } from 'lucide-vue-next'
import {
  getCostBaselines, initCostBaseline, saveCostBaseline, updateCostBaseline,
  deleteCostBaseline, getCostOptions,
} from '@/api'

const loading = ref(false)
const baselines = ref<any[]>([])
const options = ref<any>({ work_orders: [], customers: [], box_types: [] })

// 配置模式：work_order=从工令带出, customer=从客户+箱型
const mode = ref<'work_order' | 'customer'>('work_order')
const woForm = ref({ work_order_no: '' })
const cbForm = ref({ customer: '', box_type: '' })
const form = ref<any>({ customer: '', box_type: '', source_work_order_no: '', remark: '' })
const factors = ref<any[]>([])
const dirty = ref(false)

const DIM_COLORS: Record<string, string> = {
  采购: '#0891b2', 直接材料: '#2563eb', 人工成本: '#7c3aed', 制造费用: '#f97316', 交付成本: '#16a34a',
}
const dimColor = (d: string) => DIM_COLORS[d] || '#64748b'

async function loadBaselines() {
  loading.value = true
  try { baselines.value = await getCostBaselines() } finally { loading.value = false }
}

function resetForm() {
  mode.value = 'work_order'
  woForm.value = { work_order_no: '' }
  cbForm.value = { customer: '', box_type: '' }
  form.value = { customer: '', box_type: '', source_work_order_no: '', remark: '' }
  factors.value = []
  dirty.value = false
}

async function initFromWorkOrder() {
  if (!woForm.value.work_order_no) { ElMessage.warning('请选择工令号'); return }
  loading.value = true
  try {
    const r = await initCostBaseline({ work_order_no: woForm.value.work_order_no })
    form.value.customer = r.customer
    form.value.box_type = r.box_type
    form.value.source_work_order_no = r.source_work_order_no
    factors.value = r.factors.slice()
    dirty.value = true
  } finally { loading.value = false }
}

async function initFromCustomer() {
  if (!cbForm.value.box_type) { ElMessage.warning('请选择箱型'); return }
  loading.value = true
  try {
    const r = await initCostBaseline({ customer: cbForm.value.customer, box_type: cbForm.value.box_type })
    form.value.customer = cbForm.value.customer
    form.value.box_type = r.box_type
    form.value.source_work_order_no = r.source_work_order_no || ''
    factors.value = r.factors.slice()
    dirty.value = true
    ElMessage.info(`已按「${r.mode === 'existing' ? '同客户基准' : '无客户同箱型/默认基准'}」初始化，可手工调整`)
  } finally { loading.value = false }
}

async function save() {
  if (!form.value.box_type) { ElMessage.warning('请先选择箱型'); return }
  if (!factors.value.length) { ElMessage.warning('请先初始化动因因子'); return }
  loading.value = true
  try {
    const payload = {
      customer: form.value.customer,
      box_type: form.value.box_type,
      source_work_order_no: form.value.source_work_order_no,
      remark: form.value.remark,
      factors: factors.value,
    }
    await saveCostBaseline(payload)
    ElMessage.success('基准已保存')
    dirty.value = false
    await loadBaselines()
  } finally { loading.value = false }
}

function editBaseline(b: any) {
  form.value = { customer: b.customer, box_type: b.box_type,
                 source_work_order_no: b.source_work_order_no, remark: b.remark || '' }
  factors.value = (b.factors || []).map((f: any) => ({ ...f }))
  mode.value = 'customer'
  cbForm.value = { customer: b.customer, box_type: b.box_type }
  dirty.value = true
}

async function onDelete(b: any) {
  try {
    await ElMessageBox.confirm(`确认删除基准「${b.customer || '无客户'} / ${b.box_type}」？`, '删除基准', { type: 'warning' })
    await deleteCostBaseline(b.id)
    ElMessage.success('已删除')
    await loadBaselines()
  } catch { /* cancel */ }
}

onMounted(async () => {
  options.value = await getCostOptions()
  await loadBaselines()
})
</script>

<template>
  <div class="baseline-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">动因明细基准配置</h1>
        <p class="page-sub">按「同客户 + 同箱型」维度设置各成本动因因子基准；无同客户历史订单时按「无客户同箱型」/默认基准初始化</p>
      </div>
      <button class="btn" @click="resetForm"><RefreshCw :size="15" /> 新建基准</button>
    </section>

    <div class="baseline-grid">
      <!-- 左侧：基准列表 -->
      <section class="card list-card">
        <div class="card-title">基准列表</div>
        <div class="bl-list">
          <div v-for="b in baselines" :key="b.id" class="bl-item">
            <div class="bl-main">
              <span class="cm-tag" :class="b.customer ? 'cm-tag-info' : 'cm-tag-muted'">{{ b.customer || '无客户' }}</span>
              <span class="bl-box">{{ b.box_type }}</span>
            </div>
            <div class="bl-meta">
              <span v-if="b.source_work_order_no" class="mono">来源：{{ b.source_work_order_no }}</span>
              <span v-else class="text-muted">来源：{{ b.customer ? '客户初始化' : '箱型默认' }}</span>
              <span v-if="b.remark" class="text-muted">{{ b.remark }}</span>
            </div>
            <div class="bl-actions">
              <button class="op-btn" @click="editBaseline(b)"><Pencil :size="14" /> 编辑</button>
              <button class="op-btn danger" @click="onDelete(b)"><Trash2 :size="14" /> 删除</button>
            </div>
          </div>
          <p class="empty-tip" v-if="!baselines.length">暂无基准配置</p>
        </div>
      </section>

      <!-- 右侧：配置表单 -->
      <section class="card cfg-card">
        <div class="card-title">基准配置</div>

        <div class="mode-toggle">
          <button class="mt-btn" :class="{ active: mode === 'work_order' }" @click="mode = 'work_order'">从工令带出</button>
          <button class="mt-btn" :class="{ active: mode === 'customer' }" @click="mode = 'customer'">从客户+箱型</button>
        </div>

        <div v-if="mode === 'work_order'" class="init-bar">
          <el-select v-model="woForm.work_order_no" placeholder="选择工令号" filterable style="flex:1">
            <el-option v-for="w in options.work_orders" :key="w" :label="w" :value="w" />
          </el-select>
          <button class="btn primary" @click="initFromWorkOrder"><Wand2 :size="15" /> 带出动因</button>
        </div>
        <div v-else class="init-bar">
          <el-select v-model="cbForm.customer" placeholder="客户（留空=无客户）" clearable filterable style="flex:1">
            <el-option v-for="c in options.customers" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-model="cbForm.box_type" placeholder="箱型" style="flex:1">
            <el-option v-for="b in options.box_types" :key="b" :label="b" :value="b" />
          </el-select>
          <button class="btn primary" @click="initFromCustomer"><Wand2 :size="15" /> 初始化</button>
        </div>

        <div class="snapshot" v-if="form.box_type">
          <span>客户：<b>{{ form.customer || '无客户' }}</b></span>
          <span>箱型：<b>{{ form.box_type }}</b></span>
          <span v-if="form.source_work_order_no" class="mono">来源工令：{{ form.source_work_order_no }}</span>
          <el-input v-model="form.remark" placeholder="备注（可选）" style="max-width: 220px" size="small" />
        </div>

        <el-table :data="factors" size="small" max-height="420" style="width:100%">
          <el-table-column label="动因大类" width="90" align="center">
            <template #default="{ row }">
              <span class="cm-tag" :style="{ background: dimColor(row.dimension) + '1a', color: dimColor(row.dimension) }">{{ row.dimension }}</span>
            </template>
          </el-table-column>
          <el-table-column label="业务场景" prop="scene" min-width="90" />
          <el-table-column label="成本动因" prop="driver" min-width="150" />
          <el-table-column label="单位" prop="unit" width="70" align="center" />
          <el-table-column label="基准值" width="140">
            <template #default="{ row }">
              <el-input-number v-model="row.value" :min="0" :controls="false" size="small" style="width:100%" />
            </template>
          </el-table-column>
        </el-table>
        <p class="empty-tip" v-if="!factors.length">请选择工令或客户+箱型初始化动因因子后手工调整</p>

        <div class="save-bar">
          <button class="btn primary" @click="save" :disabled="!dirty"><Save :size="15" /> 保存基准</button>
          <span v-if="dirty" class="dirty-tip">有未保存的调整</span>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.baseline-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.baseline-grid { display: grid; grid-template-columns: 340px minmax(0, 1fr); gap: 16px; align-items: start; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 16px; }
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.bl-list { display: flex; flex-direction: column; gap: 10px; }
.bl-item { border: 1px solid var(--cm-border); border-radius: 10px; padding: 12px; background: var(--cm-slate-50); }
.bl-main { display: flex; align-items: center; gap: 8px; }
.bl-box { font-weight: 600; font-size: 14px; }
.bl-meta { display: flex; flex-direction: column; gap: 2px; font-size: 12px; color: var(--cm-slate-500); margin: 8px 0; }
.bl-actions { display: flex; gap: 8px; }
.mode-toggle { display: inline-flex; border: 1px solid var(--cm-border); border-radius: 8px; overflow: hidden; margin-bottom: 12px; }
.mt-btn { border: none; background: transparent; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; color: var(--cm-slate-600); }
.mt-btn.active { background: var(--cm-primary); color: #fff; }
.init-bar { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.snapshot { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; background: var(--cm-slate-50); border: 1px dashed var(--cm-border); border-radius: 8px; padding: 10px 12px; margin-bottom: 12px; font-size: 13px; }
.save-bar { display: flex; align-items: center; gap: 12px; margin-top: 14px; }
.dirty-tip { font-size: 12px; color: var(--cm-state-warning, #d97706); }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid var(--cm-border); background: var(--cm-card); }
.btn.primary { background: var(--cm-primary); color: #fff; border-color: transparent; }
.btn.primary:hover { background: var(--cm-primary-700); }
.btn[disabled] { opacity: .5; cursor: not-allowed; }
.mono { font-family: var(--cm-font-mono); font-size: 12px; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.cm-tag-info { background: var(--cm-primary-50, #e0f2fe); color: var(--cm-primary, #0891b2); }
.cm-tag-muted { background: var(--cm-slate-100); color: var(--cm-slate-500); }
.op-btn { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--cm-slate-600); cursor: pointer; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; }
.op-btn:hover { background: var(--cm-muted); color: var(--cm-primary); }
.op-btn.danger:hover { color: var(--cm-state-error); }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 20px 0; }
.text-muted { color: var(--cm-muted-foreground); }
@media (max-width: 1080px) { .baseline-grid { grid-template-columns: 1fr; } }
</style>