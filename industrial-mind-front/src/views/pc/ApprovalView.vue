<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, User, Clock, ShieldCheck, AlertCircle, CheckCircle2, XCircle, Forward } from 'lucide-vue-next'
import { getApprovals, approveOrReject } from '@/api'
import { canApprove } from '@/utils/permission'

const permApprove = canApprove()

const statusTab = ref<'pending' | 'approved' | 'rejected' | 'all'>('pending')
const typeFilter = ref('全部类型')
const keyword = ref('')
const loading = ref(false)
const data = ref<any>(null)
const selectedId = ref<number | null>(null)

const tabs = computed(() => [
  { key: 'pending', label: '待审批', count: data.value?.counts?.pending ?? 0 },
  { key: 'approved', label: '已通过', count: data.value?.counts?.approved ?? 0 },
  { key: 'rejected', label: '已驳回', count: data.value?.counts?.rejected ?? 0 },
  { key: 'all', label: '全部', count: (data.value?.counts?.pending ?? 0) + (data.value?.counts?.approved ?? 0) + (data.value?.counts?.rejected ?? 0) },
] as const)

const selected = computed(() => (data.value?.items ?? []).find((i: any) => i.id === selectedId.value) ?? null)

const typeCls: Record<string, string> = {
  '排产变更': 'tag-info', '紧急维修': 'tag-error', '采购申请': 'tag-success',
  '成本分摊': 'tag-warning', '样箱插单': 'tag-info',
}
const prioCls: Record<string, string> = { '紧急': 'tag-error', '高优先级': 'tag-warning', '普通': 'tag-muted' }
const statusInfo: Record<string, { label: string; cls: string }> = {
  pending: { label: '待审批', cls: 'tag-info' },
  approved: { label: '已通过', cls: 'tag-success' },
  rejected: { label: '已驳回', cls: 'tag-error' },
}

async function load(keepSelection = true) {
  loading.value = true
  try {
    data.value = await getApprovals({ status: statusTab.value, type_filter: typeFilter.value, keyword: keyword.value })
    const items = data.value.items ?? []
    if (!keepSelection || !items.some((i: any) => i.id === selectedId.value)) {
      selectedId.value = items[0]?.id ?? null
    }
  } finally { loading.value = false }
}

function switchTab(k: any) { statusTab.value = k; load(false) }
function fmtTime(t?: string) {
  if (!t) return ''
  return t.replace('T', ' ').slice(5, 16)
}

async function act(action: 'approve' | 'reject' | 'transfer') {
  if (!selected.value) return
  const titles: Record<string, string> = { approve: '通过审批', reject: '驳回审批', transfer: '转交' }
  try {
    const { value } = await ElMessageBox.prompt(
      action === 'approve' ? '确认通过该审批？可填写审批意见。' : action === 'reject' ? '确认驳回该审批？请填写驳回原因。' : '转交给谁处理？请输入姓名。',
      titles[action], { inputValue: '', inputPlaceholder: action === 'transfer' ? '转交给…' : '意见（可选）' },
    )
    await approveOrReject(selected.value.id, action, { operator: '张主管', comment: value ?? '' })
    ElMessage.success(action === 'approve' ? '已通过' : action === 'reject' ? '已驳回' : '已转交')
    load()
  } catch { /* cancel */ }
}

onMounted(() => load(false))
</script>

