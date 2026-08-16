import { createRouter, createWebHistory } from 'vue-router'
import { currentUser, hasMenu } from '@/utils/permission'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    { path: '/', redirect: '/pc/dashboard' },
    // PC 端
    {
      path: '/pc',
      component: () => import('@/layouts/PcLayout.vue'),
      redirect: '/pc/dashboard',
      children: [
        { path: 'dashboard', name: 'pc-dashboard', component: () => import('@/views/pc/DashboardView.vue'), meta: { title: '产线总览' } },
        { path: 'planning', name: 'pc-planning', component: () => import('@/views/pc/PlanningView.vue'), meta: { title: '排产工作台' } },
        { path: 'agent', name: 'pc-agent', component: () => import('@/views/pc/AgentChatView.vue'), meta: { title: 'Agent 对话台' } },
        { path: 'approval', name: 'pc-approval', component: () => import('@/views/pc/ApprovalView.vue'), meta: { title: '审批工作台' } },
        { path: 'material', name: 'pc-material', component: () => import('@/views/pc/MaterialManageView.vue'), meta: { title: '物料维护', menu: 'material' } },
        { path: 'storage', name: 'pc-storage', component: () => import('@/views/pc/StorageView.vue'), meta: { title: '堆存管理', menu: 'storage' } },
        { path: 'device', name: 'pc-device', component: () => import('@/views/pc/DeviceScreenView.vue'), meta: { title: '设备异常大屏', menu: 'device' } },
        { path: 'device-manage', name: 'pc-device-manage', component: () => import('@/views/pc/DeviceManageView.vue'), meta: { title: '设备管理', menu: 'device' } },
        { path: 'cost', name: 'pc-cost', component: () => import('@/views/pc/CostScreenView.vue'), meta: { title: '成本动因大屏', menu: 'cost' } },
        { path: 'cost-manage', name: 'pc-cost-manage', component: () => import('@/views/pc/CostManageView.vue'), meta: { title: '成本动因管理', menu: 'cost' } },
        { path: 'cost-baseline', name: 'pc-cost-baseline', component: () => import('@/views/pc/CostBaselineView.vue'), meta: { title: '动因明细基准配置', menu: 'cost' } },
        { path: 'cost-analyze', name: 'pc-cost-analyze', component: () => import('@/views/pc/CostAnalyzeView.vue'), meta: { title: '成本动因分析', menu: 'cost' } },
        { path: 'cost-records', name: 'pc-cost-records', component: () => import('@/views/pc/CostAnalysisRecordsView.vue'), meta: { title: '成本动因分析明细', menu: 'cost' } },
        { path: 'cost-material-detail', name: 'pc-cost-material-detail', component: () => import('@/views/pc/CostMaterialDetailView.vue'), meta: { title: '物料明细', menu: 'cost' } },
        { path: 'users', name: 'pc-users', component: () => import('@/views/pc/UserManageView.vue'), meta: { title: '用户管理', admin: true } },
        { path: 'permissions', name: 'pc-permissions', component: () => import('@/views/pc/PermManageView.vue'), meta: { title: '权限管理', admin: true } },
        { path: 'roles', name: 'pc-roles', component: () => import('@/views/pc/RoleManageView.vue'), meta: { title: '角色管理', admin: true } },
        { path: 'llm-log', name: 'pc-llm-log', component: () => import('@/views/pc/ModelCallLogView.vue'), meta: { title: '模型调用记录', admin: true } },
      ],
    },
    // 移动端
    {
      path: '/m',
      component: () => import('@/layouts/MobileLayout.vue'),
      redirect: '/m/quick-order',
      children: [
        { path: 'quick-order', name: 'm-quick-order', component: () => import('@/views/mobile/QuickOrderView.vue'), meta: { title: '现场接单' } },
        { path: 'schedule', name: 'm-schedule', component: () => import('@/views/mobile/ScheduleView.vue'), meta: { title: '排产查看' } },
        { path: 'approvals', name: 'm-approvals', component: () => import('@/views/mobile/ApprovalView.vue'), meta: { title: '审批中心' } },
      ],
    },
  ],
})

router.afterEach((to) => {
  const t = to.meta.title as string | undefined
  document.title = t ? `${t} · ContainerMind` : 'ContainerMind'
})

// 登录守卫：未登录跳转登录页；无权限访问的页面跳转总览
router.beforeEach((to) => {
  const isLoggedIn = !!localStorage.getItem('cm_token')
  if (!isLoggedIn && to.path !== '/login') return { path: '/login' }
  if (isLoggedIn && to.path === '/login') return { path: '/pc/dashboard' }
  if (to.meta.admin && currentUser().role !== '管理员') return { path: '/pc/dashboard' }
  if (to.meta.menu && !hasMenu(to.meta.menu as string)) return { path: '/pc/dashboard' }
  return true
})

export default router
