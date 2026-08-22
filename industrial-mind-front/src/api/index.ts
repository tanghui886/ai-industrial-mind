/** API 层：统一封装后端 /api/v1 接口 */
import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// 请求拦截：携带登录用户身份头，后端据此做角色权限校验
http.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem('cm_user')
    if (raw) {
      const user = JSON.parse(raw)
      if (user?.username) config.headers['X-Username'] = user.username
    }
  } catch { /* ignore */ }
  return config
})

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const msg = err?.response?.data?.detail || err?.message || '请求失败'
    return Promise.reject(new Error(msg))
  },
)

// ---------- 元数据 ----------
export const getFactories = () => http.get('/meta/factories') as Promise<any[]>
export const getLines = () => http.get('/meta/lines') as Promise<any[]>
export const getBoxTypes = () => http.get('/meta/box-types') as Promise<any[]>
export const getMaterials = () => http.get('/meta/materials') as Promise<any[]>

// ---------- 认证 ----------
export const login = (data: { username: string; password: string }) =>
  http.post('/auth/login', data) as Promise<any>
export const authMe = () => http.get('/auth/me') as Promise<any>

// ---------- 系统管理（仅管理员） ----------
export const getUsers = () => http.get('/admin/users') as Promise<any[]>
export const createUser = (data: any) => http.post('/admin/users', data) as Promise<any>
export const updateUser = (id: number, data: any) => http.put(`/admin/users/${id}`, data) as Promise<any>
export const deleteUser = (id: number) => http.delete(`/admin/users/${id}`) as Promise<any>
export const resetUserPassword = (id: number) =>
  http.post(`/admin/users/${id}/reset-password`) as Promise<any>
export const getPermissions = () => http.get('/admin/permissions') as Promise<any>
export const savePermissions = (data: { role: string; perms: string[] }) =>
  http.put('/admin/permissions', data) as Promise<any>
// 角色管理
export const getRoles = () => http.get('/admin/roles') as Promise<any[]>
export const createRole = (data: { name: string; description?: string }) =>
  http.post('/admin/roles', data) as Promise<any>
export const updateRole = (name: string, data: { name: string; description?: string }) =>
  http.put(`/admin/roles/${encodeURIComponent(name)}`, data) as Promise<any>
export const deleteRole = (name: string) =>
  http.delete(`/admin/roles/${encodeURIComponent(name)}`) as Promise<any>
// 菜单配置（角色勾选可见菜单）
export const getMenus = () => http.get('/admin/menus') as Promise<any>
export const saveMenus = (data: { role: string; menus: string[] }) =>
  http.put('/admin/menus', data) as Promise<any>
// 菜单定义管理（菜单管理页 CRUD）
export const getMenuDefs = () => http.get('/admin/menu-defs') as Promise<any[]>
export const createMenuDef = (data: any) => http.post('/admin/menu-defs', data) as Promise<any>
export const updateMenuDef = (code: string, data: any) =>
  http.put(`/admin/menu-defs/${encodeURIComponent(code)}`, data) as Promise<any>
export const deleteMenuDef = (code: string) =>
  http.delete(`/admin/menu-defs/${encodeURIComponent(code)}`) as Promise<any>

// ---------- 物料维护 ----------
export const getMaterialList = () => http.get('/material/list') as Promise<any[]>
export const getMaterialStats = () => http.get('/material/stats') as Promise<any>
export const createMaterial = (data: any) => http.post('/material/', data) as Promise<any>
export const updateMaterial = (id: number, data: any) =>
  http.put(`/material/${id}`, data) as Promise<any>
export const deleteMaterial = (id: number) => http.delete(`/material/${id}`) as Promise<any>

// ---------- 供货商动态 ----------
export const getSupplierAvailability = (params?: { supplier?: string; material?: string; months?: number }) =>
  http.get('/supplier/availability', { params }) as Promise<any>
export const getSupplierOptions = () => http.get('/supplier/options') as Promise<any>

// ---------- 设备管理 ----------
export const getStorageList = () => http.get('/storage/list') as Promise<any[]>
export const updateStorageCapacity = (data: { line_code: string; storage_capacity: number }) =>
  http.put('/storage/capacity', data) as Promise<any>
export const getDeviceList = (params?: { line_code?: string; status?: string; keyword?: string }) =>
  http.get('/device/list', { params }) as Promise<any[]>
