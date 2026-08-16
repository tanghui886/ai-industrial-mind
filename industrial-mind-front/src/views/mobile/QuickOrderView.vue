<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast, showFailToast } from 'vant'
import {
  Bell, CheckCircle2, Send, Mic, CalendarCheck, Gauge, PackageCheck,
  AlertTriangle, HelpCircle, Container, ChevronDown, Factory,
} from 'lucide-vue-next'
import { quickOrder, confirmQuickOrder, getMyOrders } from '@/api'
import { canAddWorkOrder } from '@/utils/permission'

const permAdd = canAddWorkOrder()

const router = useRouter()
const text = ref('')
const analyzing = ref(false)
const result = ref<any>(null)
const errorHint = ref('')
const myOrders = ref<any[]>([])
const user = '张业务'

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const templates = [
  '意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海',
  '意向新订单，20GP箱型，总数量200，计划2026.10.20交付，交付地点青岛',
  '意向新订单，Ener C+ 箱型，总数量50，计划2026.09.10交付，加急',
]

const feasibility = computed(() => result.value?.schedule_analysis?.feasibility ?? '')
const feasColor = computed(() => (
  { feasible: 'ok', tight: 'warn', infeasible: 'bad', unknown: 'bad' } as Record<string, string>
)[feasibility.value] ?? 'ok')
const feasText = computed(() => (
  { feasible: '排产可行', tight: '勉强可行（交期紧张）', infeasible: '排产不可行', unknown: '无法评估' } as Record<string, string>
)[feasibility.value] ?? '排产分析')

const materialList = computed(() => {
  const mc = result.value?.schedule_analysis?.material_check ?? {}
  return Object.entries(mc).map(([key, v]: [string, any]) => ({
    key, name: v.name ?? key, status: v.status, note: v.note,
  }))
})

const dailySchedule = computed(() => result.value?.schedule_analysis?.schedule_suggestion?.daily_schedule ?? [])

const riskAlerts = computed(() => result.value?.schedule_analysis?.risk_alerts ?? [])
const missingFields = computed(() => result.value?.missing_fields ?? result.value?.schedule_analysis?.missing_info ?? [])
const capacityImpact = computed(() => result.value?.schedule_analysis?.capacity_impact)
const orderInfo = computed(() => result.value?.schedule_analysis?.order_info)

async function loadOrders() {
  try { myOrders.value = await getMyOrders(user) } catch { /* ignore */ }
}

function useTemplate(t: string) { text.value = t }

async function analyze() {
  const msg = text.value.trim()
  if (!msg || analyzing.value) return
  analyzing.value = true
  result.value = null
  errorHint.value = ''
  try {
    const res = await quickOrder(msg)
    if (res.intent && res.intent !== 'new_order_intent') {
      errorHint.value = res.message ?? '未能识别为意向订单，请补充箱型、数量与交付日期。'
      result.value = null
    } else if (res.schedule_analysis) {
      result.value = res
    } else {
      errorHint.value = res.message ?? '解析失败，请按「箱型 + 数量 + 交付日期 + 交付地点」描述。'
    }
  } catch (e: any) {
    errorHint.value = e.message
  } finally { analyzing.value = false }
}

async function confirm() {
  if (!result.value) return
  const oi = orderInfo.value
  const raw = result.value.raw_extract ?? {}
  try {
    await confirmQuickOrder({
      box_type: oi.box_type, quantity: oi.quantity,
      delivery_date: oi.delivery_date,
      delivery_location: raw.delivery_location ?? oi.delivery_location,
      customer: raw.customer ?? '', input_text: text.value, teu: oi.teu,
      analysis: result.value.schedule_analysis, user,
    })
    showSuccessToast('意向订单已录入')
    result.value = null
    text.value = ''
    loadOrders()
  } catch (e: any) { showFailToast(e.message) }
}

function adjust() { text.value = text.value; window.scrollTo({ top: 0, behavior: 'smooth' }) }

onMounted(loadOrders)
</script>

