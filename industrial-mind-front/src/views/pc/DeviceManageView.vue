<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDeviceList, getLines } from '@/api'
import { Search, RefreshCw } from 'lucide-vue-next'

const loading = ref(false)
const rows = ref<any[]>([])
const lines = ref<any[]>([])
const query = ref({ line_code: '', status: '', keyword: '' })

const statusTag: Record<string, string> = { 正常: 'cm-tag-success', 预警: 'cm-tag-warning', 警告: 'cm-tag-warning', 故障: 'cm-tag-error' }
const healthColor = (h: number) => (h >= 85 ? 'hl-success' : h >= 70 ? 'hl-warning' : 'hl-error')

async function load() {
  loading.value = true
  try {
    const params: any = {}
    if (query.value.line_code) params.line_code = query.value.line_code
    if (query.value.status) params.status = query.value.status
    if (query.value.keyword.trim()) params.keyword = query.value.keyword.trim()
    rows.value = await getDeviceList(params)
  } finally { loading.value = false }
}

function reset() {
  query.value = { line_code: '', status: '', keyword: '' }
  load()
}

onMounted(async () => {
  lines.value = await getLines()
  load()
})
</script>

<template>
  <div class="device-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">设备管理</h1>
        <p class="page-sub">设备明细列表，支持按产线 / 状态 / 关键字过滤（本次为 mock 示例数据）</p>
      </div>
    </section>

    <section class="card">
      <div class="filter-bar">
        <el-select v-model="query.line_code" placeholder="全部产线" clearable style="width: 160px" @change="load">
          <el-option v-for="l in lines" :key="l.line_code" :label="`${l.line_code} ${l.line_name}`" :value="l.line_code" />
        </el-select>
        <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 130px" @change="load">
          <el-option label="正常" value="正常" />
          <el-option label="预警" value="预警" />
          <el-option label="警告" value="警告" />
          <el-option label="故障" value="故障" />
        </el-select>
        <el-input v-model="query.keyword" placeholder="设备名称 / 编号 / 类型" clearable style="width: 220px" @keyup.enter="load" @clear="load">
          <template #prefix><Search :size="14" /></template>
        </el-input>
        <button class="btn primary" @click="load"><Search :size="14" /> 查询</button>
        <button class="btn" @click="reset"><RefreshCw :size="14" /> 重置</button>
        <span class="result-count">共 {{ rows.length }} 台设备</span>
      </div>

      <el-table :data="rows" style="width: 100%" stripe>
        <el-table-column label="设备编号" width="150">
          <template #default="{ row }"><span class="mono">{{ row.device_id }}</span></template>
        </el-table-column>
        <el-table-column label="设备名称" prop="name" min-width="120" />
        <el-table-column label="设备类型" prop="device_type" min-width="110" />
        <el-table-column label="产线" width="110">
          <template #default="{ row }">{{ row.line_code }} · {{ row.line_name }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="cm-tag" :class="statusTag[row.status] ?? 'cm-tag-muted'">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="健康度" width="160" align="center">
          <template #default="{ row }">
            <div class="health-cell">
              <div class="cm-progress-bg"><div class="cm-progress-fill" :class="healthColor(row.health)" :style="{ width: row.health + '%' }"></div></div>
              <span class="num-strong">{{ row.health }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="剩余寿命 RUL" width="110" align="right">
          <template #default="{ row }">{{ (row.rul_hours ?? 0).toLocaleString() }} h</template>
        </el-table-column>
        <el-table-column label="温度" width="90" align="right">
          <template #default="{ row }">{{ row.temperature }}°C</template>
        </el-table-column>
        <el-table-column label="振动" width="90" align="right">
          <template #default="{ row }">{{ row.vibration }} mm/s</template>
        </el-table-column>
        <el-table-column label="负载率" width="90" align="right">
          <template #default="{ row }">{{ row.current_load }}%</template>
        </el-table-column>
        <el-table-column label="上次保养" width="110">
          <template #default="{ row }">{{ row.last_maintenance }}</template>
        </el-table-column>
        <el-table-column label="下次保养" width="110">
          <template #default="{ row }">{{ row.next_maintenance }}</template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!rows.length">暂无设备数据</p>
    </section>
  </div>
</template>

<style scoped>
.device-wrap { padding: 20px 24px 28px; }
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
.cm-tag-success { background: var(--cm-state-success-bg, #e6f7ed); color: var(--cm-state-success, #16a34a); }
.cm-tag-warning { background: var(--cm-state-warning-bg, #fef3c7); color: var(--cm-state-warning, #d97706); }
.cm-tag-error { background: var(--cm-state-error-bg, #fee2e2); color: var(--cm-state-error, #dc2626); }
.health-cell { display: flex; align-items: center; gap: 8px; }
.cm-progress-bg { flex: 1; height: 6px; border-radius: 999px; background: var(--cm-slate-100); overflow: hidden; }
.cm-progress-fill { height: 100%; border-radius: 999px; }
.hl-success { background: var(--cm-state-success, #16a34a); }
.hl-warning { background: var(--cm-state-warning, #d97706); }
.hl-error { background: var(--cm-state-error, #dc2626); }
.num-strong { font-weight: 600; font-size: 13px; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
</style>