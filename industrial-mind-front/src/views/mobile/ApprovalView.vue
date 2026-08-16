<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { showSuccessToast, showFailToast, showConfirmDialog } from 'vant'
import { SlidersHorizontal, ClipboardCheck, Check, X, ArrowRightLeft, FileText } from 'lucide-vue-next'
import { getMobileApprovals, mobileApprove, getApprovals } from '@/api'
import { canApprove } from '@/utils/permission'

const permApprove = canApprove()

type Tab = 'pending' | 'done' | 'mine'
const tab = ref<Tab>('pending')
const loading = ref(false)
const items = ref<any[]>([])
const counts = ref<Record<string, number>>({})
const selectedId = ref<number | null>(null)
const me = '张主管'

const tabs: { key: Tab; label: string }[] = [
  { key: 'pending', label: '待审批' },
  { key: 'done', label: '已审批' },
  { key: 'mine', label: '我发起的' },
]

const selected = computed(() => items.value.find((i) => i.id === selectedId.value) ?? null)

const TYPE_COLOR: Record<string, string> = {
  '排产变更': 'primary', '紧急维修': 'error', '样箱插单': 'primary',
  '采购申请': 'warning', '成本分摊': 'info',
}
const PRIORITY_COLOR: Record<string, string> = {
  '紧急': 'error', '高优先级': 'error', '普通': 'info', '低': 'muted',
}
const STATUS_TEXT: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已驳回' }
const STATUS_COLOR: Record<string, string> = { pending: 'warning', approved: 'success', rejected: 'error' }

async function load() {
  loading.value = true
  items.value = []
  selectedId.value = null
  try {
    if (tab.value === 'pending') {
      const res = await getMobileApprovals('pending')
      items.value = res.items ?? []
      counts.value = res.counts ?? {}
    } else if (tab.value === 'done') {
      const [a, r] = await Promise.all([getMobileApprovals('approved'), getMobileApprovals('rejected')])
      items.value = [...(a.items ?? []), ...(r.items ?? [])]
      counts.value = a.counts ?? {}
    } else {
      const res = await getApprovals({ status: 'all' })
      items.value = (res.items ?? []).filter((i: any) => i.applicant === me)
      counts.value = res.counts ?? {}
    }
    selectedId.value = items.value[0]?.id ?? null
  } catch (e: any) {
    showFailToast(e.message)
  } finally { loading.value = false }
}

function typeColor(t: string) { return TYPE_COLOR[t] ?? 'primary' }
function prioColor(p: string) { return PRIORITY_COLOR[p] ?? 'info' }
function statusKey(s: string) { return s in STATUS_TEXT ? s : 'pending' }

