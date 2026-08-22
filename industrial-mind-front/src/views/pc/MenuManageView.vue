<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Pencil, Trash2, ListTree } from 'lucide-vue-next'
import { getMenuDefs, createMenuDef, updateMenuDef, deleteMenuDef } from '@/api'

interface MenuDef {
  code: string
  name: string
  path: string
  parent_code: string
  icon: string
  sort_order: number
  admin_only: boolean
  is_builtin: boolean
  children?: MenuDef[]
}

const loading = ref(false)
const defs = ref<MenuDef[]>([])
const dialogVisible = ref(false)
const editing = ref<MenuDef | null>(null)
const form = ref({ code: '', name: '', path: '', parent_code: '', icon: '', sort_order: 0, admin_only: false })

/** 扁平列表，附带层级深度，便于表格展示缩进 */
const flat = computed(() => {
  const rows: { def: MenuDef; depth: number }[] = []
  const walk = (nodes: MenuDef[], depth: number) => {
    for (const n of nodes) {
      rows.push({ def: n, depth })
      walk(n.children ?? [], depth + 1)
    }
  }
  walk(tree.value, 0)
  return rows
})

/** 由 parent_code 组装菜单树 */
const tree = computed(() => {
  const byCode = new Map<string, MenuDef>()
  for (const d of defs.value) byCode.set(d.code, { ...d, children: [] })
  const roots: MenuDef[] = []
  for (const d of defs.value) {
    const node = byCode.get(d.code)!
    const parent = d.parent_code ? byCode.get(d.parent_code) : undefined
    if (parent && parent !== node) parent.children!.push(node)
    else roots.push(node)
  }
  const sort = (nodes: MenuDef[]) => {
    nodes.sort((a, b) => a.sort_order - b.sort_order || a.code.localeCompare(b.code))
    for (const n of nodes) sort(n.children ?? [])
  }
  sort(roots)
  return roots
})

/** 父菜单下拉选项（含“无”顶级项；编辑时排除自身及自身后代，防止成环） */
const parentOptions = computed(() => {
  const opts: { code: string; name: string }[] = [{ code: '', name: '无（顶级菜单）' }]
  const self = editing.value?.code ?? ''
  const walk = (nodes: MenuDef[], depth: number) => {
    for (const n of nodes) {
      if (n.code === self) continue
      opts.push({ code: n.code, name: `${'　'.repeat(depth)}${n.name}` })
      walk(n.children ?? [], depth + 1)
    }
  }
  walk(tree.value, 0)
  return opts
})

async function load() {
  loading.value = true
  try {
    defs.value = (await getMenuDefs()) ?? []
  } catch (e: any) { ElMessage.error(e.message) } finally { loading.value = false }
}

function openAdd(parentCode = '') {
  editing.value = null
  form.value = { code: '', name: '', path: '', parent_code: parentCode, icon: '', sort_order: 0, admin_only: false }
  dialogVisible.value = true
}

