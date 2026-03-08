<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-zinc-100 tracking-tight">Roles & Permissions</h2>
        <p class="text-sm text-zinc-500 mt-1">Define access control roles</p>
      </div>
      <button @click="showCreate = true"
        class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New Role
      </button>
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      Loading…
    </div>

    <div v-else class="space-y-3">
      <div v-for="role in roles" :key="role.role_id"
        class="bg-zinc-900 ring-1 ring-white/5 rounded-xl p-5 hover:ring-white/10 transition-all">
        <div class="flex justify-between items-start gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2.5 mb-1">
              <span class="font-semibold text-zinc-100">{{ role.name }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded bg-zinc-800 ring-1 ring-zinc-700 text-zinc-500">
                {{ role.permissions.length }} permissions
              </span>
            </div>
            <div v-if="role.permissions.length" class="flex flex-wrap gap-1.5 mt-2.5">
              <span
                v-for="perm in role.permissions"
                :key="perm.perm_id"
                class="text-xs bg-zinc-800 ring-1 ring-zinc-700 rounded-md px-2 py-0.5 text-zinc-400 font-mono"
              >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span>
            </div>
            <p v-else class="text-xs text-zinc-600 mt-2">No permissions assigned</p>
          </div>
          <div class="flex items-center gap-3 shrink-0">
            <button @click="openEdit(role)"
              class="text-xs text-zinc-500 hover:text-indigo-400 transition-colors px-2 py-1">
              Edit
            </button>
            <button @click="deleteRole(role.role_id)"
              class="text-xs text-zinc-600 hover:text-red-400 transition-colors px-2 py-1">
              Delete
            </button>
          </div>
        </div>
      </div>

      <div v-if="!roles.length" class="text-center py-12 text-zinc-600 text-sm">
        No roles defined yet
      </div>
    </div>

    <!-- Create role dialog -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreate = false" />
        <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 w-80">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-zinc-100">Create Role</h3>
            <button @click="showCreate = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <form @submit.prevent="createRole" class="space-y-4">
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Role name</label>
              <input v-model="newRoleName" placeholder="e.g. operators" required
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <div class="flex gap-3 justify-end pt-2 border-t border-white/5">
              <button type="button" @click="showCreate = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all">Cancel</button>
              <button type="submit"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all">Create</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit permissions dialog -->
    <Teleport to="body">
      <div v-if="editRole" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="editRole = null" />
        <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 w-[28rem] max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-zinc-100">
              Permissions –
              <span class="text-indigo-400">{{ editRole.name }}</span>
            </h3>
            <button @click="editRole = null"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <!-- Current permissions -->
          <div class="mb-5">
            <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-2">Assigned</p>
            <div v-if="editRole.permissions.length" class="space-y-1.5">
              <div v-for="perm in editRole.permissions" :key="perm.perm_id"
                class="flex items-center justify-between gap-2 px-3 py-2 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg">
                <span class="text-xs font-mono text-zinc-300">{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span>
                <button @click="removePerm(perm.perm_id)" :disabled="permSaving"
                  class="text-zinc-600 hover:text-red-400 transition-colors shrink-0">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <p v-else class="text-xs text-zinc-600">No permissions assigned yet</p>
          </div>

          <!-- Add permission form -->
          <div class="border-t border-white/5 pt-5">
            <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3">Add Permission</p>
            <form @submit.prevent="addPerm" class="space-y-3">
              <div class="space-y-1.5">
                <label class="text-xs text-zinc-500">Preset</label>
                <select v-model="permPreset" @change="applyPreset"
                  class="w-full px-3 py-2 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 appearance-none focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                  style="background-image: url(&quot;data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23a1a1aa' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E&quot;); background-repeat: no-repeat; background-position: right 0.5rem center; background-size: 1rem; padding-right: 2rem;">
                  <option value="">— choose a preset —</option>
                  <option value="map:view:*">View all maps</option>
                  <option value="map:edit:*">Edit all maps (settings & objects)</option>
                  <option value="map:view:custom">View a specific map…</option>
                  <option value="map:edit:custom">Edit a specific map…</option>
                </select>
              </div>
              <div v-if="needsMapName" class="space-y-1">
                <label class="text-xs text-zinc-500">Map name</label>
                <input v-model="newPerm.obj" placeholder="my-map" required
                  class="w-full px-2.5 py-2 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              </div>
              <p v-if="permError" class="text-red-400 text-xs">{{ permError }}</p>
              <div class="flex justify-end">
                <button type="submit" :disabled="permSaving || !permPreset"
                  class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
                  {{ permSaving ? 'Adding…' : 'Add' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { rolesApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { RoleRead } from '@/types/api'

const auth = useAuthStore()
const roles = ref<RoleRead[]>([])
const loading = ref(false)
const showCreate = ref(false)
const newRoleName = ref('')

const editRole = ref<RoleRead | null>(null)
const newPerm = ref({ mod: '', act: '', obj: '*' })
const permSaving = ref(false)
const permError = ref('')
const permPreset = ref('')
const needsMapName = computed(() => permPreset.value.endsWith(':custom'))

function applyPreset() {
  if (!permPreset.value || permPreset.value.endsWith(':custom')) return
  const [mod, act, obj] = permPreset.value.split(':')
  newPerm.value = { mod, act, obj }
}

async function fetchRoles() {
  loading.value = true
  try {
    roles.value = await rolesApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function createRole() {
  await rolesApi.create(newRoleName.value, auth.accessToken!)
  showCreate.value = false
  newRoleName.value = ''
  await fetchRoles()
}

async function deleteRole(id: number) {
  if (!confirm('Delete this role?')) return
  await rolesApi.delete(id, auth.accessToken!)
  await fetchRoles()
}

function openEdit(role: RoleRead) {
  editRole.value = { ...role, permissions: [...role.permissions] }
  newPerm.value = { mod: '', act: '', obj: '*' }
  permPreset.value = ''
  permError.value = ''
}

async function addPerm() {
  if (!editRole.value) return
  permError.value = ''
  permSaving.value = true
  try {
    let mod = newPerm.value.mod
    let act = newPerm.value.act
    let obj = newPerm.value.obj || '*'
    if (permPreset.value && !permPreset.value.endsWith(':custom')) {
      const parts = permPreset.value.split(':')
      mod = parts[0]; act = parts[1]; obj = parts[2]
    }
    const perm = await rolesApi.createPermission(mod, act, obj, auth.accessToken!)
    const updated = await rolesApi.assignPermission(editRole.value.role_id, perm.perm_id, auth.accessToken!)
    editRole.value = updated
    const idx = roles.value.findIndex(r => r.role_id === updated.role_id)
    if (idx !== -1) roles.value[idx] = updated
    permPreset.value = ''
    newPerm.value = { mod: '', act: '', obj: '*' }
  } catch (e: unknown) {
    permError.value = e instanceof Error ? e.message : 'Failed to add permission'
  } finally {
    permSaving.value = false
  }
}

async function removePerm(permId: number) {
  if (!editRole.value) return
  permSaving.value = true
  try {
    await rolesApi.removePermission(editRole.value.role_id, permId, auth.accessToken!)
    editRole.value.permissions = editRole.value.permissions.filter(p => p.perm_id !== permId)
    // sync in list
    const idx = roles.value.findIndex(r => r.role_id === editRole.value!.role_id)
    if (idx !== -1) roles.value[idx] = { ...editRole.value }
  } finally {
    permSaving.value = false
  }
}

onMounted(fetchRoles)
</script>
