<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Mic, CalendarRange, ClipboardCheck } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()

const tabs = [
  { path: '/m/quick-order', label: '现场接单', icon: Mic },
  { path: '/m/schedule', label: '排产查看', icon: CalendarRange },
  { path: '/m/approvals', label: '审批中心', icon: ClipboardCheck },
]
</script>

<template>
  <div class="m-shell">
    <main class="m-body">
      <router-view />
    </main>
    <nav class="m-tabbar">
      <a v-for="t in tabs" :key="t.path" class="m-tab" :class="{ active: route.path === t.path }"
         @click.prevent="router.push(t.path)">
        <component :is="t.icon" :size="20" />
        <span>{{ t.label }}</span>
      </a>
    </nav>
  </div>
</template>

<style scoped>
.m-shell {
  max-width: 420px; margin: 0 auto; min-height: 100vh;
  background: var(--cm-slate-50); position: relative;
  box-shadow: 0 0 40px rgba(15, 23, 42, 0.08);
}
.m-body { padding-bottom: 72px; }
.m-tabbar {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 100%; max-width: 420px; display: flex;
  background: var(--cm-card); border-top: 1px solid var(--cm-border);
  z-index: 100;
}
.m-tab {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 10px 0 8px; color: var(--cm-slate-400); font-size: 11px; cursor: pointer;
  text-decoration: none;
}
.m-tab.active { color: var(--cm-primary); font-weight: 500; }
</style>