export const getDeviceScreen = () => http.get('/device/screen') as Promise<any>

// ---------- 成本动因 ----------
export const getCostScreen = (params?: { line_code?: string; work_order_no?: string }) =>
  http.get('/cost/screen', { params }) as Promise<any>
export const getCostOptions = () => http.get('/cost/options') as Promise<any>
export const getCostDrivers = (params?: { dimension?: string; period?: string; line_code?: string; work_order_no?: string }) =>
  http.get('/cost/drivers', { params }) as Promise<any[]>
export const getCostWorkOrders = (params?: { line_code?: string; month?: string; keyword?: string }) =>
  http.get('/cost/work-orders', { params }) as Promise<any[]>
export const getCostMaterialDetails = (params?: { line_code?: string; work_order_no?: string; material_code?: string }) =>
  http.get('/cost/material-details', { params }) as Promise<any[]>
export const createCostDriver = (data: any) => http.post('/cost/drivers', data) as Promise<any>
export const updateCostDriver = (id: number, data: any) =>
  http.put(`/cost/drivers/${id}`, data) as Promise<any>
export const deleteCostDriver = (id: number) => http.delete(`/cost/drivers/${id}`) as Promise<any>

// ---------- 成本动因基准配置 ----------
export const getCostBaselines = (params?: { customer?: string; box_type?: string }) =>
  http.get('/cost/baselines', { params }) as Promise<any[]>
export const initCostBaseline = (params?: { work_order_no?: string; customer?: string; box_type?: string }) =>
  http.get('/cost/baselines/init', { params }) as Promise<any>
export const saveCostBaseline = (data: any) => http.post('/cost/baselines', data) as Promise<any>
export const updateCostBaseline = (id: number, data: any) =>
  http.put(`/cost/baselines/${id}`, data) as Promise<any>
export const deleteCostBaseline = (id: number) => http.delete(`/cost/baselines/${id}`) as Promise<any>

// ---------- 成本动因分析 ----------
export const analyzeCost = (data: { mode?: string; work_order_no?: string; customer?: string; box_type?: string; force?: boolean }) =>
  http.post('/cost/analyze', data) as Promise<any>
export const getCostAnalysisRecords = (params?: { work_order_no?: string; customer?: string; box_type?: string }) =>
  http.get('/cost/analysis-records', { params }) as Promise<any[]>
export const getCostAnalysisSummary = () =>
  http.get('/cost/analysis-summary') as Promise<any>

// ---------- 模型调用记录 ----------
export const getLlmLogs = (params?: { scene?: string; user?: string; session_id?: string; success?: boolean; date_from?: string; date_to?: string; page?: number; page_size?: number }) =>
  http.get('/llm-log/records', { params }) as Promise<any>

// ---------- 总览大屏 ----------
export const getDashboard = (line_code = 'PD-D') =>
  http.get('/dashboard/overview', { params: { line_code } }) as Promise<any>

// ---------- 排产 ----------
export const getSchedule = (params: { line_code: string; month: string }) =>
  http.get('/planning/schedule', { params }) as Promise<any>
export const getCalendar = (params: { line_code: string; month: string }) =>
  http.get('/planning/calendar', { params }) as Promise<any[]>
export const updateCalendar = (line_code: string, data: any) =>
  http.put('/planning/calendar', data, { params: { line_code } }) as Promise<any>
export const saveCalendarBatch = (line_code: string, items: any[]) =>
  http.post('/planning/calendar/batch', items, { params: { line_code } }) as Promise<any>
export const getGantt = (params: { line_code: string; month: string }) =>
  http.get('/planning/gantt-data', { params }) as Promise<any[]>
export const getGanttDays = (params: { line_code: string; month: string }) =>
  http.get('/planning/gantt-days', { params }) as Promise<any>
export const saveGanttDays = (line_code: string, items: any[]) =>
  http.post('/planning/gantt-days', items, { params: { line_code } }) as Promise<any>
export const smartAnalyzeAdjusted = (data: any) =>
  http.post('/planning/smart/adjust-analyze', data) as Promise<any>
export const getConflicts = (params: { line_code: string; month: string }) =>
  http.get('/planning/conflicts', { params }) as Promise<any[]>
export const getCapacitySummary = (params: { line_code: string; month: string }) =>
  http.get('/planning/capacity-summary', { params }) as Promise<any>
