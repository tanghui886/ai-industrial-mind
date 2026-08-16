<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Pencil, Trash2, Save, UserCog } from 'lucide-vue-next'
import { getRoles, createRole, updateRole, deleteRole, getMenus, saveMenus } from '@/api'

const loading = ref(false)
const roles = ref<any[]>([])
const dialogVisible = ref(false)
const editing = ref<any | null>(null)
const form = ref({ name: '', description: '' })

// 菜单配置
const menuDefs = ref<{ code: string; name: string }[]>([])
const menuConfig = ref<Record<string, string[]>>({})
const menuOrig = ref<Record<string, string[]>>({})

const dirtyMenus = computed(() => {
  const diff: string[] = []
  for (const r of roles.value) {
    if (r.name === '管理员') continue
    const a = [...(menuConfig.value[r.name] ?? [])].sort()
    const b = [...(menuOrig.value[r.name] ?? [])].sort()
    if (a.join(',') !== b.join(',')) diff.push(r.name)
  }
  return diff
})

async function load() {
  loading.value = true
  try {
    roles.value = await getRoles()
  } finally { loading.value = false }
}

async function loadMenus() {
  try {
    const data = await getMenus()
    menuDefs.value = data.defs ?? []
    menuConfig.value = JSON.parse(JSON.stringify(data.config ?? {}))
    menuOrig.value = JSON.parse(JSON.stringify(menuConfig.value))
  } catch (e: any) { ElMessage.error(e.message) }
}

function openAdd() {
  editing.value = null
  form.value = { name: '', description: '' }
  dialogVisible.value = true
}

