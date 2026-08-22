<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw, Truck } from 'lucide-vue-next'
import { getSupplierAvailability, getSupplierOptions } from '@/api'

const loading = ref(false)
const suppliers = ref<any[]>([])
const materials = ref<any[]>([])
const months = ref<string[]>([])
const data = ref<any>({ generated_at: '', items: [] })

const supplierFilter = ref('')
const materialFilter = ref('')
const monthFilter = ref('')
const monthCount = ref(3)

const statusTag: Record<string, string> = { 充足: 'tag-success', 紧张: 'tag-warning', 缺货: 'tag-error' }

const filteredItems = ref<any[]>([])

function applyFilter() {
  filteredItems.value = data.value.items.filter((it: any) => {
    if (supplierFilter.value && it.supplier_code !== supplierFilter.value) return false
    if (materialFilter.value && it.material_code !== materialFilter.value) return false
    if (monthFilter.value && it.month !== monthFilter.value) return false
    return true
  })
}

// 按供货商汇总当前筛选范围内的可用量，便于快速判断承接能力
const supplierSummary = ref<any[]>([])

function buildSummary() {
  const map = new Map<string, any>()
  for (const it of filteredItems.value) {
    const cur = map.get(it.supplier_code) || { code: it.supplier_code, name: it.supplier, port: it.port, available_qty: 0, items: 0, tight: 0, shortage: 0 }
    cur.available_qty += it.available_qty
    cur.items += 1
    if (it.status === '紧张') cur.tight += 1
    if (it.status === '缺货') cur.shortage += 1
    map.set(it.supplier_code, cur)
  }
  supplierSummary.value = Array.from(map.values())
}

async function load() {
  loading.value = true
  try {
    const opts = await getSupplierOptions()
    suppliers.value = opts.suppliers || []
    materials.value = opts.materials || []
    months.value = opts.months || []
    await reload()
  } finally { loading.value = false }
}

async function reload() {
  loading.value = true
  try {
    data.value = await getSupplierAvailability({
      supplier: supplierFilter.value || undefined,
      material: materialFilter.value || undefined,
      months: monthCount.value,
    })
    if (!monthFilter.value) monthFilter.value = ''
    applyFilter()
    buildSummary()
  } finally { loading.value = false }
}

function onFilterChange() {
  applyFilter()
  buildSummary()
}

onMounted(load)
</script>

