<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RefreshCw, Search, Bot, Clock, CheckCircle2, XCircle, FileText } from 'lucide-vue-next'
import { getLlmLogs } from '@/api'

const loading = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const query = ref<{ scene?: string; user?: string; session_id?: string; success?: boolean; date_from?: string; date_to?: string }>({})

const sceneMap: Record<string, string> = {
  intent: '意图识别', refine: '回复润色',
  cost_analysis: '成本动因分析', cost_summary: '成本汇总',
}
const scenes = Object.keys(sceneMap)

async function load() {
  loading.value = true
  try {
    const data = await getLlmLogs({ ...query.value, page: page.value, page_size: pageSize.value })
    rows.value = data.items ?? []
    total.value = data.total ?? 0
  } catch (e: any) { /* ignore */ }
  finally { loading.value = false }
}

function reset() {
  query.value = {}
  page.value = 1
  load()
}

function fmtMs(v: number) {
  return v ? `${v} ms` : '-'
}

function sceneLabel(s: string) {
  const map: Record<string, string> = {
    intent: '意图识别', refine: '回复润色',
    cost_analysis: '成本动因分析', cost_summary: '成本汇总',
  }
  return map[s] || s || '-'
}

onMounted(load)
</script>

<template>
  <div class="records-wrap cm-page" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">模型调用记录</h1>
        <p class="page-sub">查看每次大模型调用的输入、输出与 token 使用情况</p>
      </div>
    </section>

    <section class="card">
      <div class="filter-bar">
        <el-select v-model="query.scene" placeholder="调用场景" clearable style="width: 150px">
          <el-option v-for="s in scenes" :key="s" :label="sceneLabel(s)" :value="s" />
        </el-select>
        <el-select v-model="query.success" placeholder="状态" clearable style="width: 120px">
          <el-option label="成功" :value="true" />
          <el-option label="失败" :value="false" />
        </el-select>
        <el-input v-model="query.user" placeholder="调用用户" clearable style="width: 150px" />
        <el-input v-model="query.session_id" placeholder="会话ID" clearable style="width: 180px" />
        <el-date-picker
          v-model="query.date_from" type="date" placeholder="开始日期" value-format="YYYY-MM-DD"
          style="width: 150px" />
        <el-date-picker
          v-model="query.date_to" type="date" placeholder="结束日期" value-format="YYYY-MM-DD"
          style="width: 150px" />
        <button class="btn primary" @click="load"><Search :size="14" /> 查询</button>
        <button class="btn" @click="reset"><RefreshCw :size="14" /> 重置</button>
      </div>

      <el-table :data="rows" size="small" style="width:100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="expand-content">
              <div class="prompt-box">
                <div class="lb"><FileText :size="13" /> 输入（Prompt / 消息）</div>
                <pre>{{ row.prompt }}</pre>
              </div>
              <div class="resp-box">
                <div class="lb"><Bot :size="13" /> 输出（Response）</div>
                <pre>{{ row.response || (row.error ? '（失败）' + row.error : '（空）') }}</pre>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="ID" prop="id" width="60" />
        <el-table-column label="场景" width="130">
          <template #default="{ row }"><el-tag size="small">{{ sceneLabel(row.scene) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="模型" prop="model" min-width="140" show-overflow-tooltip />
        <el-table-column label="用户" prop="user" width="110" show-overflow-tooltip />
        <el-table-column label="会话ID" prop="session_id" width="160" show-overflow-tooltip />
        <el-table-column label="输入 Token" prop="prompt_tokens" width="100" align="right" />
        <el-table-column label="输出 Token" prop="completion_tokens" width="100" align="right" />
        <el-table-column label="总 Token" prop="total_tokens" width="100" align="right" />
        <el-table-column label="耗时" width="90" align="right">
          <template #default="{ row }">{{ fmtMs(row.latency_ms) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <CheckCircle2 v-if="row.success" :size="16" color="var(--cm-success)" />
            <XCircle v-else :size="16" color="var(--cm-danger)" />
          </template>
        </el-table-column>
        <el-table-column label="调用时间" width="170">
          <template #default="{ row }">
            <span class="time-cell"><Clock :size="12" /> {{ row.created_at?.replace('T', ' ') }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          layout="total, prev, pager, next"
          :total="total" :current-page="page" :page-size="pageSize"
          @current-change="(p: number) => { page = p; load() }" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.cm-page { padding: 20px; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 22px; font-weight: 700; }
.page-sub { color: var(--cm-text-3); font-size: 13px; margin-top: 4px; }
.filter-bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 14px; }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 8px;
  border: 1px solid var(--cm-border); background: var(--cm-card); font-size: 13px; cursor: pointer; }
.btn.primary { background: var(--cm-primary); color: #fff; border-color: var(--cm-primary); }
.expand-content { padding: 8px 12px; background: var(--cm-bg); border-radius: 8px; }
.prompt-box, .resp-box { margin-bottom: 10px; }
.prompt-box:last-child, .resp-box:last-child { margin-bottom: 0; }
.lb { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600;
  color: var(--cm-primary); margin-bottom: 4px; }
pre { margin: 0; white-space: pre-wrap; word-break: break-all; font-size: 12px;
  background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 6px; padding: 8px;
  max-height: 220px; overflow: auto; }
.time-cell { display: inline-flex; align-items: center; gap: 4px; color: var(--cm-text-3); font-size: 12px; }
.pager { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>