<template>
  <div class="approval-wrap" v-loading="loading">
    <!-- 页头 -->
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">审批工作台</h1>
        <p class="page-sub">AI 辅助决策需人工确认后方可执行</p>
      </div>
      <div class="head-right">
        <div class="search-box">
          <Search :size="14" class="search-icon" />
          <input v-model="keyword" placeholder="搜索审批编号、标题、申请人" @keyup.enter="load(false)" />
        </div>
        <select v-model="typeFilter" class="type-select" @change="load(false)">
          <option>全部类型</option><option>排产变更</option><option>紧急维修</option>
          <option>采购申请</option><option>成本分摊</option><option>样箱插单</option>
        </select>
      </div>
    </section>

    <div class="tab-row">
      <button v-for="t in tabs" :key="t.key" class="tab" :class="{ active: statusTab === t.key }" @click="switchTab(t.key)">
        {{ t.label }} <span class="tab-count">{{ t.count }}</span>
      </button>
    </div>

    <section class="approval-layout">
      <!-- 左：列表 -->
      <div class="approval-list">
        <div class="list-head">
          <h2>{{ tabs.find(t => t.key === statusTab)?.label }}列表</h2>
          <span class="text-muted small">共 {{ data?.items?.length ?? 0 }} 条</span>
        </div>
        <div class="list-body">
          <article v-for="a in data?.items ?? []" :key="a.id" class="list-card"
                   :class="{ active: a.id === selectedId }" @click="selectedId = a.id">
            <div class="card-tags">
              <span class="tag" :class="typeCls[a.approval_type] || 'tag-info'">{{ a.approval_type }}</span>
              <span class="tag tag-round" :class="prioCls[a.priority] || 'tag-muted'">{{ a.priority }}</span>
            </div>
            <h3 class="card-title">{{ a.title }}</h3>
            <p class="card-desc">{{ a.detail?.reason || '' }}</p>
            <div class="card-foot">
              <div class="foot-left">
                <span class="foot-item"><User :size="12" /> {{ a.applicant }} · {{ a.applicant_role }}</span>
                <span class="foot-item"><Clock :size="12" /> {{ fmtTime(a.submitted_at) }}</span>
              </div>
              <span class="tag tag-round" :class="statusInfo[a.status]?.cls">{{ statusInfo[a.status]?.label }}</span>
            </div>
          </article>
          <p v-if="!(data?.items ?? []).length" class="empty-tip">暂无审批单</p>
        </div>
      </div>

      <!-- 右：详情 -->
      <div v-if="selected" class="approval-detail">
        <div class="detail-head">
          <div class="head-tags">
            <span class="mono small text-muted">{{ selected.approval_no }}</span>
            <span class="tag" :class="typeCls[selected.approval_type] || 'tag-info'">{{ selected.approval_type }}</span>
            <span class="tag tag-round" :class="prioCls[selected.priority] || 'tag-muted'">{{ selected.priority }}</span>
          </div>
          <h2 class="detail-title">{{ selected.title }}</h2>
          <div class="head-meta">
            <span><User :size="14" /> 申请人：{{ selected.applicant }} · {{ selected.applicant_role }}</span>
            <span><Clock :size="14" /> 提交时间：{{ fmtTime(selected.submitted_at) }}</span>
            <span><ShieldCheck :size="14" /> 状态：<b :class="`s-${selected.status}`">{{ statusInfo[selected.status]?.label }}</b></span>
          </div>
        </div>

        <div class="info-grid">
          <div><p>审批类型</p><b>{{ selected.approval_type }}</b></div>
          <div><p>影响产线</p><b>{{ selected.affect_lines }}</b></div>
          <div><p>期望生效时间</p><b>{{ selected.expect_effect_time }}</b></div>
          <div><p>风险等级</p><b class="text-warning">{{ selected.risk_level }}</b></div>
          <div><p>关联 Agent</p><b>{{ selected.related_agent }}</b></div>
          <div><p>需双签</p><b>{{ selected.need_countersign ? '是' : '否' }}</b></div>
        </div>

        <div class="detail-body">
          <div class="block">
            <h3>变更原因</h3>
            <p class="reason">{{ selected.detail?.reason }}</p>
          </div>
          <div v-if="selected.detail?.plan_compare" class="compare-grid">
            <div class="compare-old">
              <h4>原方案</h4>
              <p>{{ selected.detail.plan_compare.original }}</p>
            </div>
            <div class="compare-new">
              <h4>新方案</h4>
              <p>{{ selected.detail.plan_compare.new }}</p>
            </div>
          </div>
          <div v-if="selected.detail?.impacts?.length" class="impact-grid">
            <div v-for="(im, i) in selected.detail.impacts" :key="i" class="impact-card">
              <h4>{{ im.type }}</h4>
              <p>{{ im.content }}</p>
            </div>
          </div>
          <div v-if="selected.detail?.attachments?.length" class="block">
            <h3>附件材料</h3>
            <div class="attachments">
              <span v-for="f in selected.detail.attachments" :key="f" class="attach">{{ f }}</span>
            </div>
          </div>
          <div v-if="selected.detail?.timeline?.length" class="block">
            <h3>审批轨迹</h3>
            <div class="timeline">
              <div v-for="(t, i) in selected.detail.timeline" :key="i" class="tl-item"
                   :class="{ current: t.node?.includes('当前节点') }">
                <span class="tl-dot"></span>
                <div>
                  <p class="tl-node">{{ t.node }}</p>
                  <p class="tl-time">{{ t.time }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="selected.status === 'pending'" class="action-bar">
          <div class="action-tip"><AlertCircle :size="15" class="text-warning" />
            <template v-if="permApprove">
              <template v-if="selected.need_countersign">该审批需双签，通过后仍需上级复核</template>
              <template v-else>AI 已完成风险分析（{{ selected.risk_level }}），请人工确认</template>
            </template>
            <template v-else>当前账号无审批权限，仅可查看</template>
          </div>
          <div v-if="permApprove" class="action-btns">
            <button class="btn ghost" @click="act('transfer')"><Forward :size="15" /> 转交</button>
            <button class="btn danger" @click="act('reject')"><XCircle :size="15" /> 驳回</button>
            <button class="btn primary" @click="act('approve')"><CheckCircle2 :size="15" /> 通过</button>
          </div>
        </div>
      </div>
      <div v-else class="approval-detail empty-detail"><p>请选择左侧审批单查看详情</p></div>
    </section>
  </div>
</template>

<style scoped>
.approval-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; gap: 10px; flex-wrap: wrap; }
.search-box { position: relative; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--cm-muted-foreground); }
.search-box input { height: 36px; width: 250px; padding: 0 12px 0 32px; border-radius: 6px; border: 1px solid var(--cm-input); background: var(--cm-card); color: var(--cm-foreground); font-size: 13px; outline: none; }
.search-box input:focus { border-color: var(--cm-ring); }
.type-select { height: 36px; border-radius: 6px; border: 1px solid var(--cm-input); background: var(--cm-card); color: var(--cm-muted-foreground); padding: 0 10px; font-size: 13px; outline: none; cursor: pointer; }
.tab-row { display: flex; gap: 8px; flex-wrap: wrap; border-bottom: 1px solid var(--cm-border); padding-bottom: 12px; margin-bottom: 18px; }
.tab { border: 1px solid var(--cm-input); background: var(--cm-card); color: var(--cm-muted-foreground); border-radius: 999px; padding: 6px 16px; font-size: 13px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.tab.active { background: var(--cm-primary); border-color: var(--cm-primary); color: #fff; }
.tab-count { font-size: 11px; background: rgba(255, 255, 255, 0.2); border-radius: 999px; padding: 1px 7px; }
.tab:not(.active) .tab-count { background: var(--cm-muted); color: var(--cm-muted-foreground); }
.approval-layout { display: flex; gap: 20px; align-items: flex-start; }
.approval-list { flex: 0 0 42%; min-width: 340px; max-width: 520px; }
.list-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.list-head h2 { margin: 0; font-size: 13px; font-weight: 600; color: var(--cm-muted-foreground); }
.small { font-size: 12px; }
.text-muted { color: var(--cm-muted-foreground); }
.list-body { display: flex; flex-direction: column; gap: 12px; max-height: calc(100vh - 240px); overflow-y: auto; padding-right: 4px; }
.list-card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); padding: 16px; cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s; }
.list-card:hover { box-shadow: var(--cm-shadow-2); }
.list-card.active { border: 2px solid var(--cm-primary); }
.card-tags { display: flex; gap: 8px; }
.tag { display: inline-flex; align-items: center; padding: 2px 8px; font-size: 11px; font-weight: 500; border-radius: 4px; }
.tag-round { border-radius: 999px; }
.tag-info { background: rgba(6, 182, 212, 0.1); color: var(--cm-state-info); }
.tag-success { background: var(--cm-state-success-bg); color: var(--cm-state-success); }
.tag-warning { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
.tag-error { background: var(--cm-state-error-bg); color: var(--cm-state-error); }
.tag-muted { background: var(--cm-muted); color: var(--cm-muted-foreground); }
.card-title { margin: 10px 0 0; font-size: 15px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.card-desc { margin: 6px 0 0; font-size: 13px; color: var(--cm-muted-foreground); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; font-size: 12px; color: var(--cm-muted-foreground); }
.foot-left { display: flex; gap: 12px; flex-wrap: wrap; }
.foot-item { display: inline-flex; align-items: center; gap: 4px; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 32px 0; }
.approval-detail { flex: 1; min-width: 420px; border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); }
.empty-detail { display: flex; align-items: center; justify-content: center; min-height: 300px; color: var(--cm-muted-foreground); font-size: 13px; }
.detail-head { padding: 18px 20px; border-bottom: 1px solid var(--cm-border); }
.head-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mono { font-family: var(--cm-font-mono); }
.detail-title { margin: 10px 0 0; font-size: 19px; font-weight: 600; letter-spacing: -0.02em; }
.head-meta { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 10px; font-size: 13px; color: var(--cm-muted-foreground); }
.head-meta span { display: inline-flex; align-items: center; gap: 5px; }
.s-pending { color: var(--cm-state-info); }
.s-approved { color: var(--cm-state-success); }
.s-rejected { color: var(--cm-state-error); }
.info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px 20px; padding: 16px 20px; border-bottom: 1px solid var(--cm-border); }
.info-grid p { margin: 0; font-size: 11px; color: var(--cm-muted-foreground); }
.info-grid b { font-size: 13px; font-weight: 500; }
.detail-body { padding: 18px 20px; max-height: calc(100vh - 460px); overflow-y: auto; display: flex; flex-direction: column; gap: 18px; }
.block h3 { margin: 0 0 8px; font-size: 13px; font-weight: 600; }
.reason { margin: 0; font-size: 13px; color: var(--cm-slate-600); line-height: 1.7; }
.compare-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.compare-old { border: 1px solid var(--cm-border); background: rgba(148, 163, 184, 0.06); border-radius: 8px; padding: 14px; }
.compare-new { border: 1px solid rgba(8, 145, 178, 0.25); background: rgba(8, 145, 178, 0.05); border-radius: 8px; padding: 14px; }
.compare-old h4, .compare-new h4 { margin: 0 0 8px; font-size: 12px; font-weight: 600; color: var(--cm-muted-foreground); }
.compare-new h4 { color: var(--cm-primary); }
.compare-old p, .compare-new p { margin: 0; font-size: 13px; color: var(--cm-slate-600); line-height: 1.6; }
.impact-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.impact-card { border: 1px solid var(--cm-border); border-radius: 8px; padding: 14px; }
.impact-card h4 { margin: 0 0 6px; font-size: 12px; font-weight: 600; color: var(--cm-muted-foreground); }
.impact-card p { margin: 0; font-size: 12.5px; line-height: 1.6; color: var(--cm-slate-600); }
.attachments { display: flex; flex-wrap: wrap; gap: 10px; }
.attach { border: 1px solid var(--cm-border); background: rgba(148, 163, 184, 0.06); border-radius: 8px; padding: 7px 12px; font-size: 12.5px; }
.timeline { position: relative; padding-left: 18px; }
.timeline::before { content: ''; position: absolute; left: 5px; top: 8px; bottom: 8px; width: 1px; background: var(--cm-border); }
.tl-item { position: relative; padding-left: 16px; margin-bottom: 14px; }
.tl-item:last-child { margin-bottom: 0; }
.tl-dot { position: absolute; left: -17px; top: 5px; width: 11px; height: 11px; border-radius: 999px; background: var(--cm-card); border: 2px solid var(--cm-primary); }
.tl-item.current .tl-dot { background: var(--cm-primary); }
.tl-node { margin: 0; font-size: 13px; font-weight: 500; }
.tl-time { margin: 2px 0 0; font-size: 11.5px; color: var(--cm-muted-foreground); }
.action-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; border-top: 1px solid var(--cm-border); background: rgba(148, 163, 184, 0.06); padding: 14px 20px; border-radius: 0 0 12px 12px; }
.action-tip { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--cm-muted-foreground); }
.text-warning { color: var(--cm-state-warning); }
.action-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.ghost { background: var(--cm-card); border-color: var(--cm-border); color: var(--cm-muted-foreground); }
.btn.ghost:hover { background: var(--cm-muted); }
.btn.danger { background: var(--cm-card); border-color: rgba(239, 68, 68, 0.35); color: var(--cm-state-error); }
.btn.danger:hover { background: rgba(239, 68, 68, 0.06); }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
@media (max-width: 1024px) {
  .approval-layout { flex-direction: column; }
  .approval-list { flex: none; max-width: none; width: 100%; }
  .list-body { max-height: 320px; }
}
</style>