<template>
  <div class="supplier-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">供货商动态</h1>
        <p class="page-sub">5 家供货商未来数月各物料可供货日历（mock），辅助接单评估与排产预测</p>
      </div>
      <div class="head-right">
        <button class="btn primary" @click="reload"><RefreshCw :size="15" /> 刷新</button>
      </div>
    </section>

    <section class="filter-bar card">
      <label>供货商
        <el-select v-model="supplierFilter" placeholder="全部" clearable style="width: 180px" @change="onFilterChange">
          <el-option v-for="s in suppliers" :key="s.code" :label="`${s.name}`" :value="s.code" />
        </el-select>
      </label>
      <label>物料
        <el-select v-model="materialFilter" placeholder="全部" clearable style="width: 160px" @change="onFilterChange">
          <el-option v-for="m in materials" :key="m.code" :label="`${m.name}`" :value="m.code" />
        </el-select>
      </label>
      <label>月份
        <el-select v-model="monthFilter" placeholder="全部月份" clearable style="width: 130px" @change="onFilterChange">
          <el-option v-for="mo in months" :key="mo" :label="mo" :value="mo" />
        </el-select>
      </label>
      <label>月数
        <el-select v-model="monthCount" style="width: 100px" @change="reload">
          <el-option :label="'3 个月'" :value="3" />
          <el-option :label="'6 个月'" :value="6" />
          <el-option :label="'12 个月'" :value="12" />
        </el-select>
      </label>
      <span class="generated" v-if="data.generated_at">生成于 {{ data.generated_at }}</span>
    </section>

    <section class="supplier-cards" v-if="supplierSummary.length">
      <div class="sup-card" v-for="s in supplierSummary" :key="s.code">
        <div class="sup-head"><Truck :size="16" class="sup-icon" /><span class="sup-name">{{ s.name }}</span><span class="sup-code">{{ s.code }}</span></div>
        <div class="sup-meta">港口：{{ s.port }} ｜ {{ s.items }} 项记录</div>
        <div class="sup-stats">
          <div class="sup-stat"><span class="stat-label">可用总量</span><span class="stat-value">{{ s.available_qty }}</span></div>
          <div class="sup-stat warn"><span class="stat-label">紧张</span><span class="stat-value">{{ s.tight }}</span></div>
          <div class="sup-stat err"><span class="stat-label">缺货</span><span class="stat-value">{{ s.shortage }}</span></div>
        </div>
      </div>
    </section>

    <section class="card">
      <el-table :data="filteredItems" style="width: 100%" stripe>
        <el-table-column label="月份" prop="month" width="100" align="center">
          <template #default="{ row }"><span class="mono">{{ row.month }}</span></template>
        </el-table-column>
        <el-table-column label="供货商" prop="supplier" min-width="150" />
        <el-table-column label="港口" prop="port" width="90" align="center" />
        <el-table-column label="物料" prop="material" min-width="120" />
        <el-table-column label="类别" prop="category" min-width="90" />
        <el-table-column label="承诺量" prop="committed_qty" width="90" align="center" />
        <el-table-column label="可用量" prop="available_qty" width="90" align="center">
          <template #default="{ row }"><b class="mono">{{ row.available_qty }}</b></template>
        </el-table-column>
        <el-table-column label="单位" prop="unit" width="70" align="center" />
        <el-table-column label="可到货日期" prop="arrival_date" width="110" align="center">
          <template #default="{ row }">{{ row.arrival_date }}</template>
        </el-table-column>
        <el-table-column label="供货保障" width="90" align="center">
          <template #default="{ row }">
            <span class="cm-tag" :class="statusTag[row.status] ?? 'cm-tag-muted'">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="提前期(天)" prop="lead_days" width="90" align="center" />
      </el-table>
      <p class="empty-tip" v-if="!filteredItems.length">当前筛选条件下暂无供货数据</p>
    </section>
  </div>
</template>

<style scoped>
.supplier-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; gap: 10px; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); }
.filter-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding: 12px 16px; margin-bottom: 14px; }
.filter-bar label { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--cm-muted-foreground); }
.generated { margin-left: auto; font-size: 12px; color: var(--cm-muted-foreground); }
.supplier-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; margin-bottom: 14px; }
.sup-card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 12px 14px; }
.sup-head { display: flex; align-items: center; gap: 8px; }
.sup-icon { color: var(--cm-primary); }
.sup-name { font-weight: 600; font-size: 14px; }
.sup-code { margin-left: auto; font-size: 12px; color: var(--cm-muted-foreground); font-family: var(--cm-font-mono); }
.sup-meta { font-size: 12px; color: var(--cm-muted-foreground); margin: 4px 0 10px; }
.sup-stats { display: flex; gap: 10px; }
.sup-stat { display: flex; flex-direction: column; flex: 1; padding: 6px 8px; border-radius: 8px; background: var(--cm-muted); }
.sup-stat .stat-label { font-size: 11px; color: var(--cm-muted-foreground); }
.sup-stat .stat-value { font-size: 16px; font-weight: 700; color: var(--cm-primary); }
.sup-stat.warn .stat-value { color: var(--cm-state-warning); }
.sup-stat.err .stat-value { color: var(--cm-state-error); }
.el-table { --el-table-border-color: var(--cm-border); }
.mono { font-family: var(--cm-font-mono); font-size: 13px; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.tag-success { background: var(--cm-state-success-bg, #e6f7ed); color: var(--cm-state-success, #16a34a); }
.tag-warning { background: var(--cm-state-warning-bg, #fef3c7); color: var(--cm-state-warning, #d97706); }
.tag-error { background: var(--cm-state-error-bg, #fee2e2); color: var(--cm-state-error, #dc2626); }
.cm-tag-muted { background: var(--cm-muted); color: var(--cm-muted-foreground); }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
</style>