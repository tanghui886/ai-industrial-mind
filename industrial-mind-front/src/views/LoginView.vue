<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User, Boxes } from 'lucide-vue-next'
import { login } from '@/api'
import { persistAuth } from '@/utils/permission'

const router = useRouter()
const form = ref({ username: 'admin', password: '123456' })
const loading = ref(false)

async function onSubmit() {
  if (!form.value.username || !form.value.password) { ElMessage.warning('请输入用户名和密码'); return }
  if (form.value.username === 'zhang' && form.value.password === '123456') {
    localStorage.setItem('cm_token', 'demo')
    persistAuth({
      user: { username: 'zhang', display_name: '张业务', role: '业务经理' },
      perms: ['workorder.add', 'workorder.edit', 'workorder.delete'],
      menus: ['dashboard', 'planning', 'agent', 'approval'],
      menu_tree: [
        { code: 'dashboard', name: '产线总览', path: '/pc/dashboard', icon: 'LayoutDashboard' },
        { code: 'agent', name: 'Agent 对话台', path: '/pc/agent', icon: 'BotMessageSquare' },
        { code: 'planning', name: '排产工作台', path: '/pc/planning', icon: 'CalendarDays' },
        { code: 'approval', name: '审批工作台', path: '/pc/approval', icon: 'ClipboardCheck' },
      ],
    })
    ElMessage.success('登录成功')
    router.push('/pc/dashboard')
    return
  }
  loading.value = true
  try {
    const res = await login({ username: form.value.username, password: form.value.password })
    localStorage.setItem('cm_token', res.token)
    persistAuth({ user: res.user, perms: res.perms, menus: res.menus, menu_tree: res.menu_tree })
    ElMessage.success('登录成功')
    router.push('/pc/dashboard')
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="brand">
        <div class="brand-logo"><Boxes :size="30" /></div>
        <h1 class="brand-title">ContainerMind</h1>
        <p class="brand-sub">集装箱制造业工业 Agent 协同系统</p>
      </div>
      <el-form class="login-form" label-position="top" @submit.prevent="onSubmit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" :prefix-icon="Lock"
                    show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button class="login-btn" type="primary" size="large" :loading="loading" @click="onSubmit">
          登 录
        </el-button>
      </el-form>
      <div class="login-tip">
        演示账号：
		<div>
		<span class="mono">管理员：admin / 123456</span><br/>
		<span class="mono">业务员：zhang / 123456</span><br/>
		<span class="mono">计划员：liji / 123456</span><br/>
		<span class="mono">审批员：zhu / 123456</span><br/>
		<span class="mono">采购员：chen / 123456</span>
		</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f2b46 0%, #14507a 55%, #1f6f8b 100%);
  padding: 24px;
}
.login-card {
  width: 400px;
  background: #fff;
  border-radius: 16px;
  padding: 40px 36px 28px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
}
.brand { text-align: center; margin-bottom: 28px; }
.brand-logo {
  width: 60px; height: 60px; margin: 0 auto 14px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 14px; color: #fff;
  background: linear-gradient(135deg, #14507a, #1f6f8b);
}
.brand-title { font-size: 22px; font-weight: 700; color: #12283f; margin: 0 0 4px; }
.brand-sub { font-size: 13px; color: #7a8a99; margin: 0; }
.login-form :deep(.el-form-item__label) { font-weight: 600; color: #33475b; }
.login-btn { width: 100%; margin-top: 6px; font-size: 16px; letter-spacing: 4px; }
.login-tip { margin-top: 18px; text-align: center; font-size: 12px; color: #8a97a5; }
.mono { font-family: Consolas, monospace; }
</style>