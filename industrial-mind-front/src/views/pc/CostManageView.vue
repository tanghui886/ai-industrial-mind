<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Pencil, Trash2, Search, RefreshCw } from 'lucide-vue-next'
import { getCostDrivers, createCostDriver, updateCostDriver, deleteCostDriver, getCostWorkOrders, getLines, getCostOptions } from '@/api'

const loading = ref(false)
// 视图切换：dimension=维度明细, workorder=工令号明细
const view = ref<'dimension' | 'workorder'>('dimension')

// ---------- 维度明细视图 ----------
const rows = ref<any[]>([])
const periods = ref<string[]>([])
const dimLines = ref<any[]>([])
const dimWorkOrders = ref<string[]>([])
const query = ref({ dimension: '', period: '', line_code: '', work_order_no: '' })
const dialogVisible = ref(false)
const editing = ref<any | null>(null)
const form = ref<any>({ dimension: '采购', scene: '', driver: '', unit: '', period: '', value: 0, cost: 0, note: '' })

// ---------- 工令号明细视图 ----------
const workRows = ref<any[]>([])
const lines = ref<any[]>([])
const woQuery = ref({ line_code: '', month: '2026-08', keyword: '' })

const DIMENSIONS = ['采购', '直接材料', '人工成本', '制造费用', '交付成本']
const WO_DIMENSIONS = ['采购', '直接材料', '人工成本', '制造费用', '交付成本']
const DIM_COLORS: Record<string, string> = {
  采购: '#0891b2', 直接材料: '#2563eb', 人工成本: '#7c3aed', 制造费用: '#f97316', 交付成本: '#16a34a',
}
const dimColor = (d: string) => DIM_COLORS[d] || '#64748b'

// ---------- 维度明细 ----------
async function load() {
  loading.value = true
  try {
    const params: any = {}
    if (query.value.dimension) params.dimension = query.value.dimension
    if (query.value.period) params.period = query.value.period
    if (query.value.line_code) params.line_code = query.value.line_code
    if (query.value.work_order_no) params.work_order_no = query.value.work_order_no
    rows.value = await getCostDrivers(params)
  } finally { loading.value = false }
}

async function loadPeriods() {
  const all = await getCostDrivers()
  periods.value = [...new Set(all.map((r: any) => r.period).sort())]
}

async function loadDimOptions() {
  const opts = await getCostOptions()
  dimLines.value = opts.lines
  dimWorkOrders.value = opts.work_orders
}

function reset() {
  query.value = { dimension: '', period: '', line_code: '', work_order_no: '' }
  load()
}

// ---------- 工令号明细 ----------
async function loadWorkOrders() {
  loading.value = true
  try {
    const params: any = { month: woQuery.value.month }
    if (woQuery.value.line_code) params.line_code = woQuery.value.line_code
    if (woQuery.value.keyword.trim()) params.keyword = woQuery.value.keyword.trim()
    workRows.value = await getCostWorkOrders(params)
  } finally { loading.value = false }
}

function resetWorkOrders() {
  woQuery.value = { line_code: '', month: '2026-08', keyword: '' }
  loadWorkOrders()
}

function switchView(v: 'dimension' | 'workorder') {
  view.value = v
  if (v === 'workorder' && !lines.value.length) loadLines()
  v === 'dimension' ? load() : loadWorkOrders()
}

async function loadLines() {
  lines.value = await getLines()
}

// ---------- 维度明细 CRUD ----------
function openAdd() {
  editing.value = null
  form.value = { dimension: '采购', scene: '', driver: '', unit: '', period: '', value: 0, cost: 0, note: '' }
  dialogVisible.value = true
}