<template>
  <div class="page">
    <!-- 顶部 -->
    <header class="m-header">
      <div class="brand">
        <span class="brand-logo">CM</span>
        <span class="brand-name">ContainerMind</span>
      </div>
      <div class="header-actions">
        <button class="icon-btn" @click="showFailToast('暂无新通知')">
          <Bell :size="18" />
        </button>
        <span class="avatar">张</span>
      </div>
    </header>

    <main class="content">
      <!-- 问候 -->
      <section class="greeting">
        <h1>{{ greeting }}，{{ user }}</h1>
        <p>一句话录入意向订单，AI 秒级排产分析</p>
      </section>

      <!-- 无录单权限提示 -->
      <section v-if="!permAdd" class="hint-card">
        <AlertTriangle :size="16" />
        <span>当前账号无添加工令权限（仅业务人员可现场接单），可前往「排产查看」查看排产计划。</span>
      </section>

      <!-- 快捷模板 -->
      <section v-if="permAdd">
        <div class="sec-title">快捷模板</div>
        <div class="chips">
          <button v-for="(t, i) in templates" :key="i" class="chip" @click="useTemplate(t)">{{ t }}</button>
        </div>
      </section>

      <!-- 录入区 -->
      <section v-if="permAdd" class="input-card">
        <textarea v-model="text" rows="4" placeholder="例如：意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海" />
        <div class="input-actions">
          <button class="round-btn" title="语音输入" @click="showFailToast('语音输入仅 App 端支持')"><Mic :size="16" /></button>
          <button class="send-btn" :disabled="analyzing || !text.trim()" @click="analyze">
            <Send :size="16" />
            <span>{{ analyzing ? '分析中…' : '发送' }}</span>
          </button>
        </div>
      </section>

      <!-- 解析失败提示 -->
      <section v-if="errorHint" class="hint-card">
        <AlertTriangle :size="16" />
        <span>{{ errorHint }}</span>
      </section>

      <!-- AI 分析结果卡 -->
      <section v-if="result" class="result-card">
        <div class="rc-head">
          <span class="badge" :class="feasColor">{{ feasText }}</span>
          <span class="badge" :class="feasColor">置信度 {{ (result.confidence * 100).toFixed(0) }}%</span>
          <span class="rc-time">刚刚</span>
        </div>

        <!-- 订单信息 -->
        <div class="grid2">
          <div class="cell"><label>箱型</label><b>{{ orderInfo?.box_type_display ?? orderInfo?.box_type }}</b></div>
          <div class="cell"><label>数量</label><b>{{ orderInfo?.quantity?.toLocaleString() }} 台</b></div>
          <div class="cell"><label>TEU</label><b>{{ orderInfo?.teu?.toLocaleString() }}</b></div>
          <div class="cell"><label>交付日期</label><b>{{ orderInfo?.delivery_date }}</b></div>
          <div class="cell span2"><label>交付地点</label><b>{{ orderInfo?.delivery_location }}</b></div>
        </div>

        <!-- 建议排产期 -->
        <div class="block">
          <div class="block-title"><CalendarCheck :size="15" /> 建议排产期</div>
          <div class="phase">
            <span>{{ result.schedule_analysis?.schedule_suggestion?.recommended_start }}</span>
            <span class="arrow">→</span>
            <span>{{ result.schedule_analysis?.schedule_suggestion?.recommended_end }}</span>
            <span class="phase-tag">共 {{ dailySchedule.length }} 个工作日</span>
          </div>
        </div>

        <!-- 产能影响 -->
        <div v-if="capacityImpact" class="block">
          <div class="block-title"><Gauge :size="15" /> 产能影响</div>
          <div class="util-line">
            <span class="util-num">{{ capacityImpact.current_utilization }}</span>
            <span class="arrow">→</span>
            <span class="util-num primary">{{ capacityImpact.after_this_order }}</span>
            <span class="muted">（{{ capacityImpact.month }} 当月）</span>
          </div>
        </div>

        <!-- 物料齐套 -->
        <div v-if="materialList.length" class="block">
          <div class="block-title"><PackageCheck :size="15" /> 物料齐套检查</div>
          <div class="grid3">
            <div v-for="m in materialList" :key="m.key" class="mat" :class="m.status">
              <span>{{ m.name }}</span>
              <b>{{ { sufficient: '充足', warning: '需补货', insufficient: '缺口' }[m.status as string] ?? m.status }}</b>
            </div>
          </div>
        </div>

        <!-- 风险提醒 -->
        <div v-if="riskAlerts.length" class="block">
          <div class="block-title warn"><AlertTriangle :size="15" /> 风险提醒</div>
          <ul class="risks">
            <li v-for="(r, i) in riskAlerts" :key="i" :class="{ first: i === 0 }">{{ r }}</li>
          </ul>
        </div>

        <!-- 待确认信息 -->
        <div v-if="missingFields.length" class="block">
          <div class="block-title"><HelpCircle :size="15" /> 待确认信息</div>
          <div class="chips">
            <span v-for="(f, i) in missingFields" :key="i" class="chip static">{{ f }}</span>
          </div>
        </div>

        <!-- 操作 -->
        <div class="rc-actions">
          <button class="btn primary big" @click="confirm"><CheckCircle2 :size="16" /> 确认录入</button>
          <button class="btn outline" @click="adjust">调整参数</button>
        </div>
        <button class="btn text" @click="router.push('/m/schedule')"><Factory :size="14" /> 查看排产日历</button>
        <p class="safety">{{ result.safety_note }}</p>
      </section>

      <!-- 我的意向订单 -->
      <section v-if="myOrders.length">
        <div class="sec-title row">
          <span>最近意向订单</span>
          <span class="muted small">{{ myOrders.length }} 条</span>
        </div>
        <div class="order-list">
          <div v-for="o in myOrders.slice(0, 5)" :key="o.intention_id" class="order-item">
            <div class="oi-main">
              <div class="oi-line">
                <Container :size="14" />
                <b>{{ o.box_type }}</b>
                <span>× {{ o.quantity }} 台</span>
                <span class="status-tag" :class="o.status">{{ o.status_cn }}</span>
              </div>
              <div class="oi-sub">交付 {{ o.delivery_date }} · {{ o.delivery_location || '—' }} · {{ o.created_at }}</div>
            </div>
            <ChevronDown :size="14" class="muted" style="transform: rotate(-90deg)" />
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
@import '@/styles/mobile.css';