function openEdit(r: any) {
  editing.value = r
  form.value = { name: r.name, description: r.description || '' }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.name.trim()) { ElMessage.warning('请填写角色名称'); return }
  try {
    if (editing.value) {
      await updateRole(editing.value.name, form.value)
      ElMessage.success('角色已更新')
    } else {
      await createRole(form.value)
      ElMessage.success('角色已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function onDelete(r: any) {
  try {
    await ElMessageBox.confirm(`确认删除角色「${r.name}」？`, '删除角色', { type: 'warning' })
    await deleteRole(r.name)
    ElMessage.success('已删除')
    load()
  } catch { /* cancel */ }
}

function hasMenu(r: string, code: string) { return (menuConfig.value[r] ?? []).includes(code) }

function toggleMenu(r: string, code: string) {
  const arr = menuConfig.value[r] ?? []
  if (arr.includes(code)) menuConfig.value[r] = arr.filter((c) => c !== code)
  else menuConfig.value[r] = [...arr, code]
}

async function saveMenuConfig() {
  const diff = dirtyMenus.value
  if (!diff.length) { ElMessage.info('没有需要保存的菜单变更'); return }
  try {
    for (const r of diff) {
      await saveMenus({ role: r, menus: menuConfig.value[r] ?? [] })
    }
    ElMessage.success(`已保存 ${diff.length} 个角色的菜单`)
    await loadMenus()
  } catch (e: any) { ElMessage.error(e.message) }
}

onMounted(() => { load(); loadMenus() })
</script>

<template>
  <div class="role-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">角色管理</h1>
        <p class="page-sub">维护系统角色，并为各角色配置可见菜单（保存后刷新生效；管理员拥有全部菜单）</p>
      </div>
      <div class="head-right">
        <button class="btn primary" @click="openAdd"><Plus :size="15" /> 新增角色</button>
      </div>
    </section>

    <section class="card">
      <el-table :data="roles" style="width: 100%" stripe>
        <el-table-column label="角色" min-width="130">
          <template #default="{ row }">
            <span class="role-chip">{{ row.name }}</span>
            <span v-if="row.is_builtin" class="tag tag-warning">内置</span>
          </template>
        </el-table-column>
        <el-table-column label="说明" prop="description" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" width="160" align="center">
          <template #default="{ row }">
            <button class="op-btn" @click="openEdit(row)"><Pencil :size="14" /> 编辑</button>
            <button class="op-btn danger" :disabled="row.is_builtin" @click="onDelete(row)"><Trash2 :size="14" /> 删除</button>
          </template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!roles.length">暂无角色</p>
    </section>

    <section class="card menu-card">
      <div class="menu-head">
        <h2 class="cm-heading menu-title"><UserCog :size="16" /> 角色菜单配置</h2>
        <button class="btn primary" :disabled="!dirtyMenus.length" @click="saveMenuConfig">
          <Save :size="15" /> 保存菜单<template v-if="dirtyMenus.length">（{{ dirtyMenus.length }}）</template>
        </button>
      </div>
      <div class="matrix-scroll">
        <table class="menu-matrix">
          <thead>
            <tr>
              <th class="col-role">角色</th>
              <th v-for="d in menuDefs" :key="d.code" class="col-menu">{{ d.name }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in roles" :key="r.name" :class="{ admin: r.name === '管理员', dirty: dirtyMenus.includes(r.name) }">
              <td class="col-role">
                <span class="role-chip">{{ r.name }}</span>
                <span v-if="r.name === '管理员'" class="muted small">（全部）</span>
              </td>
              <td v-for="d in menuDefs" :key="d.code" class="col-menu">
                <label class="checkbox" :class="{ disabled: r.name === '管理员' }">
                  <input type="checkbox" :checked="hasMenu(r.name, d.code)" :disabled="r.name === '管理员'" @change="toggleMenu(r.name, d.code)" />
                  <span class="box"></span>
                </label>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="foot-tip"><UserCog :size="14" /> 菜单配置保存在 role_menu 表；已登录用户下次进入系统（或刷新）后按新菜单生效。</p>
    </section>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑角色' : '新增角色'" width="440px">
      <el-form label-width="80px">
        <el-form-item label="角色名称">
          <el-input v-model="form.name" :disabled="editing?.is_builtin" placeholder="如 仓储管理员" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="角色职责说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.role-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; gap: 10px; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; margin-bottom: 16px; }
.menu-card { padding: 4px; }
.menu-head { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.menu-title { margin: 0; font-size: 15px; display: inline-flex; align-items: center; gap: 6px; }
.role-chip { display: inline-block; padding: 3px 10px; border-radius: 999px; background: var(--cm-primary-50); color: var(--cm-primary); font-size: 12px; font-weight: 500; }
.tag { display: inline-flex; align-items: center; padding: 2px 8px; margin-left: 8px; font-size: 11px; font-weight: 500; border-radius: 4px; }
.tag-warning { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
.op-btn { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--cm-slate-600); cursor: pointer; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; }
.op-btn:hover { background: var(--cm-muted); color: var(--cm-primary); }
.op-btn.danger:hover { color: var(--cm-state-error); }
.op-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.matrix-scroll { overflow-x: auto; }
.menu-matrix { border-collapse: collapse; width: 100%; min-width: 900px; }
.menu-matrix th, .menu-matrix td { border-bottom: 1px solid var(--cm-border); padding: 10px 14px; text-align: center; }
.menu-matrix thead th { position: sticky; top: 0; background: var(--cm-muted); color: var(--cm-muted-foreground); font-size: 12px; font-weight: 600; white-space: nowrap; }
.col-role { text-align: left !important; min-width: 170px; }
.col-menu { min-width: 96px; }
tr.dirty .role-chip { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
tr.admin td { background: rgba(148, 163, 184, 0.06); }
.muted { color: var(--cm-muted-foreground); }
.small { font-size: 12px; }
.checkbox { display: inline-flex; align-items: center; cursor: pointer; }
.checkbox input { position: absolute; opacity: 0; pointer-events: none; }
.checkbox .box { width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid var(--cm-input); background: var(--cm-card); position: relative; transition: all .15s; }
.checkbox input:checked + .box { background: var(--cm-primary); border-color: var(--cm-primary); }
.checkbox input:checked + .box::after { content: ''; position: absolute; left: 5.5px; top: 2px; width: 4px; height: 8px; border: solid #fff; border-width: 0 2px 2px 0; transform: rotate(45deg); }
.checkbox.disabled { cursor: not-allowed; }
.checkbox.disabled .box { background: var(--cm-muted); border-color: var(--cm-input); }
.checkbox.disabled input:checked + .box::after { border-color: var(--cm-muted-foreground); }
.foot-tip { display: flex; align-items: center; gap: 6px; padding: 12px 16px; font-size: 12px; color: var(--cm-muted-foreground); margin: 0; }
</style>