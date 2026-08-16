<script setup lang="ts">
import { onMounted } from 'vue'
import { authMe } from '@/api'
import { persistAuth } from '@/utils/permission'

// 根组件：仅承载路由出口（布局由各路由的布局组件负责）
// 启动时刷新一次登录用户信息与按钮权限，保证管理员改权限后无需重新登录
onMounted(async () => {
  if (!localStorage.getItem('cm_token')) return
  try {
    const data = await authMe()
    persistAuth({ user: data, perms: data.perms, menus: data.menus })
  } catch { /* 后端未就绪时忽略，保持本地登录态 */ }
})
</script>

<template>
  <router-view />
</template>
