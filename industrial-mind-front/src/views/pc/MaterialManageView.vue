<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Pencil, Trash2 } from 'lucide-vue-next'
import { getMaterialList, getMaterialStats, createMaterial, updateMaterial, deleteMaterial } from '@/api'

const loading = ref(false)
const rows = ref<any[]>([])
const stats = ref<any>({ total: {}, by_factory: [] })
const factoryFilter = ref('')
const dialogVisible = ref(false)
const editing = ref<any | null>(null)
const form = ref({ code: '', name: '', category: '', factory: 'DFQD', unit: '', stock_note: '', in_stock_units: 0, support_units: 0, in_transit_units: 0, purchase_units: 0, arrival_date: '', status: '充足' })

const STATUS_OPTIONS = ['充足', '需补货', '预警']
const statusTag: Record<string, string> = { 充足: 'tag-success', 需补货: 'tag-warning', 预警: 'tag-error' }
const FACTORY_OPTIONS = ['DFQD', 'DFSH', 'DFNT', 'DFLYG']

const filteredRows = ref<any[]>([])

function applyFilter() {
  filteredRows.value = factoryFilter.value
    ? rows.value.filter((r) => r.factory === factoryFilter.value)
    : rows.value
}

async function load() {
  loading.value = true
  try {
    rows.value = await getMaterialList()
    stats.value = await getMaterialStats()
    applyFilter()
  } finally { loading.value = false }
}

function openAdd() {
  editing.value = null
  form.value = { code: '', name: '', category: '', factory: 'DFQD', unit: '', stock_note: '', in_stock_units: 0, support_units: 0, in_transit_units: 0, purchase_units: 0, arrival_date: '', status: '充足' }
  dialogVisible.value = true
}

