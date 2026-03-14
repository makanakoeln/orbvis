<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl w-[32rem] max-h-[85vh] flex flex-col">

        <!-- Header -->
        <div class="flex items-start justify-between px-6 pt-5 pb-4 shrink-0 border-b border-[var(--border)]">
          <div>
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('board.settingsTitle') }}</h3>
            <p class="text-xs text-zinc-500 mt-0.5 font-mono">{{ board.name }}</p>
          </div>
          <button @click="$emit('close')"
            class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Tabs -->
        <div class="flex gap-1 px-6 pt-3 shrink-0">
          <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
            class="px-3 py-1.5 rounded-md text-sm font-medium transition-all"
            :class="activeTab === tab.id
              ? 'bg-indigo-600/20 text-indigo-300'
              : 'text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)]'">
            {{ tab.label }}
          </button>
        </div>

        <!-- Tab content -->
        <div class="overflow-y-auto flex-1 px-6 py-4">

          <!-- General -->
          <div v-if="activeTab === 'general'" class="space-y-4">
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.displayName') }}</label>
              <input v-model="form.alias"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.connection') }}</label>
              <div class="relative">
                <select v-model="form.backend_id"
                  class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                  <option v-for="b in backends" :key="b.id" :value="b.id">{{ b.label || b.id }}</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.iconSize') }}</label>
                <div class="flex items-center gap-2">
                  <input v-model.number="form.icon_size" type="number" min="16" max="96" step="4"
                    class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                  <span class="text-xs text-zinc-500 shrink-0">px</span>
                </div>
              </div>
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.rotationInterval') }}</label>
                <div class="flex items-center gap-2">
                  <input v-model.number="form.rotation_interval" type="number" min="0" step="5"
                    class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                  <span class="text-xs text-zinc-500 shrink-0">{{ t('board.rotationSuffix') }}</span>
                </div>
                <p class="text-xs text-zinc-600">{{ t('board.rotationIntervalHint') }}</p>
              </div>
            </div>
            <p v-if="saveError" class="text-xs text-red-400">{{ saveError }}</p>
          </div>

          <!-- Permissions -->
          <div v-else-if="activeTab === 'permissions'">
            <div v-if="permLoading" class="flex items-center justify-center py-8 text-zinc-500 text-sm gap-2">
              <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {{ t('common.loading') }}
            </div>
            <div v-else>
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-[var(--border)]">
                    <th class="px-3 py-2.5 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.role') }}</th>
                    <th class="px-3 py-2.5 text-center text-xs font-semibold text-zinc-500 uppercase tracking-wider w-20">View</th>
                    <th class="px-3 py-2.5 text-center text-xs font-semibold text-zinc-500 uppercase tracking-wider w-20">Edit</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--border)]">
                  <tr v-for="role in permRoles" :key="role.role_id" class="hover:bg-[var(--bg-hover)]">
                    <td class="px-3 py-2.5 font-medium text-[var(--text)]">{{ role.name }}</td>
                    <td class="px-3 py-2.5 text-center">
                      <div class="flex items-center justify-center gap-1">
                        <input type="checkbox" :checked="hasPerm(role, 'view')"
                          :disabled="hasWildcard(role, 'view') || permUpdating.has(`${role.role_id}-view`)"
                          class="accent-indigo-500 w-4 h-4 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          @change="togglePerm(role, 'view')" />
                        <span v-if="hasWildcard(role, 'view')" class="text-[10px] text-zinc-600" title="Via *-Regel">*</span>
                      </div>
                    </td>
                    <td class="px-3 py-2.5 text-center">
                      <div class="flex items-center justify-center gap-1">
                        <input type="checkbox" :checked="hasPerm(role, 'edit')"
                          :disabled="hasWildcard(role, 'edit') || permUpdating.has(`${role.role_id}-edit`)"
                          class="accent-indigo-500 w-4 h-4 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          @change="togglePerm(role, 'edit')" />
                        <span v-if="hasWildcard(role, 'edit')" class="text-[10px] text-zinc-600" title="Via *-Regel">*</span>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
              <p v-if="!permRoles.length" class="text-center py-6 text-zinc-600 text-sm">{{ t('admin.noRoles') }}</p>
              <p class="text-xs text-zinc-600 mt-3 px-1">* {{ t('admin.wildcardNote') }}</p>
            </div>
          </div>

        </div>

        <!-- Footer -->
        <div class="flex items-center justify-end gap-3 px-6 py-4 shrink-0 border-t border-[var(--border)]">
          <button @click="$emit('close')"
            class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">
            {{ activeTab === 'general' ? t('common.cancel') : t('common.close') }}
          </button>
          <button v-if="activeTab === 'general'" @click="save" :disabled="saving"
            class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-white transition-all">
            {{ saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { boardsApi, connectionsApi, rolesApi } from '@/api/client'
import type { BoardRead, BackendConfig, RoleRead, PermissionRead } from '@/types/api'

const props = defineProps<{ board: BoardRead }>()
const emit = defineEmits<{ close: []; updated: [] }>()

const { t } = useI18n()
const auth = useAuthStore()

const tabs: { id: 'general' | 'permissions'; label: string }[] = [
  { id: 'general', label: t('admin.settings') },
  { id: 'permissions', label: t('admin.boardPermissions') },
]
const activeTab = ref<'general' | 'permissions'>('general')

// ── General ────────────────────────────────────────────────────────────────
const form = ref({
  alias: props.board.alias,
  backend_id: props.board.backend_id,
  icon_size: props.board.icon_size,
  rotation_interval: props.board.rotation_interval,
})
const backends = ref<BackendConfig[]>([])
const saving = ref(false)
const saveError = ref('')

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    await boardsApi.update(props.board.name, {
      alias: form.value.alias,
      backend_id: form.value.backend_id,
      icon_size: form.value.icon_size,
      rotation_interval: form.value.rotation_interval,
    }, auth.accessToken!)
    emit('updated')
    emit('close')
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    saving.value = false
  }
}

