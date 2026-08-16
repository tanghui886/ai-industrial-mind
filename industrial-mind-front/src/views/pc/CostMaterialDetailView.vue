<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Search, RefreshCw } from 'lucide-vue-next'
import { getCostMaterialDetails, getCostOptions } from '@/api'

const loading = ref(false)
const rows = ref<any[]>([])
const lines = ref<any[]>([])
const workOrders = ref<string[]>([])
const materials = ref<any[]>([])
const query = ref({ line_code: '', work_order_no: '', material_code: '' })

const STATUS_TAG: Record<string, string> = {
  draft: 'cm-tag-warning', pending_approval: 'cm-tag-info', confirmed: 'cm-tag-success',
  completed: 'cm-tag-success', cancelled: 'cm-tag-muted',
}
const statusLabel: Record<string, string> = {
  draft: '草稿', pending_approval: '审批中', confirmed: '已确认',
  completed: '已完成', cancelled: '已取消',
}

async function load() {
  loading.value = true
  try {
    const params: any = {}
    if (query.value.line_code) params.line_code = query.value.line_code
    if (query.value.work_order_no) params.work_order_no = query.value.work_order_no
    if (query.value.material_code) params.material_code = query.value.material_code
    rows.value = await getCostMaterialDetails(params)
  } finally { loading.value = false }
}

async function loadOptions() {
  const opts = await getCostOptions()
  lines.value = opts.lines
  workOrders.value = opts.work_orders
  materials.value = opts.materials
}

function reset() {
  query.value = { line_code: '', work_order_no: '', material_code: '' }
  load()
}

onMounted(async () => {
  await loadOptions()
  load()
})
</script>

<template>
  <div class="mat-detail-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">物料明细</h1>
        <p class="page-sub">按产线、工令展示每个工令的物料用量，是「物料维护 - 订单扣减/缺口」的用量口径来源</p>
      </div>
    </section>

    <section class="card">
      <div class="filter-bar">
        <el-select v-model="query.line_code" placeholder="全部产线" clearable style="width: 180px" @change="load">
          <el-option v-for="l in lines" :key="l.line_code" :label="`${l.line_code} ${l.line_name}`" :value="l.line_code" />
        </el-select>
        <el-select v-model="query.work_order_no" placeholder="全部工令号" clearable filterable style="width: 200px" @change="load">
          <el-option v-for="w in workOrders" :key="w" :label="w" :value="w" />
        </el-select>
        <el-select v-model="query.material_code" placeholder="全部物料" clearable filterable style="width: 200px" @change="load">
          <el-option v-for="m in materials" :key="m.code" :label="`${m.name}（${m.code}）`" :value="m.code" />
        </el-select>
        <button class="btn primary" @click="load"><Search :size="14" /> 查询</button>
        <button class="btn" @click="reset"><RefreshCw :size="14" /> 重置</button>
        <span class="result-count">共 {{ rows.length }} 条</span>
      </div>

      <el-table :data="rows" style="width: 100%" stripe>
        <el-table-column label="产线" width="130">
          <template #default="{ row }">{{ row.line_code }} · {{ row.line_name }}</template>
        </el-table-column>
        <el-table-column label="工令号" width="180">
          <template #default="{ row }"><span class="mono">{{ row.work_order_no }}</span></template>
        </el-table-column>
        <el-table-column label="箱型" prop="box_type" width="100" />
        <el-table-column label="数量" prop="quantity" width="80" align="center" />
        <el-table-column label="工令状态" width="100" align="center">
          <template #default="{ row }">
            <span class="cm-tag" :class="STATUS_TAG[row.status] || 'cm-tag-muted'">{{ statusLabel[row.status] || row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="物料名称" prop="material_name" min-width="140" />
        <el-table-column label="物料编码" width="130">
          <template #default="{ row }"><span class="mono">{{ row.material_code }}</span></template>
        </el-table-column>
        <el-table-column label="用量" width="110" align="right">
          <template #default="{ row }"><span class="num-strong">{{ row.usage_units }}</span></template>
        </el-table-column>
        <el-table-column label="单位" prop="unit" width="70" align="center" />
      </el-table>
      <p class="empty-tip" v-if="!rows.length">暂无物料明细数据</p>
    </section>
  </div>
</template>

<style scoped>
.mat-detail-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.filter-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 16px; border-bottom: 1px solid var(--cm-border); }
.result-count { margin-left: auto; font-size: 13px; color: var(--cm-muted-foreground); }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid var(--cm-border); background: var(--cm-card); }
.btn.primary { background: var(--cm-primary); color: #fff; border-color: transparent; }
.btn.primary:hover { background: var(--cm-primary-700); }
.mono { font-family: var(--cm-font-mono); font-size: 13px; }
.cm-tag { display: inline-block; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.num-strong { font-weight: 600; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
</style>