function openEdit(row: any) {
  editing.value = row
  form.value = {
    code: row.code, name: row.name, category: row.category, factory: row.factory || 'DFQD',
    unit: row.unit || '', stock_note: row.stock_note || '', in_stock_units: row.in_stock_units || 0,
    support_units: row.support_units || 0, in_transit_units: row.in_transit_units || 0, purchase_units: row.purchase_units || 0,
    arrival_date: row.arrival_date || '', status: row.status,
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.code.trim() || !form.value.name.trim()) {
    ElMessage.warning('请填写物料编码和名称'); return
  }
  const payload = {
    ...form.value,
    factory: form.value.factory || 'DFQD',
    arrival_date: form.value.arrival_date || null,
  }
  try {
    if (editing.value) {
      await updateMaterial(editing.value.id, payload)
      ElMessage.success('物料已更新')
    } else {
      await createMaterial(payload)
      ElMessage.success('物料已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function onDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除物料「${row.name}（${row.code}）」？`, '删除物料', { type: 'warning' })
    await deleteMaterial(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancel */ }
}

onMounted(load)
</script>

<template>
  <div class="material-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">物料维护</h1>
        <p class="page-sub">维护原材料与关键物料信息，供智能排产物料风险评估使用</p>
      </div>
      <div class="head-right">
        <button class="btn primary" @click="openAdd"><Plus :size="15" /> 新增物料</button>
      </div>
    </section>

    <section class="card stats-card">
      <div class="stats-head">物料数量统计</div>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-label">在库物料总量</span><span class="stat-value">{{ stats.total?.in_stock_units ?? 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">订单扣减量</span><span class="stat-value">{{ stats.total?.order_deducted_units ?? 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">在途量</span><span class="stat-value">{{ stats.total?.in_transit_units ?? 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">采购量</span><span class="stat-value">{{ stats.total?.purchase_units ?? 0 }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">转换台数</span><span class="stat-value">{{ stats.total?.support_units ?? 0 }}</span>
        </div>
      </div>
      <div class="stats-factory" v-if="(stats.by_factory || []).length">
        <span v-for="f in stats.by_factory" :key="f.factory" class="factory-chip">
          {{ f.factory }}：在库 {{ f.in_stock_units }} ｜ 在途 {{ f.in_transit_units }} ｜ 采购 {{ f.purchase_units }} ｜ 转换 {{ f.support_units }} 台
        </span>
      </div>
    </section>

    <section class="card">
      <div class="filter-bar">
        <el-select v-model="factoryFilter" placeholder="按工厂筛选" clearable style="width: 160px" @change="applyFilter">
          <el-option v-for="f in FACTORY_OPTIONS" :key="f" :label="f" :value="f" />
        </el-select>
      </div>
      <el-table :data="filteredRows" style="width: 100%" stripe>
        <el-table-column label="工厂" prop="factory" width="90" align="center">
          <template #default="{ row }"><span class="cm-tag cm-tag-muted">{{ row.factory }}</span></template>
        </el-table-column>
        <el-table-column label="物料编码" prop="code" width="130">
          <template #default="{ row }"><span class="mono">{{ row.code }}</span></template>
        </el-table-column>
        <el-table-column label="物料名称" prop="name" min-width="120" />
        <el-table-column label="类别" prop="category" min-width="100" />
        <el-table-column label="物料单位" prop="unit" width="90" align="center">
          <template #default="{ row }">{{ row.unit || '—' }}</template>
        </el-table-column>
        <el-table-column label="在库物料总量" prop="in_stock_units" width="130" align="center" />
        <el-table-column label="订单扣减" prop="order_deducted_units" width="100" align="center" />
        <el-table-column label="缺口" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.gap_units > 0" class="cm-tag tag-error">{{ row.gap_units }}</span>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column label="转换台数" prop="support_units" width="100" align="center" />
        <el-table-column label="在途量" prop="in_transit_units" width="90" align="center" />
        <el-table-column label="采购量" prop="purchase_units" width="90" align="center" />
        <el-table-column label="采购到货日期" width="120">
          <template #default="{ row }">{{ row.arrival_date || '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="cm-tag" :class="statusTag[row.status] ?? 'cm-tag-muted'">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="stock_note" min-width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <button class="op-btn" @click="openEdit(row)"><Pencil :size="14" /> 编辑</button>
            <button class="op-btn danger" @click="onDelete(row)"><Trash2 :size="14" /> 删除</button>
          </template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!filteredRows.length">暂无物料</p>
    </section>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑物料' : '新增物料'" width="560px">
      <el-form label-width="120px">
        <el-form-item label="所属工厂">
          <el-select v-model="form.factory" style="width: 100%">
            <el-option v-for="f in FACTORY_OPTIONS" :key="f" :label="f" :value="f" />
          </el-select>
        </el-form-item>
        <el-form-item label="物料编码">
          <el-input v-model="form.code" placeholder="如 STEEL-HR" />
        </el-form-item>
        <el-form-item label="物料名称">
          <el-input v-model="form.name" placeholder="如 热轧卷板" />
        </el-form-item>
        <el-form-item label="类别">
          <el-input v-model="form.category" placeholder="如 钢材 / 油漆 / 木地板" />
        </el-form-item>
        <el-form-item label="物料单位">
          <el-input v-model="form.unit" placeholder="如 吨 / 箱 / 张 / 套" />
        </el-form-item>
        <el-form-item label="在库物料总量">
          <el-input-number v-model="form.in_stock_units" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="转换台数">
          <el-input-number v-model="form.support_units" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="在途量">
          <el-input-number v-model="form.in_transit_units" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="采购量">
          <el-input-number v-model="form.purchase_units" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="采购到货日期">
          <el-date-picker v-model="form.arrival_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in STATUS_OPTIONS" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.stock_note" placeholder="可选" />
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
.material-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; gap: 10px; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.stats-card { padding: 14px 16px; margin-bottom: 14px; }
.stats-head { font-size: 14px; font-weight: 600; margin-bottom: 10px; }
.stats-grid { display: flex; gap: 16px; flex-wrap: wrap; }
.stat-item { display: flex; flex-direction: column; gap: 2px; min-width: 110px; padding: 8px 12px; border-radius: 8px; background: var(--cm-muted); }
.stat-label { font-size: 12px; color: var(--cm-muted-foreground); }
.stat-value { font-size: 18px; font-weight: 700; color: var(--cm-primary); }
.stats-factory { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.factory-chip { font-size: 12px; padding: 4px 10px; border-radius: 6px; background: var(--cm-state-success-bg, #e6f7ed); color: var(--cm-slate-700); }
.filter-bar { display: flex; gap: 8px; padding: 8px 12px; }
.mono { font-family: var(--cm-font-mono); font-size: 13px; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.tag-success { background: var(--cm-state-success-bg, #e6f7ed); color: var(--cm-state-success, #16a34a); }
.tag-warning { background: var(--cm-state-warning-bg, #fef3c7); color: var(--cm-state-warning, #d97706); }
.tag-error { background: var(--cm-state-error-bg, #fee2e2); color: var(--cm-state-error, #dc2626); }
.op-btn { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--cm-slate-600); cursor: pointer; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; }
.op-btn:hover { background: var(--cm-muted); color: var(--cm-primary); }
.op-btn.danger:hover { color: var(--cm-state-error); }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
</style>