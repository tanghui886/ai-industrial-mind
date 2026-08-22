/** 前端权限工具：按钮权限编码（perm_code）判断，与后端 app/permissions.py 保持一致
 *
 * 权限来源：登录/`/auth/me` 接口返回的 perms 数组，存放于 localStorage['cm_perms']；
 * 管理员角色拥有全部按钮权限。
 * 按钮权限由管理员在「权限管理」页可配置，前端据此控制按钮显隐。
 */

export interface CmUser {
  username?: string
  display_name?: string
  role?: string
  phone?: string
}

/** 菜单节点：与后端 /auth 返回的 menu_tree 结构一致 */
export interface CmMenu {
  code: string
  name: string
  path?: string
  parent_code?: string
  icon?: string
  sort_order?: number
  admin_only?: boolean
  children?: CmMenu[]
}

export function currentUser(): CmUser {
  try {
    return JSON.parse(localStorage.getItem('cm_user') || '{}')
  } catch {
    return {}
  }
}

export function currentPerms(): string[] {
  try {
    const raw = localStorage.getItem('cm_perms')
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

/** 当前用户可见菜单编码（登录/`/auth/me` 返回，存于 cm_menus） */
export function currentMenus(): string[] {
  try {
    const raw = localStorage.getItem('cm_menus')
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

/** 当前用户可见菜单树（登录/`/auth/me` 返回，存于 cm_menu_tree，用于动态渲染导航） */
export function currentMenuTree(): CmMenu[] {
  try {
    const raw = localStorage.getItem('cm_menu_tree')
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return []
}

export function isAdmin(): boolean {
  return currentUser().role === '管理员'
}

/** 是否可见某菜单（管理员恒为 true） */
export function hasMenu(...codes: string[]): boolean {
  if (isAdmin()) return true
  const menus = currentMenus()
  return codes.some((c) => menus.includes(c))
}

/** 是否拥有任一给定按钮权限（管理员恒为 true） */
export function hasPerm(...codes: string[]): boolean {
  if (isAdmin()) return true
  const perms = currentPerms()
  return codes.some((c) => perms.includes(c))
}

/** 统一写入登录态：cm_user（用户信息）+ cm_perms（按钮权限）+ cm_menus（可见菜单）+ cm_menu_tree（菜单树） */
export function persistAuth(data: { user?: CmUser; perms?: string[]; menus?: string[]; menu_tree?: CmMenu[] }): void {
  if (data.user) localStorage.setItem('cm_user', JSON.stringify(data.user))
  if (data.perms) localStorage.setItem('cm_perms', JSON.stringify(data.perms))
  if (data.menus) localStorage.setItem('cm_menus', JSON.stringify(data.menus))
  if (data.menu_tree) localStorage.setItem('cm_menu_tree', JSON.stringify(data.menu_tree))
}

export function clearAuth(): void {
  localStorage.removeItem('cm_token')
  localStorage.removeItem('cm_user')
  localStorage.removeItem('cm_perms')
  localStorage.removeItem('cm_menus')
  localStorage.removeItem('cm_menu_tree')
}

// 用户角色 -> 权限组（与后端一致，用于展示/粗略分组）
const ROLE_GROUP: Record<string, string> = {
  管理员: 'admin',
  业务经理: 'business',
  计划员: 'planner',
  生产主管: 'approver',
  设备主管: 'approver',
  采购专员: 'viewer',
  财务专员: 'viewer',
}

export function userGroup(): string {
  return ROLE_GROUP[currentUser().role ?? ''] ?? 'viewer'
}

// 添加工令 / 编辑 / 删除工令
export const canAddWorkOrder = () => hasPerm('workorder.add')
export const canEditWorkOrder = () => hasPerm('workorder.edit')
export const canDeleteWorkOrder = () => hasPerm('workorder.delete')
// 排产（确认/甘特）、智能排产、排班配置
export const canSchedule = () => hasPerm('planning.schedule')
export const canSmartPlan = () => hasPerm('planning.smart')
export const canConfigCalendar = () => hasPerm('planning.calendar')
// 审批：通过 / 驳回 / 转交
export const canApprove = () => hasPerm('approval.approve')
export const canReject = () => hasPerm('approval.reject')
export const canTransfer = () => hasPerm('approval.transfer')
// 编辑/删除工令（任一即可，兼容旧调用）
export const canManageWorkOrder = () => hasPerm('workorder.edit', 'workorder.delete')
// 物料维护
export const canManageMaterial = () => hasPerm('material.manage')
