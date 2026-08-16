<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Sparkles, AlertTriangle, PieChart, Plus, Search, Bot, Mic, SendHorizonal,
  Wrench, ShieldCheck, Globe, Coins, Zap, FileText, Lightbulb, Check, SlidersHorizontal,
  Boxes, Warehouse, CalendarDays, Share2, CheckCircle2, Cpu, Trash2,
} from 'lucide-vue-next'
import { chatStream, confirmQuickOrder, getChatSessions, createChatSession, deleteChatSession, getChatMessages } from '@/api'

const router = useRouter()
const input = ref('')
const sending = ref(false)
const streamRef = ref<HTMLElement>()
let es: EventSource | null = null

interface Msg {
  role: 'user' | 'agent'
  text?: string
  thinking?: string[]
  card?: any
  intent_label?: string
  agent?: string
  done?: boolean
}
const messages = ref<Msg[]>([])

const sessions = ref<any[]>([])
const activeSessionId = ref<string | null>(null)

const scenes = [
  { icon: Sparkles, label: '智能排产', prompt: '意向新订单，40HC箱型，总数量1000，计划2026.09.30交付，交付地点上海' },
  { icon: Wrench, label: '设备诊断', prompt: 'WLD-R03 焊接机器人当前健康状况如何' },
  { icon: Boxes, label: '物料缺口', prompt: '当前各产线物料缺口情况如何' },
  { icon: Warehouse, label: '堆存风险', prompt: '哪些产线的堆存存在爆仓风险' },
  { icon: Coins, label: '成本动因', prompt: '本月成本动因分析' },
]
const prompts = ['按交期倒排', '规避检修日', '替代物料方案', '分批交付方案']
const suggestions = ['9月份QD-D线还有多少空位', 'DFQD-2026-281-DS排到几号了', '当前有哪些待审批']

function scrollToBottom() {
  nextTick(() => { streamRef.value?.scrollTo({ top: streamRef.value.scrollHeight, behavior: 'smooth' }) })
}

function pick(p: string) { input.value = p; send() }

async function loadSessions() {
  try {
    sessions.value = await getChatSessions()
  } catch { sessions.value = [] }
}