export const smartPlan = (data: {
  line_code: string
  month: string
  apply?: boolean
  work_order_no?: string
  proposals?: any[]
}) => http.post('/planning/smart', data) as Promise<any>
export const whatIf = (data: { box_type: string; quantity: number; delivery_date: string; delivery_location?: string }) =>
  http.post('/planning/what-if', data) as Promise<any>
export const createWorkOrder = (data: any) => http.post('/planning/manual', data) as Promise<any>
export const confirmSchedule = (id: number, operator: string) =>
  http.post(`/planning/schedule/${id}/confirm`, null, { params: { operator } }) as Promise<any>
export const deleteSchedule = (id: number) => http.delete(`/planning/schedule/${id}`) as Promise<any>

// ---------- 审批 ----------
export const getApprovals = (params?: any) => http.get('/approval/list', { params }) as Promise<any>
export const getApprovalDetail = (id: number) => http.get(`/approval/${id}`) as Promise<any>
export const approveOrReject = (id: number, action: 'approve' | 'reject', data: { operator: string; comment?: string }) =>
  http.post(`/approval/${id}/${action}`, data) as Promise<any>

// ---------- Agent 编排 ----------
export const chat = (data: { message: string; source?: string; user?: string; session_id?: string }) =>
  http.post('/orchestrator/chat', data) as Promise<any>
export const getChatSessions = () => http.get('/chat/sessions') as Promise<any[]>
export const createChatSession = (data: { title?: string }) =>
  http.post('/chat/sessions', data) as Promise<any>
export const deleteChatSession = (session_id: string) =>
  http.delete(`/chat/sessions/${session_id}`) as Promise<any>
export const getChatMessages = (session_id: string) =>
  http.get(`/chat/sessions/${session_id}/messages`) as Promise<any[]>
export const getAgentStatus = () => http.get('/agents/status') as Promise<any>
export const agentDiagnosis = (device_id: string) =>
  http.get('/agents/diagnosis', { params: { device_id } }) as Promise<any>
export const agentSupply = () => http.get('/agents/supply-chain') as Promise<any>
export const agentCost = () => http.get('/agents/cost-analysis') as Promise<any>

/** SSE 流式对话：逐事件回调 */
export function chatStream(payload: { message: string; source?: string; user?: string; session_id?: string }, onEvent: (ev: any) => void) {
  // EventSource 无法携带自定义请求头，将当前用户注入 payload 传给后端做持久化
  let user = payload.user
  if (!user) {
    try {
      const raw = localStorage.getItem('cm_user')
      if (raw) user = JSON.parse(raw)?.username
    } catch { /* ignore */ }
  }
  const token = JSON.stringify({ ...payload, user })
  const es = new EventSource(`/api/v1/orchestrator/chat/stream?payload=${encodeURIComponent(token)}`)
  const handlerMap: Record<string, string[]> = {}
  es.onmessage = (e) => {
    try { onEvent({ event: 'message', data: JSON.parse(e.data) }) } catch { onEvent({ event: 'message', data: e.data }) }
  }
  for (const name of ['intent', 'thinking', 'tool', 'result', 'done', 'error']) {
    es.addEventListener(name, (e: any) => {
      try { onEvent({ event: name, data: JSON.parse(e.data) }) } catch { onEvent({ event: name, data: e.data }) }
    })
  }
  return es
}

// ---------- 移动端 ----------
export const quickOrder = (text: string) => http.post('/mobile/quick-order', { text }) as Promise<any>
export const confirmQuickOrder = (data: any) => http.post('/mobile/quick-order/confirm', data) as Promise<any>
export const getMyOrders = (user?: string) =>
  http.get('/mobile/my-orders', { params: user ? { user } : {} }) as Promise<any[]>
export const getCapacityBrief = (params: { line_code: string; month: string }) =>
  http.get('/mobile/capacity-brief', { params }) as Promise<any>
export const getDayOrders = (day: string, line_code = 'PD-D') =>
  http.get('/mobile/day-orders', { params: { day, line_code } }) as Promise<any[]>
export const getNotifications = (user?: string) =>
  http.get('/mobile/notifications', { params: user ? { user } : {} }) as Promise<any>
export const getMobileApprovals = (status?: string) =>
  http.get('/mobile/approvals', { params: status ? { status } : {} }) as Promise<any>
export const mobileApprove = (id: number, data: any) =>
  http.post(`/mobile/approvals/${id}/approve`, data) as Promise<any>
