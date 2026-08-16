<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Pencil, Trash2, KeyRound, Users } from 'lucide-vue-next'
import { getUsers, getRoles, createUser, updateUser, deleteUser, resetUserPassword } from '@/api'

const ROLES = ref<string[]>([])

const loading = ref(false)
const users = ref<any[]>([])
const dialogVisible = ref(false)
const editing = ref<any | null>(null) // null=新增
const form = ref({ username: '', password: '123456', display_name: '', role: '业务经理', phone: '' })

async function load() {
  loading.value = true
  try { users.value = await getUsers() } finally { loading.value = false }
}

onMounted(async () => {
  load()
  try {
    ROLES.value = (await getRoles()).map((r: any) => r.name)
  } catch { /* 忽略 */ }
})

function openAdd() {
  editing.value = null
  form.value = { username: '', password: '123456', display_name: '', role: '业务经理', phone: '' }
  dialogVisible.value = true
}

function openEdit(u: any) {
  editing.value = u
  form.value = { username: u.username, password: '', display_name: u.display_name, role: u.role, phone: u.phone || '' }
  dialogVisible.value = true
}

async function submit() {
  if (!form.value.username.trim() || !form.value.display_name.trim()) {
    ElMessage.warning('请填写用户名和姓名'); return
  }
  try {
    if (editing.value) {
      await updateUser(editing.value.id, { display_name: form.value.display_name, role: form.value.role, phone: form.value.phone })
      ElMessage.success('用户已更新')
    } else {
      await createUser({ ...form.value, username: form.value.username.trim() })
      ElMessage.success('用户已创建')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function onReset(u: any) {
  try {
    await ElMessageBox.confirm(`确认将「${u.display_name}」的密码重置为 123456？`, '重置密码', { type: 'warning' })
    await resetUserPassword(u.id)
    ElMessage.success('密码已重置为 123456')
  } catch { /* cancel */ }
}

async function onDelete(u: any) {
  try {
    await ElMessageBox.confirm(`确认删除用户「${u.display_name}（${u.username}）」？`, '删除用户', { type: 'warning' })
    await deleteUser(u.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancel */ }
}

onMounted(load)
</script>

<template>
  <div class="user-wrap" v-loading="loading">
    <section class="page-head">
      <div class="head-left">
        <h1 class="cm-heading page-title">用户管理</h1>
        <p class="page-sub">维护系统账号与角色分配，新增用户默认密码 123456</p>
      </div>
      <div class="head-right">
        <button class="btn primary" @click="openAdd"><Plus :size="15" /> 新增用户</button>
      </div>
    </section>

    <section class="card">
      <el-table :data="users" style="width: 100%" stripe>
        <el-table-column label="用户名" prop="username" width="140">
          <template #default="{ row }">
            <span class="mono">{{ row.username }}</span>
            <span v-if="row.is_admin" class="tag tag-warning">管理员</span>
          </template>
        </el-table-column>
        <el-table-column label="姓名" prop="display_name" min-width="120" />
        <el-table-column label="角色" min-width="130">
          <template #default="{ row }">
            <span class="role-chip">{{ row.role }}</span>
          </template>
        </el-table-column>
        <el-table-column label="手机号" prop="phone" min-width="140" />
        <el-table-column label="操作" width="220" align="center">
          <template #default="{ row }">
            <button class="op-btn" @click="openEdit(row)"><Pencil :size="14" /> 编辑</button>
            <button class="op-btn" @click="onReset(row)"><KeyRound :size="14" /> 重置密码</button>
            <button class="op-btn danger" :disabled="row.is_admin" @click="onDelete(row)"><Trash2 :size="14" /> 删除</button>
          </template>
        </el-table-column>
      </el-table>
      <p class="empty-tip" v-if="!users.length">暂无用户</p>
    </section>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑用户' : '新增用户'" width="480px">
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="!!editing" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item v-if="!editing" label="密码">
          <el-input v-model="form.password" placeholder="默认 123456" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.display_name" placeholder="显示姓名" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option v-for="r in ROLES" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="可选" />
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
.user-wrap { padding: 20px 24px 28px; }
.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.page-title { margin: 0; font-size: 22px; }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--cm-muted-foreground); }
.head-right { display: flex; gap: 10px; }
.card { border: 1px solid var(--cm-border); border-radius: 12px; background: var(--cm-card); box-shadow: var(--cm-shadow-1); padding: 8px 0; }
.mono { font-family: var(--cm-font-mono); font-size: 13px; }
.tag { display: inline-flex; align-items: center; padding: 2px 8px; margin-left: 8px; font-size: 11px; font-weight: 500; border-radius: 4px; }
.tag-warning { background: var(--cm-state-warning-bg); color: var(--cm-state-warning); }
.role-chip { display: inline-block; padding: 3px 10px; border-radius: 999px; background: var(--cm-primary-50); color: var(--cm-primary); font-size: 12px; font-weight: 500; }
.op-btn { display: inline-flex; align-items: center; gap: 4px; border: none; background: none; color: var(--cm-slate-600); cursor: pointer; font-size: 12.5px; padding: 4px 6px; border-radius: 6px; }
.op-btn:hover { background: var(--cm-muted); color: var(--cm-primary); }
.op-btn.danger:hover { color: var(--cm-state-error); }
.op-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.empty-tip { text-align: center; color: var(--cm-muted-foreground); font-size: 13px; padding: 28px 0; }
.btn { display: inline-flex; align-items: center; gap: 6px; border-radius: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; cursor: pointer; border: 1px solid transparent; }
.btn.primary { background: var(--cm-primary); color: #fff; }
.btn.primary:hover { background: var(--cm-primary-700); }
</style>
