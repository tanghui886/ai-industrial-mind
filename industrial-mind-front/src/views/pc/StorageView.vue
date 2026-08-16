<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshCw, Warehouse } from 'lucide-vue-next'
import { getStorageList, updateStorageCapacity } from '@/api'

const loading = ref(false)
const rows = ref<any[]>([])

async function load() {
  loading.value = true
  try {
    rows.value = await getStorageList()
  } finally { loading.value = false }
}

async function onCapacityChange(row: any) {
  row.savingCapacity = true
  try {
    await updateStorageCapacity({ line_code: row.line_code, storage_capacity: row.storage_capacity })
    ElMessage.success(`${row.line_code} 总容纳已更新`)
    await load()
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    row.savingCapacity = false
  }
}

onMounted(load)
</script>

<template>
  <div class="storage-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">堆存管理</h1>
        <p class="page-sub">堆存=已确认工令合计；预堆存=待审批/审批中/草稿工令合计；总容纳可手工设置</p>
      </div>
      <button class="btn" @click="load"><RefreshCw :size="14" /> 刷新</button>
    </section>

    <section class="card">
      <el-table :data="rows" style="width: 100%" :row-class-name="({ row }) => row.status === '风险' ? 'row-risk' : ''">
        <el-table-column label="工厂" width="140">
          <template #default="{ row }"><span class="factory">{{ row.factory_code }}</span> {{ row.factory_name }}</template>
        </el-table-column>
        <el-table-column label="产线" width="150">
          <template #default="{ row }"><span class="mono">{{ row.line_code }}</span> · {{ row.line_name }}</template>
        </el-table-column>
        <el-table-column label="产线类型" prop="line_type" width="100" align="center" />
        <el-table-column label="总容纳数量" width="150" align="right">
          <template #default="{ row }">
            <el-input-number v-model="row.storage_capacity" :min="0" :controls="false" class="cap-input"
              @change="onCapacityChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="堆存数量" prop="storage_units" width="110" align="right">
          <template #default="{ row }"><span class="num">{{ row.storage_units }}</span></template>
        </el-table-column>
        <el-table-column label="预堆存" prop="pre_storage" width="100" align="right">
          <template #default="{ row }"><span class="num">{{ row.pre_storage }}</span></template>
        </el-table-column>
        <el-table-column label="剩余空间" width="120" align="right">
          <template #default="{ row }">
            <span class="num" :class="row.remaining < 0 ? 'text-danger' : 'text-success'">{{ row.remaining }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <span class="cm-tag" :class="row.status === '风险' ? 'cm-tag-error' : 'cm-tag-success'">
              <Warehouse :size="12" /> {{ row.status }}
            </span>
          </template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!rows.length">暂无堆存数据</p>
    </section>
  </div>
</template>

<style scoped>
.storage-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid var(--cm-border); background: var(--cm-card); }
.btn:hover { border-color: var(--cm-primary); color: var(--cm-primary); }
.factory { font-weight: 600; }
.mono { font-family: var(--cm-font-mono); font-size: 13px; }
.num { font-weight: 600; }
.cap-input { width: 110px; }
.cap-input :deep(.el-input__inner) { text-align: right; }
.text-danger { color: var(--cm-state-error); }
.text-success { color: var(--cm-state-success); }
.cm-tag { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; font-size: 12px; font-weight: 500; border-radius: 4px; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
:deep(.row-risk) { background: rgba(239, 68, 68, 0.06); }
</style>