function openEdit(d: MenuDef) {
  editing.value = d
  form.value = {
    code: d.code, name: d.name, path: d.path, parent_code: d.parent_code,
    icon: d.icon, sort_order: d.sort_order, admin_only: d.admin_only,
  }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.code.trim()) { ElMessage.warning('请填写菜单编码'); return }
  if (!form.value.name.trim()) { ElMessage.warning('请填写菜单名称'); return }
  if (!form.value.parent_code && !form.value.path.trim()) { ElMessage.warning('顶级菜单需要填写路由路径（分组菜单可留空）'); return }
  try {
    if (editing.value) {
      await updateMenuDef(editing.value.code, form.value)
      ElMessage.success('菜单已更新')
    } else {
      await createMenuDef(form.value)
      ElMessage.success('菜单已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function onDelete(d: MenuDef) {
  try {
    await ElMessageBox.confirm(`确认删除菜单「${d.name}」（${d.code}）？删除后该角色配置一并失效。`, '删除菜单', { type: 'warning' })
    await deleteMenuDef(d.code)
    ElMessage.success('已删除')
    load()
  } catch { /* cancel */ }
}

onMounted(load)
</script>

<template>
  <div class="menu-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">菜单管理</h1>
        <p class="page-sub">维护系统导航菜单定义（层级/图标/排序/是否仅管理员可见），角色在「角色管理」中按编码勾选可见菜单，登录后按角色配置动态渲染。</p>
      </div>
      <div class="head-right">
        <button class="btn primary" @click="openAdd()"><Plus :size="15" /> 新增顶级菜单</button>
      </div>
    </section>

    <section class="card">
      <el-table :data="flat" style="width: 100%" stripe>
        <el-table-column label="菜单名称" min-width="220">
          <template #default="{ row }">
            <span :style="{ paddingLeft: row.depth * 24 + 'px' }">
              <span v-if="row.depth" class="tree-line">└─ </span>
              {{ row.def.name }}
            </span>
            <span v-if="row.def.is_builtin" class="tag tag-warning">内置</span>
            <span v-if="row.def.admin_only" class="tag tag-admin">仅管理员</span>
          </template>
        </el-table-column>
        <el-table-column label="编码" prop="def.code" min-width="140" />
        <el-table-column label="路由路径" min-width="170">
          <template #default="{ row }">
            <span :class="{ muted: !row.def.path }">{{ row.def.path || '—（分组）' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="图标" prop="def.icon" min-width="110" />
        <el-table-column label="排序" prop="def.sort_order" width="70" align="center" />
        <el-table-column label="操作" width="170" align="center">
          <template #default="{ row }">
            <button class="op-btn" @click="openEdit(row.def)"><Pencil :size="14" /> 编辑</button>
            <button class="op-btn" @click="openAdd(row.def.code)"><Plus :size="14" /> 加子项</button>
            <button class="op-btn danger" :disabled="row.def.is_builtin" @click="onDelete(row.def)"><Trash2 :size="14" /> 删除</button>
          </template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!flat.length">暂无菜单定义</p>
      <p class="foot-tip"><ListTree :size="14" /> 内置菜单不可删除；删除菜单会同时清理该菜单在角色配置中的勾选。</p>
    </section>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑菜单' : '新增菜单'" width="480px">
      <el-form label-width="90px">
        <el-form-item label="菜单编码">
          <el-input v-model="form.code" :disabled="!!editing" placeholder="如 cost-custom（唯一，角色配置关联键）" />
        </el-form-item>
        <el-form-item label="菜单名称">
          <el-input v-model="form.name" placeholder="如 自定义菜单" />
        </el-form-item>
        <el-form-item label="父菜单">
          <el-select v-model="form.parent_code" style="width: 100%">
            <el-option v-for="o in parentOptions" :key="o.code" :label="o.name" :value="o.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="路由路径">
          <el-input v-model="form.path" placeholder="如 /pc/cost-custom（分组菜单可留空）" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="lucide 图标名，如 Settings / Boxes" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :max="999" style="width: 100%" />
        </el-form-item>
        <el-form-item label="仅管理员">
          <el-switch v-model="form.admin_only" />
          <span class="muted small" style="margin-left: 8px">开启后仅系统管理员可见（如系统设置下的管理菜单）</span>
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
.menu-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); max-width: 720px; }
.head-right { display: flex; gap: 10px; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
.op-btn { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--cm-slate-600); cursor: pointer; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; }
.op-btn:hover { background: var(--cm-muted); color: var(--cm-primary); }
.op-btn.danger:hover { color: var(--cm-state-error); }
.op-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.tag { display: inline-flex; align-items: center; padding: 2px 8px; margin-left: 8px; font-size: 11px; font-weight: 500; border-radius: 4px; }
.tag-warning { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
.tag-admin { background: var(--cm-primary-50); color: var(--cm-primary); }
.tree-line { color: var(--cm-slate-400); font-size: 12px; }
.muted { color: var(--cm-muted-foreground); }
.small { font-size: 12px; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
.foot-tip { display: flex; align-items: center; gap: 6px; padding: 12px 16px; font-size: 12px; color: var(--cm-muted-foreground); margin: 0; }
</style>