// ── Permissions ────────────────────────────────────────────────────────────
const permRoles = ref<RoleRead[]>([])
const permLoading = ref(false)
const permUpdating = reactive(new Set<string>())

async function loadPermissions() {
  permLoading.value = true
  try {
    permRoles.value = await rolesApi.list(auth.accessToken!)
  } finally {
    permLoading.value = false
  }
}

function hasWildcard(role: RoleRead, act: string): boolean {
  return role.permissions.some(p => p.mod === 'map' && p.act === act && p.obj === '*')
}

function hasDirectPerm(role: RoleRead, act: string): boolean {
  return role.permissions.some(p => p.mod === 'map' && p.act === act && p.obj === props.board.name)
}

function hasPerm(role: RoleRead, act: string): boolean {
  return hasDirectPerm(role, act) || hasWildcard(role, act)
}

async function togglePerm(role: RoleRead, act: string) {
  if (hasWildcard(role, act)) return
  const key = `${role.role_id}-${act}`
  permUpdating.add(key)
  try {
    if (hasDirectPerm(role, act)) {
      const perm = role.permissions.find(p => p.mod === 'map' && p.act === act && p.obj === props.board.name)!
      await rolesApi.removePermission(role.role_id, perm.perm_id, auth.accessToken!)
    } else {
      let existingPerm: PermissionRead | null = null
      for (const r of permRoles.value) {
        const p = r.permissions.find(p => p.mod === 'map' && p.act === act && p.obj === props.board.name)
        if (p) { existingPerm = p; break }
      }
      if (!existingPerm) {
        existingPerm = await rolesApi.createPermission('map', act, props.board.name, auth.accessToken!)
      }
      await rolesApi.assignPermission(role.role_id, existingPerm.perm_id, auth.accessToken!)
    }
    permRoles.value = await rolesApi.list(auth.accessToken!)
  } finally {
    permUpdating.delete(key)
  }
}

onMounted(async () => {
  const [bs] = await Promise.all([
    connectionsApi.list(auth.accessToken!),
    loadPermissions(),
  ])
  backends.value = bs
})
</script>
