<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Save, ShieldCheck } from 'lucide-vue-next'
import { getPermissions, savePermissions } from '@/api'

const loading = ref(false)
const saving = ref(false)
const defs = ref<{ code: string; name: string }[]>([])
const roles = ref<string[]>([])
const config = ref<Record<string, string[]>>({})
const orig = ref<Record<string, string[]>>({})

const dirtyRoles = computed(() => {
  const diff: string[] = []
  for (const r of roles.value) {
    if (r === '管理员') continue
    const a = [...(config.value[r] ?? [])].sort()
    const b = [...(orig.value[r] ?? [])].sort()
    if (a.join(',') !== b.join(',')) diff.push(r)
  }
  return diff
})

async function load() {
  loading.value = true
  try {
    const data = await getPermissions()
    defs.value = data.defs ?? []
    roles.value = data.roles ?? []
    config.value = JSON.parse(JSON.stringify(data.config ?? {}))
    orig.value = JSON.parse(JSON.stringify(config.value))
  } finally { loading.value = false }
}

function has(role: string, code: string) { return (config.value[role] ?? []).includes(code) }

function toggle(role: string, code: string) {
  if (role === '管理员') return
  const arr = config.value[role] ?? []
  if (arr.includes(code)) config.value[role] = arr.filter((c) => c !== code)
  else config.value[role] = [...arr, code]
}

async function save() {
  const diff = dirtyRoles.value
  if (!diff.length) { ElMessage.info('没有需要保存的变更'); return }
  saving.value = true
  try {
    for (const r of diff) {
      await savePermissions({ role: r, perms: config.value[r] ?? [] })
    }
    ElMessage.success(`已保存 ${diff.length} 个角色的按钮权限`)
    await load()
  } catch (e: any) { ElMessage.error(e.message) } finally { saving.value = false }
}

onMounted(load)
</script>

<template>
  <div class="perm-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">权限管理</h1>
        <p class="page-sub">为各角色配置按钮权限（勾选即授权），保存后立即生效；管理员拥有全部权限</p>
      </div>
      <div class="head-right">
        <button class="btn primary" :disabled="saving || !dirtyRoles.length" @click="save">
          <Save :size="15" /> 保存配置<template v-if="dirtyRoles.length">（{{ dirtyRoles.length }}）</template>
        </button>
      </div>
    </section>

    <section class="card">
      <div class="matrix-scroll">
        <table class="perm-matrix">
          <thead>
            <tr>
              <th class="col-role">角色</th>
              <th v-for="d in defs" :key="d.code" class="col-perm">{{ d.name }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in roles" :key="r" :class="{ admin: r === '管理员', dirty: dirtyRoles.includes(r) }">
              <td class="col-role">
                <span class="role-chip">{{ r }}</span>
                <span v-if="r === '管理员'" class="muted small">（全部）</span>
              </td>
              <td v-for="d in defs" :key="d.code" class="col-perm">
                <label class="checkbox" :class="{ disabled: r === '管理员' }">
                  <input type="checkbox" :checked="has(r, d.code)" :disabled="r === '管理员'" @change="toggle(r, d.code)" />
                  <span class="box"></span>
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="foot-tip"><ShieldCheck :size="14" /> 权限变更保存在 role_permission 表；已登录用户下次进入页面（或刷新）后生效。</p>
    </section>
  </div>
</template>

<style scoped>
.perm-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; gap: 10px; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 4px 0; }
.matrix-scroll { overflow-x: auto; }
.perm-matrix { border-collapse: collapse; width: 100%; min-width: 900px; }
.perm-matrix th, .perm-matrix td { border-bottom: 1px solid var(--cm-border); padding: 10px 14px; text-align: center; }
.perm-matrix thead th {
  position: sticky; top: 0; background: var(--cm-muted); color: var(--cm-muted-foreground);
  font-size: 12px; font-weight: 600; white-space: nowrap;
}
.col-role { text-align: left !important; min-width: 170px; }
.col-perm { min-width: 96px; }
.role-chip { display: inline-block; padding: 3px 10px; border-radius: 999px; background: var(--cm-primary-50); color: var(--cm-primary); font-size: 12px; font-weight: 500; }
tr.dirty .role-chip { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
tr.admin td { background: rgba(148, 163, 184, 0.06); }
.muted { color: var(--cm-muted-foreground); }
.small { font-size: 12px; }
.checkbox { display: inline-flex; align-items: center; cursor: pointer; }
.checkbox input { position: absolute; opacity: 0; pointer-events: none; }
.checkbox .box {
  width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid var(--cm-input);
  background: var(--cm-card); position: relative; transition: all .15s;
}
.checkbox input:checked + .box { background: var(--cm-primary); border-color: var(--cm-primary); }
.checkbox input:checked + .box::after {
  content: ''; position: absolute; left: 5.5px; top: 2px; width: 4px; height: 8px;
  border: solid #fff; border-width: 0 2px 2px 0; transform: rotate(45deg);
}
.checkbox.disabled { cursor: not-allowed; }
.checkbox.disabled .box { background: var(--cm-muted); border-color: var(--cm-input); }
.checkbox.disabled input:checked + .box::after { border-color: var(--cm-muted-foreground); }
.foot-tip { display: flex; align-items: center; gap: 6px; padding: 12px 16px; font-size: 12px; color: var(--cm-muted-foreground); margin: 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