function openEdit(row: any) {
  editing.value = row
  form.value = {
    dimension: row.dimension, scene: row.scene, driver: row.driver, unit: row.unit,
    period: row.period, value: row.value, cost: row.cost, note: row.note || '',
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.driver.trim() || !form.value.period.trim()) {
    ElMessage.warning('请填写动因名称和期间'); return
  }
  try {
    const payload = { ...form.value }
    if (editing.value) {
      await updateCostDriver(editing.value.id, payload)
      ElMessage.success('动因数据已更新')
    } else {
      await createCostDriver(payload)
      ElMessage.success('动因数据已新增')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.driver}」${row.period} 数据？`, '删除动因数据', { type: 'warning' })
    await deleteCostDriver(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancel */ }
}

onMounted(async () => {
  await loadPeriods()
  await loadLines()
  await loadDimOptions()
  load()
})
</script>

<template>
  <div class="cost-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">成本动因管理</h1>
        <p class="page-sub">按采购 / 直接材料 / 人工成本 / 制造费用 / 交付成本维度维护动因数据，并按工令号查看各维度明细（mock 示例）</p>
      </div>
      <div class="head-right">
        <div class="view-toggle">
          <button class="vt-btn" :class="{ active: view === 'dimension' }" @click="switchView('dimension')">维度明细</button>
          <button class="vt-btn" :class="{ active: view === 'workorder' }" @click="switchView('workorder')">工令号明细</button>
        </div>
        <button v-if="view === 'dimension'" class="btn primary" @click="openAdd"><Plus :size="15" /> 新增动因数据</button>
      </div>
    </section>

    <!-- 维度明细视图 -->
    <section class="card" v-if="view === 'dimension'">
      <div class="filter-bar">
        <el-select v-model="query.line_code" placeholder="全部产线" clearable style="width: 160px" @change="load">
          <el-option v-for="l in dimLines" :key="l.line_code" :label="`${l.line_code} ${l.line_name}`" :value="l.line_code" />
        </el-select>
        <el-select v-model="query.work_order_no" placeholder="全部工令号" clearable filterable style="width: 190px" @change="load">
          <el-option v-for="w in dimWorkOrders" :key="w" :label="w" :value="w" />
        </el-select>
        <el-select v-model="query.dimension" placeholder="全部维度" clearable style="width: 140px" @change="load">
          <el-option v-for="d in DIMENSIONS" :key="d" :label="d" :value="d" />
        </el-select>
        <el-select v-model="query.period" placeholder="全部期间" clearable style="width: 130px" @change="load">
          <el-option v-for="p in periods" :key="p" :label="p" :value="p" />
        </el-select>
        <button class="btn primary" @click="load"><Search :size="14" /> 查询</button>
        <button class="btn" @click="reset"><RefreshCw :size="14" /> 重置</button>
        <span class="result-count">共 {{ rows.length }} 条</span>
      </div>

      <el-table :data="rows" style="width: 100%" stripe>
        <el-table-column label="产线" width="120">
          <template #default="{ row }">{{ row.line_code }} · {{ row.line_name }}</template>
        </el-table-column>
        <el-table-column label="工令号" width="170">
          <template #default="{ row }"><span class="mono">{{ row.work_order_no }}</span></template>
        </el-table-column>
        <el-table-column label="动因大类" width="100" align="center">
          <template #default="{ row }">
            <span class="cm-tag" :style="{ background: dimColor(row.dimension) + '1a', color: dimColor(row.dimension) }">{{ row.dimension }}</span>
          </template>
        </el-table-column>
        <el-table-column label="业务场景" prop="scene" min-width="100" />
        <el-table-column label="成本动因" prop="driver" min-width="170" />
        <el-table-column label="单位" prop="unit" width="80" align="center" />
        <el-table-column label="期间" prop="period" width="85" align="center">
          <template #default="{ row }"><span class="mono">{{ row.period }}</span></template>
        </el-table-column>
        <el-table-column label="动因值" width="110" align="right">
          <template #default="{ row }">{{ row.value }}</template>
        </el-table-column>
        <el-table-column label="成本(元)" width="120" align="right">
          <template #default="{ row }">{{ (row.cost ?? 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="备注" prop="note" min-width="110" />
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <button class="op-btn" @click="openEdit(row)"><Pencil :size="14" /> 编辑</button>
            <button class="op-btn danger" @click="onDelete(row)"><Trash2 :size="14" /> 删除</button>
          </template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!rows.length">暂无动因数据</p>
    </section>

    <!-- 工令号明细视图 -->
    <section class="card" v-else>
      <div class="filter-bar">
        <el-select v-model="woQuery.line_code" placeholder="全部产线" clearable style="width: 180px" @change="loadWorkOrders">
          <el-option v-for="l in lines" :key="l.line_code" :label="`${l.line_code} ${l.line_name}`" :value="l.line_code" />
        </el-select>
        <el-input v-model="woQuery.month" placeholder="期间，如 2026-08" style="width: 140px" clearable @keyup.enter="loadWorkOrders" @clear="loadWorkOrders" />
        <el-input v-model="woQuery.keyword" placeholder="工令号 / 客户 / 箱型" clearable style="width: 200px" @keyup.enter="loadWorkOrders" @clear="loadWorkOrders">
          <template #prefix><Search :size="14" /></template>
        </el-input>
        <button class="btn primary" @click="loadWorkOrders"><Search :size="14" /> 查询</button>
        <button class="btn" @click="resetWorkOrders"><RefreshCw :size="14" /> 重置</button>
        <span class="result-count">共 {{ workRows.length }} 个工令</span>
      </div>

      <el-table :data="workRows" style="width: 100%" stripe>
        <el-table-column label="工令号" width="170">
          <template #default="{ row }"><span class="mono">{{ row.work_order_no }}</span></template>
        </el-table-column>
        <el-table-column label="产线" width="130">
          <template #default="{ row }">{{ row.line_code }} · {{ row.line_name }}</template>
        </el-table-column>
        <el-table-column label="箱型" prop="box_type" width="100" />
        <el-table-column label="客户" prop="customer" min-width="120" />
        <el-table-column label="数量" prop="quantity" width="80" align="center" />
        <el-table-column label="期间" prop="period" width="90" align="center">
          <template #default="{ row }"><span class="mono">{{ row.period }}</span></template>
        </el-table-column>
        <el-table-column v-for="d in WO_DIMENSIONS" :key="d" :label="d + '(元)'" width="110" align="right">
          <template #default="{ row }">{{ (row.costs?.[d] ?? 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="合计(元)" width="120" align="right">
          <template #default="{ row }"><span class="num-strong">{{ (row.costs?.合计 ?? 0).toLocaleString() }}</span></template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!workRows.length">该期间暂无工令成本数据</p>
    </section>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑动因数据' : '新增动因数据'" width="520px">
      <el-form label-width="100px">
        <el-form-item label="成本维度">
          <el-select v-model="form.dimension" style="width: 100%">
            <el-option v-for="d in DIMENSIONS" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务场景">
          <el-input v-model="form.scene" placeholder="如 工令领料 / 能源费用-电费" />
        </el-form-item>
        <el-form-item label="成本动因">
          <el-input v-model="form.driver" placeholder="如 物料单价（移动加权平均）" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" placeholder="如 元/箱 / 吨 / kWh" />
        </el-form-item>
        <el-form-item label="期间">
          <el-input v-model="form.period" placeholder="如 2026-08" />
        </el-form-item>
        <el-form-item label="动因值">
          <el-input-number v-model="form.value" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成本(元)">
          <el-input-number v-model="form.cost" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.cost-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.view-toggle { display: inline-flex; border: 1px solid var(--cm-border); border-radius: 8px; overflow: hidden; background: var(--cm-muted); }
.vt-btn { border: none; background: transparent; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; color: var(--cm-slate-600); }
.vt-btn.active { background: var(--cm-primary); color: #fff; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.filter-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 16px; border-bottom: 1px solid var(--cm-border); }
.result-count { margin-left: auto; font-size: 13px; color: var(--cm-muted-foreground); }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid var(--cm-border); background: var(--cm-card); }
.btn.primary { background: var(--cm-primary); color: #fff; border-color: transparent; }
.btn.primary:hover { background: var(--cm-primary-700); }
.mono { font-family: var(--cm-font-mono); font-size: 13px; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.num-strong { font-weight: 600; }
.op-btn { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--cm-slate-600); cursor: pointer; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; }
.op-btn:hover { background: var(--cm-muted); color: var(--cm-primary); }
.op-btn.danger:hover { color: var(--cm-state-error); }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
</style>