.page { padding-top: 56px; }
.content { padding: 16px; display: flex; flex-direction: column; gap: 20px; }

/* 问候 */
.greeting h1 { font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--cm-slate-900); }
.greeting p { font-size: 13px; color: var(--cm-slate-500); margin-top: 4px; }

/* 模板 */
.chips { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 2px; scrollbar-width: none; }
.chips::-webkit-scrollbar { display: none; }
.chip {
  flex-shrink: 0; padding: 6px 12px; border-radius: 9999px; font-size: 12px;
  background: var(--cm-card); border: 1px solid var(--cm-border); color: var(--cm-slate-600);
  cursor: pointer;
}
.chip.static { cursor: default; color: var(--cm-slate-500); background: var(--cm-slate-100); border-color: transparent; }

/* 录入卡 */
.input-card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 12px; padding: 12px; }
.input-card textarea {
  width: 100%; border: none; outline: none; resize: none; font-size: 14px;
  font-family: inherit; line-height: 1.6; min-height: 96px; color: var(--cm-slate-800);
  background: transparent;
}
.input-actions { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.round-btn {
  width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--cm-border); background: var(--cm-card); color: var(--cm-slate-500); cursor: pointer;
}
.send-btn {
  display: flex; align-items: center; gap: 6px; padding: 0 16px; height: 36px; border-radius: 9999px;
  border: none; background: var(--cm-primary); color: #fff; font-size: 13px; font-weight: 500; cursor: pointer;
}
.send-btn:disabled { opacity: 0.5; }

/* 失败提示 */
.hint-card {
  display: flex; gap: 8px; align-items: flex-start; padding: 12px; border-radius: 12px;
  background: var(--cm-state-warning-bg); color: #92400e; font-size: 13px; line-height: 1.5;
}