async function newSession() {
  try {
    const s = await createChatSession({ title: '新会话' })
    activeSessionId.value = s.session_id
    messages.value = []
    await loadSessions()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function openSession(sessionId: string) {
  if (sessionId === activeSessionId.value) return
  activeSessionId.value = sessionId
  messages.value = []
  try {
    const msgs = await getChatMessages(sessionId)
    messages.value = msgs.map((m) => ({
      role: m.role,
      text: m.content || undefined,
      card: m.card && Object.keys(m.card).length ? m.card : undefined,
      intent_label: m.intent_label || undefined,
      agent: m.agent || undefined,
      done: true,
      thinking: [],
    }))
    scrollToBottom()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function removeSession(sessionId: string) {
  try {
    await ElMessageBox.confirm('确定删除该会话及其历史记录？', '删除会话', { type: 'warning' })
  } catch { return }
  try {
    await deleteChatSession(sessionId)
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = null
      messages.value = []
    }
    await loadSessions()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function send() {
  const text = input.value.trim()
  if (!text || sending.value) return
  // 无活动会话时自动新建一个会话，保证消息能持久化
  if (!activeSessionId.value) {
    try {
      const s = await createChatSession({ title: text.slice(0, 20) })
      activeSessionId.value = s.session_id
      loadSessions()
    } catch { /* 忽略，仍继续发送 */ }
  }
  input.value = ''
  messages.value.push({ role: 'user', text })
  const agentMsg: Msg = { role: 'agent', thinking: [], done: false }
  messages.value.push(agentMsg)
  sending.value = true
  scrollToBottom()

  es = chatStream({ message: text, source: 'pc', session_id: activeSessionId.value || undefined }, (ev) => {
    if (ev.event === 'intent') {
      agentMsg.intent_label = ev.data.intent_label
      agentMsg.agent = ev.data.agent
    } else if (ev.event === 'thinking') {
      agentMsg.thinking!.push(ev.data.text)
      scrollToBottom()
    } else if (ev.event === 'result') {
      agentMsg.text = ev.data.reply_text
      agentMsg.card = ev.data.card
    } else if (ev.event === 'done' || ev.event === 'error') {
      agentMsg.done = true
      sending.value = false
      es?.close()
      scrollToBottom()
      loadSessions()
    }
  })
  es.onerror = () => {
    agentMsg.done = true
    sending.value = false
    if (!agentMsg.text) agentMsg.text = '连接中断，请稍后重试。'
  }
}

const feasibilityTag = (f: any) =>
  f === 'feasible' ? { label: '可行', cls: 'cm-tag-success' }
  : f === 'risky' ? { label: '有风险', cls: 'cm-tag-warning' }
  : { label: '不可行', cls: 'cm-tag-error' }
const woStatus: Record<string, string> = { draft: '草稿', pending_approval: '待审批', confirmed: '已确认', completed: '已完成' }

async function onConfirmEntry(card: any) {
  const oi = card?.data?.order_info
  if (!oi) return
  try {
    await confirmQuickOrder({
      box_type: oi.box_type, quantity: oi.quantity,
      delivery_date: card.data.schedule_suggestion?.recommended_end
        || card.data.delivery_assessment?.estimated_delivery || '',
      delivery_location: oi.delivery_location || '上海', customer: oi.customer || '未提供客户',
      teu: oi.teu, input_text: `PC端确认录入：${oi.box_type} × ${oi.quantity}`,
    })
    ElMessage.success('已录入意向订单，等待计划员确认排产')
  } catch (e: any) { ElMessage.error(e.message) }
}

onMounted(loadSessions)
onBeforeUnmount(() => es?.close())
</script>

<template>
  <div class="chat-layout">
    <!-- 左：会话历史 -->
    <aside class="sidebar-left">
      <div class="sidebar-block">
        <div class="search-box">
          <Search :size="14" class="search-icon" />
          <input type="text" placeholder="搜索会话历史…" />
        </div>
      </div>
      <div class="session-list">
        <button v-for="s in sessions" :key="s.session_id" class="session-item"
                :class="{ active: activeSessionId === s.session_id }"
                @click="openSession(s.session_id)">
          <Sparkles :size="15" class="shrink0 text-primary" />
          <div class="minw0 flex1">
            <p class="session-title">{{ s.title }}</p>
            <p class="session-desc">{{ s.updated_at?.replace('T', ' ').slice(0, 16) }}</p>
          </div>
          <button class="del-btn" title="删除会话" @click.stop="removeSession(s.session_id)">
            <Trash2 :size="13" />
          </button>
        </button>
        <button class="session-item new-btn" @click="newSession">
          <Plus :size="15" /><span class="session-title">新建会话</span>
        </button>
      </div>
    </aside>

    <!-- 中：聊天流 -->
    <main class="chat-main">
      <div ref="streamRef" class="message-stream">
        <!-- 欢迎屏 -->
        <div v-if="!messages.length" class="welcome">
          <div class="welcome-icon"><Bot :size="26" /></div>
          <h3>ContainerMind 工业协同 Agent</h3>
          <p>支持自然语言排产评估、产能查询、工令追踪与审批检索</p>
          <div class="welcome-chips">
            <button v-for="s in suggestions" :key="s" @click="pick(s)">{{ s }}</button>
          </div>
        </div>

        <template v-for="(m, i) in messages" :key="i">
          <!-- 用户消息 -->
          <div v-if="m.role === 'user'" class="msg-user-row">
            <div class="msg-user">{{ m.text }}</div>
          </div>
          <!-- Agent 消息 -->
          <div v-else class="msg-agent-row">
            <div class="agent-avatar"><Bot :size="16" /></div>
            <div class="agent-body">
              <!-- 思考中 -->
              <div v-if="m.thinking?.length && !m.done" class="agent-bubble">
                <div class="thinking-row">
                  <span>{{ m.thinking[m.thinking.length - 1] }}</span>
                  <span class="dots"><i></i><i></i><i></i></span>
                </div>
                <div class="thinking-steps">
                  <div v-for="(t, j) in m.thinking" :key="j" class="step done">✓ {{ t }}</div>
                </div>
              </div>
              <!-- 结果文本 -->
              <div v-if="m.text" class="agent-bubble">
                <div class="agent-meta" v-if="m.intent_label">
                  <span class="cm-tag cm-tag-info">{{ m.intent_label }}</span>
                  <span class="agent-name">{{ m.agent }}</span>
                </div>
                <pre class="reply-text">{{ m.text }}</pre>
              </div>
              <!-- 结构化卡片：可行性评估 -->
              <div v-if="m.card?.type === 'feasibility'" class="agent-card">
                <div class="card-head">
                  <div class="card-head-left">
                    <span class="card-title">{{ m.card.title }}</span>
                    <span class="cm-tag" :class="feasibilityTag(m.card.data.feasibility).cls">
                      <CheckCircle2 :size="12" />{{ feasibilityTag(m.card.data.feasibility).label }}
                    </span>
                  </div>
                  <span class="model-tag">deepseek-v4-flash-0731</span>
                </div>
                <div class="card-grid">
                  <div class="info-row"><div class="info-icon pi"><CalendarDays :size="14" /></div>
                    <div><p>建议排产期</p><b>{{ m.card.data.schedule_suggestion?.recommended_start || '-' }} 至 {{ m.card.data.schedule_suggestion?.recommended_end || '-' }}</b></div></div>
                  <div class="info-row"><div class="info-icon pi"><Zap :size="14" /></div>
                    <div><p>产能占用</p><b>{{ m.card.data.schedule_suggestion?.note || '见逐日排产建议' }}</b></div></div>
                  <div class="info-row"><div class="info-icon pi"><Globe :size="14" /></div>
                    <div><p>TEU 换算</p><b>{{ m.card.data.order_info?.box_type }} {{ m.card.data.order_info?.quantity }}台 ≈ {{ m.card.data.order_info?.teu?.toLocaleString() }} TEU</b></div></div>
                  <div class="info-row"><div class="info-icon ii"><SendHorizonal :size="14" /></div>
                    <div><p>交付评估</p><b>{{ m.card.data.delivery_assessment?.estimated_delivery || '-' }} 交付，缓冲 {{ m.card.data.delivery_assessment?.buffer_days }} 天（风险 {{ m.card.data.delivery_assessment?.risk_level }}）</b></div></div>
                  <div class="info-row"><div class="info-icon is"><ShieldCheck :size="14" /></div>
                    <div><p>物料检查</p><b>{{ m.card.data.material_check || '库存满足排产建议' }}</b></div></div>
                  <div class="info-row"><div class="info-icon iw"><AlertTriangle :size="14" /></div>
                    <div><p>风险提示</p><b>{{ (m.card.data.risk_alerts || []).join('；') || '暂无重大风险' }}</b></div></div>
                </div>
                <div class="card-actions">
                  <button class="chip" @click="onConfirmEntry(m.card)"><Check :size="13" />确认录入</button>
                  <button class="chip" @click="router.push('/pc/planning')"><SlidersHorizontal :size="13" />调整参数</button>
                  <button class="chip" @click="router.push('/pc/planning')"><CalendarDays :size="13" />查看排产</button>
                  <button class="chip"><Share2 :size="13" />分享</button>
                </div>
              </div>
              <!-- 结构化卡片：产能概况 -->
              <div v-else-if="m.card?.type === 'capacity'" class="agent-card">
                <div class="card-head"><span class="card-title">{{ m.card.title }}</span></div>
                <div class="cap-grid">
                  <div><p>计划 TEU</p><b>{{ m.card.data.plan_teu?.toLocaleString() }}</b></div>
                  <div><p>已排 TEU</p><b>{{ m.card.data.scheduled_teu?.toLocaleString() }}</b></div>
                  <div><p>剩余空位</p><b class="text-success">{{ m.card.data.remaining_teu?.toLocaleString() }}</b></div>
                  <div><p>利用率</p><b class="text-primary">{{ m.card.data.utilization_rate }}%</b></div>
                  <div><p>工作日</p><b>{{ m.card.data.workdays }} 天</b></div>
                  <div><p>冲突日</p><b :class="m.card.data.conflict_days ? 'text-error' : ''">{{ m.card.data.conflict_days }} 天</b></div>
                </div>
              </div>
              <!-- 结构化卡片：工令列表 -->
              <div v-else-if="m.card?.type === 'work_orders'" class="agent-card">
                <div class="card-head"><span class="card-title">{{ m.card.title }}</span></div>
                <table class="mini-table">
                  <thead><tr><th>工令号</th><th>客户</th><th>箱型</th><th>数量</th><th>排产区间</th><th>状态</th></tr></thead>
                  <tbody>
                    <tr v-for="o in m.card.data" :key="o.work_order_no">
                      <td class="mono">{{ o.work_order_no }}</td><td>{{ o.customer }}</td>
                      <td>{{ o.box_type }}</td><td>{{ o.quantity }}</td>
                      <td>{{ o.start_date }} ~ {{ o.end_date }}</td>
                      <td><span class="cm-tag cm-tag-info">{{ woStatus[o.status] || o.status }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <!-- 结构化卡片：审批列表 -->
              <div v-else-if="m.card?.type === 'approvals'" class="agent-card">
                <div class="card-head">
                  <span class="card-title">{{ m.card.title }}</span>
                  <button class="chip" @click="router.push('/pc/approval')">前往审批工作台</button>
                </div>
                <div v-for="a in m.card.data" :key="a.approval_no" class="approval-line">
                  <span class="mono">{{ a.approval_no }}</span>
                  <span class="cm-tag cm-tag-muted">{{ a.type }}</span>
                  <span class="flex1 ellipsis">{{ a.title }}</span>
                  <span class="text-muted">{{ a.applicant }}</span>
                </div>
              </div>
              <!-- 安全提示 -->
              <p v-if="m.done && m.text" class="safety-note">⚠️ 以上内容由 AI Agent 辅助生成，仅供辅助参考。涉及排产变更、设备操作、产线停机等决策，必须由具备资质的专业人员确认后执行。</p>
            </div>
          </div>
        </template>
      </div>

      <!-- 输入栏 -->
      <div class="input-bar">
        <div class="input-row">
          <div class="input-box">
            <textarea v-model="input" rows="1" placeholder="输入需求，Agent 将自动理解并执行…"
                      @keydown.enter.exact.prevent="send" />
            <button class="mic-btn" title="语音输入"><Mic :size="15" /></button>
          </div>
          <button class="send-btn" :disabled="sending || !input.trim()" @click="send">
            <span>发送</span><SendHorizonal :size="15" />
          </button>
        </div>
        <div class="input-foot">
          <div class="model-line"><Cpu :size="13" /><span>切换模型</span><span class="model-tag">deepseek-v4-flash-0731</span></div>
          <span class="hint">按 Enter 发送，Shift + Enter 换行</span>
        </div>
      </div>
    </main>

    <!-- 右：快捷场景 -->
    <aside class="sidebar-right">
      <div class="sidebar-block">
        <h3 class="side-title"><Zap :size="15" class="text-primary" />快捷场景</h3>
      </div>
      <div class="scene-list">
        <button v-for="(s, i) in scenes" :key="s.label" class="scene-item" :class="{ primary: i === 0 }" @click="pick(s.prompt)">
          <component :is="s.icon" :size="15" />
          <span>{{ s.label }}</span>
        </button>
      </div>
      <div class="side-section">
        <h3 class="side-title"><FileText :size="15" class="text-muted" />推荐提示词</h3>
        <div class="prompt-chips">
          <button v-for="p in prompts" :key="p" @click="input = p">{{ p }}</button>
        </div>
      </div>
      <div class="side-section">
        <h3 class="side-title"><Lightbulb :size="15" class="text-muted" />试试这样问</h3>
        <div class="prompt-chips">
          <button v-for="s in suggestions" :key="s" @click="pick(s)">{{ s }}</button>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.chat-layout { display: flex; height: calc(100vh - var(--cm-topbar-h)); overflow: hidden; }
.sidebar-left { width: 240px; min-width: 240px; background: var(--cm-card); border-right: 1px solid var(--cm-border); display: flex; flex-direction: column; overflow-y: auto; }
.sidebar-right { width: 280px; min-width: 280px; background: var(--cm-card); border-left: 1px solid var(--cm-border); display: flex; flex-direction: column; overflow-y: auto; }
.sidebar-block { padding: 16px; border-bottom: 1px solid var(--cm-border); }
.search-box { position: relative; }
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--cm-muted-foreground); }
.search-box input { width: 100%; height: 34px; padding: 0 12px 0 32px; border-radius: 6px; border: 1px solid var(--cm-input); background: var(--cm-background); color: var(--cm-foreground); font-size: 13px; outline: none; }
.search-box input:focus { border-color: var(--cm-ring); }
.session-list { flex: 1; padding: 8px; display: flex; flex-direction: column; gap: 4px; }
.session-item { display: flex; align-items: flex-start; gap: 10px; width: 100%; padding: 10px 12px; border: 1px solid transparent; border-radius: 6px; background: transparent; text-align: left; cursor: pointer; }
.session-item:hover { background: var(--cm-muted); }
.session-item.active { background: rgba(8, 145, 178, 0.08); border-color: rgba(8, 145, 178, 0.2); }
.session-item.new-btn { margin-top: 12px; align-items: center; color: var(--cm-muted-foreground); }
.session-title { margin: 0; font-size: 13px; font-weight: 500; color: var(--cm-foreground); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-desc { margin: 2px 0 0; font-size: 12px; color: var(--cm-muted-foreground); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.shrink0 { flex-shrink: 0; }
.minw0 { min-width: 0; }
.flex1 { flex: 1; min-width: 0; }
.del-btn { flex-shrink: 0; border: none; background: transparent; color: var(--cm-muted-foreground); cursor: pointer; padding: 4px; border-radius: 4px; opacity: 0; transition: opacity .15s; }
.session-item:hover .del-btn { opacity: 1; }
.del-btn:hover { background: var(--cm-muted); color: var(--cm-danger); }
.chat-main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.message-stream { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 18px; }
.welcome { margin: auto; text-align: center; max-width: 560px; padding: 40px 0; }
.welcome-icon { width: 56px; height: 56px; margin: 0 auto 16px; border-radius: 16px; background: rgba(8, 145, 178, 0.1); border: 1px solid rgba(8, 145, 178, 0.2); color: var(--cm-primary); display: flex; align-items: center; justify-content: center; }
.welcome h3 { margin: 0 0 8px; font-size: 18px; }
.welcome p { margin: 0; color: var(--cm-muted-foreground); font-size: 13px; }
.welcome-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 20px; }
.welcome-chips button { padding: 7px 14px; border-radius: 999px; border: 1px solid var(--cm-border); background: var(--cm-card); color: var(--cm-slate-600); font-size: 12px; cursor: pointer; }
.welcome-chips button:hover { border-color: var(--cm-primary); color: var(--cm-primary); }
.msg-user-row { display: flex; justify-content: flex-end; }
.msg-user { max-width: 78%; background: var(--cm-primary); color: #fff; padding: 10px 16px; border-radius: 16px 16px 4px 16px; font-size: 14px; line-height: 1.6; }
.msg-agent-row { display: flex; align-items: flex-start; gap: 10px; max-width: 94%; }
.agent-avatar { width: 32px; height: 32px; border-radius: 999px; background: rgba(8, 145, 178, 0.1); border: 1px solid rgba(8, 145, 178, 0.2); color: var(--cm-primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.agent-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
.agent-bubble { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 4px 16px 16px 16px; padding: 12px 16px; box-shadow: var(--cm-shadow-1); }
.thinking-row { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--cm-muted-foreground); }
.dots { display: inline-flex; gap: 4px; }
.dots i { width: 6px; height: 6px; border-radius: 999px; background: var(--cm-primary); animation: pulse-dot 1.4s infinite ease-in-out both; }
.dots i:nth-child(1) { animation-delay: -0.32s; }
.dots i:nth-child(2) { animation-delay: -0.16s; }
.thinking-steps { margin-top: 8px; display: flex; flex-direction: column; gap: 3px; }
.thinking-steps .step { font-size: 11px; color: var(--cm-state-success); }
@keyframes pulse-dot { 0%, 80%, 100% { opacity: 0.35; transform: scale(0.85); } 40% { opacity: 1; transform: scale(1); } }
.agent-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.agent-name { font-size: 11px; color: var(--cm-muted-foreground); }
.reply-text { margin: 0; font-family: inherit; font-size: 13.5px; line-height: 1.7; white-space: pre-wrap; word-break: break-word; }
.agent-card { background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 4px 16px 16px 16px; box-shadow: var(--cm-shadow-1); overflow: hidden; }
.card-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border-bottom: 1px solid var(--cm-border); }
.card-head-left { display: flex; align-items: center; gap: 10px; }
.card-title { font-size: 14px; font-weight: 600; }
.model-tag { font-size: 11px; color: var(--cm-muted-foreground); background: var(--cm-muted); border-radius: 4px; padding: 2px 8px; }
.card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 20px; padding: 16px; }
.info-row { display: flex; align-items: flex-start; gap: 10px; }
.info-row p { margin: 0; font-size: 11px; color: var(--cm-muted-foreground); }
.info-row b { font-size: 13px; font-weight: 500; line-height: 1.5; }
.info-icon { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.pi { background: var(--cm-primary-50); color: var(--cm-primary-600); }
.ii { background: var(--cm-state-info-bg); color: var(--cm-state-info); }
.is { background: var(--cm-state-success-bg); color: var(--cm-state-success); }
.iw { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
.card-actions { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--cm-border); background: rgba(148, 163, 184, 0.06); }
.chip { display: inline-flex; align-items: center; gap: 5px; padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 500; border: 1px solid var(--cm-border); background: var(--cm-card); color: var(--cm-foreground); cursor: pointer; }
.chip:hover { border-color: var(--cm-primary); color: var(--cm-primary); }
.cap-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 16px; }
.cap-grid > div { background: var(--cm-slate-50); border-radius: 8px; padding: 10px 12px; }
.cap-grid p { margin: 0; font-size: 11px; color: var(--cm-muted-foreground); }
.cap-grid b { font-size: 18px; font-weight: 600; font-variant-numeric: tabular-nums; }
.mini-table { width: 100%; border-collapse: collapse; }
.mini-table th, .mini-table td { padding: 8px 14px; text-align: left; font-size: 12px; border-bottom: 1px solid var(--cm-border); }
.mini-table th { background: var(--cm-slate-50); font-weight: 600; }
.mono { font-family: var(--cm-font-mono); font-size: 11px; }
.approval-line { display: flex; align-items: center; gap: 10px; padding: 10px 16px; border-bottom: 1px solid var(--cm-border); font-size: 12px; }
.approval-line:last-child { border-bottom: none; }
.flex1 { flex: 1; min-width: 0; }
.ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.text-muted { color: var(--cm-muted-foreground); }
.safety-note { margin: 0; font-size: 11px; color: var(--cm-slate-400); line-height: 1.6; }
.input-bar { border-top: 1px solid var(--cm-border); background: var(--cm-card); padding: 14px 20px; }
.input-row { display: flex; align-items: flex-end; gap: 12px; max-width: 960px; margin: 0 auto; }
.input-box { flex: 1; position: relative; min-width: 0; }
.input-box textarea { width: 100%; min-height: 44px; max-height: 128px; padding: 11px 44px 11px 16px; border-radius: 12px; border: 1px solid var(--cm-input); background: var(--cm-background); color: var(--cm-foreground); font-size: 13.5px; font-family: inherit; resize: none; outline: none; }
.input-box textarea:focus { border-color: var(--cm-ring); }
.mic-btn { position: absolute; right: 10px; bottom: 10px; border: none; background: transparent; color: var(--cm-muted-foreground); cursor: pointer; padding: 4px; border-radius: 4px; }
.mic-btn:hover { background: var(--cm-muted); color: var(--cm-foreground); }
.send-btn { height: 44px; padding: 0 18px; border: none; border-radius: 12px; background: var(--cm-primary); color: #fff; font-size: 13px; font-weight: 500; display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
.send-btn:hover { filter: brightness(1.06); }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.input-foot { display: flex; align-items: center; justify-content: space-between; max-width: 960px; margin: 8px auto 0; }
.model-line { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--cm-muted-foreground); }
.hint { font-size: 12px; color: var(--cm-muted-foreground); }
.side-title { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 13px; font-weight: 600; }
.scene-list { padding: 12px; display: flex; flex-direction: column; gap: 6px; }
.scene-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 6px; border: 1px solid transparent; background: transparent; color: var(--cm-foreground); font-size: 13px; font-weight: 500; cursor: pointer; text-align: left; }
.scene-item:hover { background: var(--cm-muted); }
.scene-item.primary { background: rgba(8, 145, 178, 0.08); border-color: rgba(8, 145, 178, 0.2); color: var(--cm-primary); }
.scene-item.primary svg { color: var(--cm-primary); }
.scene-item svg { color: var(--cm-muted-foreground); }
.side-section { padding: 12px 16px; border-top: 1px solid var(--cm-border); }
.prompt-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.prompt-chips button { padding: 5px 10px; border-radius: 6px; font-size: 12px; border: 1px solid var(--cm-border); background: var(--cm-background); color: var(--cm-muted-foreground); cursor: pointer; }
.prompt-chips button:hover { border-color: var(--cm-primary); color: var(--cm-primary); }
@media (max-width: 1100px) { .sidebar-right { display: none; } }
@media (max-width: 860px) { .sidebar-left { display: none; } }
</style>
