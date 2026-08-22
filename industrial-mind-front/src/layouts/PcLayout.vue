<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Container, LogOut, ChevronDown, Circle } from 'lucide-vue-next'
import * as Icons from 'lucide-vue-next'
import { authMe } from '@/api'
import { currentMenuTree, currentUser, persistAuth, clearAuth } from '@/utils/permission'
import type { CmMenu } from '@/utils/permission'

const route = useRoute()
const router = useRouter()
const factory = ref('PD-D')

/** 由后端返回的 menu_tree 动态渲染导航（按角色配置，无需前端硬编码） */
const navs = computed(() => currentMenuTree().map(mapNode))

function mapNode(n: CmMenu): any {
  const icon = (Icons as any)[n.icon] || Circle
  return {
    code: n.code,
    label: n.name,
    path: n.path,
    icon,
    children: (n.children ?? []).map(mapNode),
  }
}

function isActive(n: any): boolean {
  if (n.children && n.children.length) return n.children.some((c: any) => route.path === c.path)
  return route.path === n.path
}

function logout() {
  clearAuth()
  router.push('/login')
}

// 刷新登录信息 + 按钮权限 + 菜单树
onMounted(async () => {
  if (!localStorage.getItem('cm_token')) return
  try {
    const data = await authMe()
    persistAuth({ user: data, perms: data.perms, menus: data.menus, menu_tree: data.menu_tree })
  } catch { /* 忽略 */ }
})
</script>

<template>
  <div class="pc-shell">
    <header class="cm-topbar">
      <div class="cm-topbar-start">
        <a class="cm-brand" @click.prevent="router.push('/pc/dashboard')">
          <Container class="brand-icon" :size="26" />
          <span class="brand-text">ContainerMind</span>
        </a>
        <nav class="cm-nav" aria-label="全局导航">
          <template v-for="n in navs" :key="n.label || n.path">
            <!-- 分组菜单（二级菜单） -->
            <div v-if="n.children && n.children.length" class="nav-group" :class="{ active: isActive(n) }">
              <a class="nav-group-trigger" @click.prevent="router.push(n.children[0].path)">
                <component :is="n.icon" :size="15" />
                <span>{{ n.label }}</span>
                <ChevronDown :size="14" class="caret" />
              </a>
              <div class="nav-dropdown">
                <router-link v-for="c in n.children" :key="c.path" :to="c.path"
                             class="nav-drop-link" :class="{ active: route.path === c.path }">
                  <span>{{ c.label }}</span>
                </router-link>
              </div>
            </div>
            <!-- 普通菜单 -->
            <router-link v-else :to="n.path" class="cm-nav-link" :class="{ active: isActive(n) }">
              <component :is="n.icon" :size="15" />
              <span>{{ n.label }}</span>
            </router-link>
          </template>
        </nav>
      </div>
      <div class="cm-topbar-end">
        <div class="cm-user">
          <div class="user-meta">
            <div class="user-name">{{ currentUser().display_name || '未登录' }}</div>
            <div class="user-role">{{ currentUser().role || '—' }}</div>
          </div>
          <div class="user-avatar">{{ (currentUser().display_name || '?').slice(0, 1) }}</div>
          <a class="logout-btn" title="退出登录" @click="logout"><LogOut :size="15" /></a>
        </div>
        <a class="mobile-entry" @click.prevent="router.push('/m/quick-order')">移动端</a>
      </div>
    </header>
    <main class="pc-main">
      <router-view :key="factory" />
    </main>
  </div>
</template>

<style scoped>
.pc-shell { min-height: 100vh; }
.cm-topbar {
  position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  height: var(--cm-topbar-h); padding: 0 24px;
  background: var(--cm-card); border-bottom: 1px solid var(--cm-border);
}
.cm-topbar-start, .cm-topbar-end { display: flex; align-items: center; gap: 16px; }
.cm-brand { display: flex; align-items: center; gap: 8px; cursor: pointer; text-decoration: none; color: var(--cm-foreground); }
.brand-icon { color: var(--cm-primary); }
.brand-text { font-size: 18px; font-weight: 600; letter-spacing: -0.02em; }
.cm-nav { display: flex; align-items: center; gap: 8px; margin-left: 24px; }
.cm-nav-link {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
  border-radius: var(--cm-radius-medium); color: var(--cm-slate-600);
  text-decoration: none; font-size: 14px; font-weight: 500;
}
.cm-nav-link:hover { background: var(--cm-slate-100); color: var(--cm-slate-900); }
.cm-nav-link.active { background: var(--cm-primary-50); color: var(--cm-primary); }
.nav-group { position: relative; }
.nav-group-trigger {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
  border-radius: var(--cm-radius-medium); color: var(--cm-slate-600);
  text-decoration: none; font-size: 14px; font-weight: 500; cursor: pointer; user-select: none;
}
.nav-group-trigger:hover { background: var(--cm-slate-100); color: var(--cm-slate-900); }
.nav-group.active > .nav-group-trigger { background: var(--cm-primary-50); color: var(--cm-primary); }
.nav-group-trigger .caret { transition: transform .15s; }
.nav-group:hover .caret, .nav-group.active .caret { transform: rotate(180deg); }
.nav-dropdown {
  position: absolute; top: calc(100% + 6px); left: 0; min-width: 180px;
  background: var(--cm-card); border: 1px solid var(--cm-border); border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, .12); padding: 6px; z-index: 200;
  opacity: 0; visibility: hidden; transform: translateY(6px); transition: all .15s;
}
.nav-group:hover .nav-dropdown, .nav-group:focus-within .nav-dropdown { opacity: 1; visibility: visible; transform: translateY(0); }
.nav-drop-link {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 8px;
  color: var(--cm-slate-600); text-decoration: none; font-size: 13.5px; font-weight: 500;
}
.nav-drop-link:hover { background: var(--cm-slate-100); color: var(--cm-slate-900); }
.nav-drop-link.active { background: var(--cm-primary-50); color: var(--cm-primary); }
.cm-factory-select {
  display: flex; align-items: center; gap: 8px; padding: 6px 12px;
  border: 1px solid var(--cm-border); border-radius: var(--cm-radius-medium);
  background: var(--cm-muted); font-size: 13px;
}
.cm-factory-select select {
  background: transparent; border: none; outline: none; font-size: 13px;
  cursor: pointer; color: var(--cm-foreground);
}
.cm-user { display: flex; align-items: center; gap: 12px; padding-left: 16px; border-left: 1px solid var(--cm-border); }
.user-meta { text-align: right; }
.user-name { font-size: 14px; font-weight: 500; }
.user-role { font-size: 12px; color: var(--cm-muted-foreground); }
.user-avatar {
  width: 36px; height: 36px; border-radius: 999px; background: var(--cm-primary);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600;
}
.logout-btn {
  display: flex; align-items: center; color: var(--cm-slate-500); cursor: pointer;
  padding: 6px; border-radius: 6px; transition: color .15s, background .15s;
}
.logout-btn:hover { color: var(--cm-primary); background: var(--cm-primary-50); }
.mobile-entry { font-size: 12px; color: var(--cm-primary); cursor: pointer; text-decoration: none; padding-left: 12px; border-left: 1px solid var(--cm-border); }
.pc-main { min-width: 1080px; }
</style>