/* 结果卡 */
.result-card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 12px; padding: 16px; box-shadow: var(--cm-shadow-1); }
.rc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.rc-time { margin-left: auto; font-size: 11px; color: var(--cm-slate-400); }
.badge { font-size: 11px; padding: 3px 8px; border-radius: 9999px; font-weight: 500; }
.badge.ok { background: var(--cm-state-success-bg); color: #047857; }
.badge.warn { background: var(--cm-state-warning-bg); color: #b45309; }
.badge.bad { background: var(--cm-state-error-bg); color: #b91c1c; }

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 12px; padding-bottom: 14px; border-bottom: 1px dashed var(--cm-border); }
.cell label { display: block; font-size: 11px; color: var(--cm-slate-400); margin-bottom: 2px; }
.cell b { font-size: 14px; font-weight: 600; color: var(--cm-slate-800); font-variant-numeric: tabular-nums; }
.cell.span2 { grid-column: span 2; }

.block { margin-top: 14px; }
.block-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--cm-slate-700); margin-bottom: 8px; }
.block-title.warn { color: #b45309; }

.phase { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--cm-slate-700); font-variant-numeric: tabular-nums; }
.phase .arrow { color: var(--cm-slate-400); }
.phase-tag { margin-left: auto; font-size: 11px; color: var(--cm-primary); background: var(--cm-primary-50); padding: 2px 8px; border-radius: 9999px; }

.util-line { display: flex; align-items: baseline; gap: 8px; font-size: 15px; font-weight: 600; color: var(--cm-slate-700); font-variant-numeric: tabular-nums; }
.util-line .primary { color: var(--cm-primary); font-size: 18px; }
.util-line .muted { font-size: 11px; font-weight: 400; color: var(--cm-slate-400); }

.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.mat { border-radius: 8px; padding: 8px; text-align: center; display: flex; flex-direction: column; gap: 2px; }
.mat span { font-size: 11px; color: var(--cm-slate-500); }
.mat b { font-size: 12px; }
.mat.sufficient { background: var(--cm-state-success-bg); }
.mat.sufficient b { color: #047857; }
.mat.warning { background: var(--cm-state-warning-bg); }
.mat.warning b { color: #b45309; }
.mat.insufficient { background: var(--cm-state-error-bg); }
.mat.insufficient b { color: #b91c1c; }

.risks { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.risks li { font-size: 12px; line-height: 1.5; color: var(--cm-slate-500); padding: 6px 10px; border-radius: 6px; background: var(--cm-slate-100); }
.risks li.first { background: var(--cm-state-warning-bg); color: #92400e; }

.rc-actions { display: grid; grid-template-columns: 1fr auto; gap: 8px; margin-top: 16px; }
.btn { display: flex; align-items: center; justify-content: center; gap: 6px; border-radius: 8px; font-size: 14px; cursor: pointer; height: 40px; }
.btn.primary { background: var(--cm-primary); color: #fff; border: none; font-weight: 500; }
.btn.primary.big { font-size: 15px; }
.btn.outline { background: var(--cm-card); border: 1px solid var(--cm-border); color: var(--cm-slate-600); }
.btn.text { width: 100%; margin-top: 8px; background: none; border: none; color: var(--cm-primary); font-size: 13px; }
.safety { margin-top: 12px; font-size: 11px; color: var(--cm-slate-400); text-align: center; line-height: 1.5; }

/* 订单列表 */
.sec-title.row { display: flex; justify-content: space-between; align-items: center; }
.order-list { display: flex; flex-direction: column; gap: 8px; }
.order-item {
  display: flex; justify-content: space-between; align-items: center; padding: 10px 12px;
  background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 10px;
}
.oi-line { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--cm-slate-700); }
.oi-sub { font-size: 11px; color: var(--cm-slate-400); margin-top: 3px; }
.status-tag { font-size: 10px; padding: 1px 6px; border-radius: 9999px; margin-left: auto; }
.status-tag.pending { background: var(--cm-state-warning-bg); color: #b45309; }
.status-tag.confirmed { background: var(--cm-state-info-bg); color: var(--cm-primary-700); }
.status-tag.converted { background: var(--cm-state-success-bg); color: #047857; }
.status-tag.cancelled { background: var(--cm-slate-100); color: var(--cm-slate-500); }
.muted { color: var(--cm-slate-400); }
.small { font-size: 11px; font-weight: 400; }
</style>