async function act(item: any, action: 'approve' | 'reject' | 'transfer') {
  const titles: Record<string, string> = { approve: '通过审批', reject: '驳回审批', transfer: '转交审批' }
  try {
    await showConfirmDialog({
      title: titles[action],
      message: action === 'transfer'
        ? '确认将该审批单转交给同级别主管处理？'
        : action === 'approve'
          ? `确认通过「${item.title}」？`
          : `确认驳回「${item.title}」？`,
    })
    if (action === 'transfer') {
      await mobileApprove(item.id, { action: 'approve', operator: `${me}(转交)`, comment: '移动端转交处理' })
      showSuccessToast('已转交')
    } else {
      const comment = action === 'approve' ? '移动端审批通过' : '移动端驳回'
      await mobileApprove(item.id, { action, operator: me, comment })
      showSuccessToast(action === 'approve' ? '已通过' : '已驳回')
    }
    load()
  } catch (e: any) {
    if (e !== 'cancel' && e?.message !== 'cancel') showFailToast(e?.message ?? '操作失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <!-- 顶部 -->
    <header class="m-header">
      <div class="brand">
        <span class="brand-logo">CM</span>
        <div>
          <div class="brand-name sm">ContainerMind</div>
          <div class="brand-title">审批中心</div>
        </div>
      </div>
      <button class="icon-btn" @click="showFailToast('筛选：已按状态/类型聚合')">
        <SlidersHorizontal :size="16" />
      </button>
    </header>

    <!-- tabs -->
    <nav class="tabs">
      <button v-for="t in tabs" :key="t.key" class="tab" :class="{ active: tab === t.key }"
              @click="tab = t.key; load()">
        {{ t.label }}
        <span v-if="t.key === 'pending' && counts.pending" class="count-badge">{{ counts.pending }}</span>
      </button>
    </nav>

    <main class="content">
      <div v-if="loading" class="loading">加载中…</div>

      <!-- 空状态 -->
      <div v-else-if="!items.length" class="empty">
        <span class="empty-icon"><ClipboardCheck :size="28" /></span>
        <b>暂无审批记录</b>
        <span>当前筛选条件下没有相关审批</span>
      </div>

      <template v-else>
        <!-- 卡片列表 -->
        <div class="cards">
          <div v-for="a in items" :key="a.id" class="card" :class="{ selected: a.id === selectedId }"
               @click="selectedId = a.id">
            <div class="card-head">
              <div class="badges">
                <span class="m-badge" :class="typeColor(a.approval_type)">{{ a.approval_type }}</span>
                <span class="m-badge" :class="prioColor(a.priority)">{{ a.priority }}</span>
              </div>
              <span class="m-badge" :class="STATUS_COLOR[statusKey(a.status)]">{{ STATUS_TEXT[statusKey(a.status)] }}</span>
            </div>
            <h2 class="card-title">{{ a.title }}</h2>
            <div class="card-sub">申请人：{{ a.applicant }} · {{ a.submitted_at }}</div>
            <div v-if="a.status === 'pending' && permApprove" class="card-actions" @click.stop>
              <button class="btn primary" @click="act(a, 'approve')"><Check :size="15" /> 通过</button>
              <button class="btn danger-outline" @click="act(a, 'reject')"><X :size="15" /> 驳回</button>
            </div>
          </div>
        </div>

        <!-- 详情卡 -->
        <section v-if="selected" class="detail">
          <div class="detail-head">
            <span class="v-bar" />
            <b>审批详情</b>
            <span class="detail-no">{{ selected.approval_no }}</span>
          </div>

          <div class="fields">
            <div class="field">
              <label>申请原因</label>
              <p>{{ selected.detail?.reason ?? '—' }}</p>
            </div>
            <div class="field">
              <label>影响产线</label>
              <p>{{ selected.affect_lines ?? '—' }}</p>
            </div>
            <div class="field">
              <label>原方案</label>
              <p>{{ selected.detail?.plan_compare?.original ?? '—' }}</p>
            </div>
            <div class="field">
              <label>新方案</label>
              <p class="new">{{ selected.detail?.plan_compare?.new ?? '—' }}</p>
            </div>
            <div class="field">
              <label>风险提示</label>
              <p class="risk">{{ selected.risk_level ?? '—' }} · 生效时间 {{ selected.expect_effect_time ?? '待定' }}</p>
            </div>
          </div>

          <div v-if="(selected.detail?.impacts ?? []).length" class="impacts">
            <div class="impact-title"><FileText :size="13" /> AI 影响评估</div>
            <div v-for="(im, i) in selected.detail.impacts" :key="i" class="impact">
              <span class="impact-type">{{ im.type }}</span>
              <span>{{ im.content }}</span>
            </div>
          </div>

          <div v-if="selected.status === 'pending' && permApprove" class="detail-actions">
            <button class="btn primary grow" @click="act(selected, 'approve')"><Check :size="15" /> 通过</button>
            <button class="btn danger-outline" @click="act(selected, 'reject')"><X :size="15" /> 驳回</button>
            <button class="btn outline" @click="act(selected, 'transfer')"><ArrowRightLeft :size="14" /> 转交</button>
          </div>
          <p class="safety">⚠️ 以上为 AI 辅助分析，审批决策请以人工判断为准</p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
@import '@/styles/mobile.css';

.page { padding-top: 100px; }

.brand-name.sm { font-size: 10px; font-weight: 500; color: var(--cm-slate-400); line-height: 1.2; }
.brand-title { font-size: 15px; font-weight: 600; color: var(--cm-slate-800); line-height: 1.3; }

/* tabs（吸顶在 header 下方） */
.tabs {
  position: fixed; top: 56px; left: 50%; transform: translateX(-50%);
  width: 100%; max-width: 420px; z-index: 90;
  display: flex; background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--cm-border);
}
.tab {
  flex: 1; padding: 12px 0; background: none; border: none; cursor: pointer;
  font-size: 14px; color: var(--cm-slate-500);
  border-bottom: 2px solid transparent;
  display: flex; align-items: center; justify-content: center; gap: 5px;
}
.tab.active { color: var(--cm-primary); font-weight: 600; border-bottom-color: var(--cm-primary); }
.count-badge {
  min-width: 16px; height: 16px; padding: 0 4px; border-radius: 9999px;
  background: var(--cm-primary); color: #fff; font-size: 10px;
  display: inline-flex; align-items: center; justify-content: center;
}

.content { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.loading { text-align: center; color: var(--cm-slate-400); font-size: 13px; padding: 24px 0; }

/* 空状态 */
.empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 48px 0; }
.empty-icon {
  width: 64px; height: 64px; border-radius: 50%; background: var(--cm-slate-100);
  color: var(--cm-slate-400); display: flex; align-items: center; justify-content: center; margin-bottom: 4px;
}
.empty b { font-size: 14px; color: var(--cm-slate-600); font-weight: 500; }
.empty span:last-child { font-size: 12px; color: var(--cm-slate-400); }

/* 卡片 */
.cards { display: flex; flex-direction: column; gap: 10px; }
.card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 12px; padding: 14px; cursor: pointer; }
.card.selected { border-color: var(--cm-primary); box-shadow: 0 0 0 2px var(--cm-primary-100); }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.badges { display: flex; gap: 6px; flex-wrap: wrap; }
.card-title {
  font-size: 15px; font-weight: 600; color: var(--cm-slate-800);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.card-sub { font-size: 11px; color: var(--cm-slate-400); margin-top: 4px; }
.card-actions { display: flex; gap: 8px; margin-top: 12px; }

.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  height: 34px; padding: 0 14px; border-radius: 8px; font-size: 13px; cursor: pointer;
}
.btn.grow { flex: 1; }
.btn.primary { background: var(--cm-primary); border: none; color: #fff; font-weight: 500; flex: 1; }
.btn.danger-outline { background: var(--cm-card); border: 1px solid var(--cm-state-error); color: var(--cm-state-error); flex: 1; }
.btn.outline { background: var(--cm-card); border: 1px solid var(--cm-border); color: var(--cm-slate-600); }

/* 详情 */
.detail { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 12px; padding: 14px; }
.detail-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.v-bar { width: 3px; height: 16px; border-radius: 2px; background: var(--cm-primary); }
.detail-head b { font-size: 14px; font-weight: 600; color: var(--cm-slate-800); }
.detail-no { margin-left: auto; font-size: 11px; color: var(--cm-slate-400); font-variant-numeric: tabular-nums; }

.fields { display: flex; flex-direction: column; gap: 10px; }
.field label { display: block; font-size: 11px; color: var(--cm-slate-400); margin-bottom: 3px; }
.field p { font-size: 13px; color: var(--cm-slate-700); line-height: 1.55; }
.field p.new { color: var(--cm-primary-700); }
.field p.risk { color: var(--cm-state-error); }

.impacts { margin-top: 12px; padding: 10px; border-radius: 8px; background: var(--cm-slate-50); }
.impact-title { display: flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 600; color: var(--cm-slate-600); margin-bottom: 8px; }
.impact { display: flex; gap: 8px; font-size: 12px; color: var(--cm-slate-500); line-height: 1.5; }
.impact + .impact { margin-top: 6px; }
.impact-type { flex-shrink: 0; color: var(--cm-primary-700); }

.detail-actions { display: flex; gap: 8px; margin-top: 14px; }
.safety { margin-top: 10px; font-size: 11px; color: var(--cm-slate-400); text-align: center; }
</style>
