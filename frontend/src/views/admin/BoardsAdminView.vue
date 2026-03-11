<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('admin.boards') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('admin.boardsSubtitle') }}</p>
      </div>
      <div class="flex items-center gap-2">
        <!-- Import -->
        <label class="flex items-center gap-2 px-4 py-2 bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] rounded-lg text-sm font-semibold text-zinc-300 transition-all cursor-pointer">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          {{ t('admin.importBoard') }}
          <input type="file" accept=".json,application/json" class="hidden" @change="importBoard" />
        </label>
        <button @click="showCreate = true"
          class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          {{ t('admin.newBoard') }}
        </button>
      </div>
    </div>

    <div v-if="boardsStore.loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--border)]">
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.name') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.alias2') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.type') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.connections') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.objectsHeader') }}</th>
            <th class="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--border)]">
          <tr v-for="map in boardsStore.boards" :key="map.name"
            class="hover:bg-[var(--bg-hover)] transition-colors">
            <td class="px-4 py-3">
              <router-link :to="`/boards/${map.name}`"
                class="font-medium text-indigo-400 hover:text-indigo-300 transition-colors font-mono text-xs">
                {{ map.name }}
              </router-link>
            </td>
            <td class="px-4 py-3 text-zinc-400">
              {{ map.alias || '—' }}
              <span v-if="map.readonly"
                class="ml-2 inline-flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded-full bg-zinc-700/50 text-zinc-500 ring-1 ring-zinc-700">
                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
                </svg>
                read-only
              </span>
            </td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium ring-1"
                :class="map.map_type === 'worldmap'
                  ? 'bg-cyan-500/10 text-cyan-400 ring-cyan-500/20'
                  : map.map_type === 'automap'
                  ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20'
                  : map.map_type === 'radar'
                  ? 'bg-violet-500/10 text-violet-400 ring-violet-500/20'
                  : 'bg-zinc-700/50 text-zinc-500 ring-zinc-700'">
                {{ { static: t('board.boardTypeStatic'), worldmap: t('board.boardTypeGeoBoard'), automap: t('board.boardTypeFlowBoard'), radar: t('board.boardTypeRadar') }[map.map_type] ?? map.map_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-zinc-500 font-mono text-xs">{{ map.backend_id }}</td>
            <td class="px-4 py-3 text-zinc-500">{{ map.object_count }}</td>
            <td class="px-4 py-3 text-right flex items-center justify-end gap-3">
              <!-- Permissions (not for readonly) -->
              <button v-if="!map.readonly" @click="openPermissions(map.name)"
                class="text-zinc-500 hover:text-indigo-400 transition-colors"
                :title="t('admin.boardPermissions')">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              </button>
              <!-- Export -->
              <button @click="exportBoard(map.name)"
                class="text-zinc-500 hover:text-emerald-400 transition-colors"
                :title="t('admin.exportBoard')">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
              </button>
              <!-- Clone -->
              <button @click="cloneBoard(map.name)"
                class="text-zinc-500 hover:text-amber-400 transition-colors"
                :title="t('admin.cloneBoard')">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                </svg>
              </button>
              <!-- Delete -->
              <button @click="deleteBoard(map.name)"
                class="text-xs text-zinc-600 hover:text-red-400 transition-colors">{{ t('common.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!boardsStore.boards.length" class="text-center py-12 text-zinc-600 text-sm">
        {{ t('admin.noBoards') }}
      </div>
    </div>

    <CreateBoardModal v-if="showCreate" @close="showCreate = false" @created="showCreate = false" />

    <!-- Board Permissions Modal -->
    <Teleport to="body">
      <div v-if="permissionsMapName" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="permissionsMapName = null" />
        <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-[34rem] max-h-[80vh] flex flex-col">
          <div class="flex items-center justify-between mb-5 shrink-0">
            <div>
              <h3 class="text-base font-bold text-[var(--text)]">{{ t('admin.boardPermissions') }}</h3>
              <p class="text-xs text-zinc-500 mt-0.5 font-mono">{{ permissionsMapName }}</p>
            </div>
            <button @click="permissionsMapName = null"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <div v-if="permissionsLoading" class="flex items-center justify-center py-8 text-zinc-500 text-sm gap-2">
            <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            {{ t('common.loading') }}
          </div>

          <div v-else class="overflow-y-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-[var(--border)]">
                  <th class="px-3 py-2.5 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.role') }}</th>
                  <th class="px-3 py-2.5 text-center text-xs font-semibold text-zinc-500 uppercase tracking-wider w-20">View</th>
                  <th class="px-3 py-2.5 text-center text-xs font-semibold text-zinc-500 uppercase tracking-wider w-20">Edit</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--border)]">
                <tr v-for="role in permissionsRoles" :key="role.role_id" class="hover:bg-[var(--bg-hover)]">
                  <td class="px-3 py-2.5 font-medium text-[var(--text)]">
                    {{ role.name }}
                  </td>
                  <td class="px-3 py-2.5 text-center">
                    <div class="flex items-center justify-center gap-1">
                      <input
                        type="checkbox"
                        :checked="hasPerm(role, 'view')"
                        :disabled="hasWildcard(role, 'view') || permUpdating.has(`${role.role_id}-view`)"
                        class="accent-indigo-500 w-4 h-4 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        @change="togglePerm(role, 'view')"
                      />
                      <span v-if="hasWildcard(role, 'view')" class="text-[10px] text-zinc-600" title="Via *-Regel">*</span>
                    </div>
                  </td>
                  <td class="px-3 py-2.5 text-center">
                    <div class="flex items-center justify-center gap-1">
                      <input
                        type="checkbox"
                        :checked="hasPerm(role, 'edit')"
                        :disabled="hasWildcard(role, 'edit') || permUpdating.has(`${role.role_id}-edit`)"
                        class="accent-indigo-500 w-4 h-4 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                        @change="togglePerm(role, 'edit')"
                      />
                      <span v-if="hasWildcard(role, 'edit')" class="text-[10px] text-zinc-600" title="Via *-Regel">*</span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
            <p v-if="!permissionsRoles.length" class="text-center py-6 text-zinc-600 text-sm">
              {{ t('admin.noRoles') }}
            </p>
            <p class="text-xs text-zinc-600 mt-3 px-1">* {{ t('admin.wildcardNote') }}</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBoardsStore } from '@/stores/boards'
import { useAuthStore } from '@/stores/auth'
import { boardsApi, rolesApi } from '@/api/client'
import type { BoardConfig, RoleRead, PermissionRead } from '@/types/api'
import CreateBoardModal from '@/components/board/CreateBoardModal.vue'

const { t } = useI18n()
const boardsStore = useBoardsStore()
const authStore = useAuthStore()
const showCreate = ref(false)

async function deleteBoard(name: string) {
  if (!confirm(t('admin.deleteBoard', { name }))) return
  await boardsStore.deleteBoard(name)
}

async function cloneBoard(name: string) {
  const newName = prompt(t('admin.cloneBoardPrompt', { name }), `${name}_copy`)
  if (!newName) return
  try {
    await boardsApi.clone(name, { new_name: newName }, authStore.accessToken!)
    await boardsStore.fetchBoards()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : t('admin.cloneFailed'))
  }
}

async function exportBoard(name: string) {
  await boardsApi.exportBoard(name, authStore.accessToken!)
}

async function importBoard(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const data: BoardConfig = JSON.parse(text)
    const overwrite = false
    try {
      await boardsApi.importBoard(data, authStore.accessToken!, overwrite)
    } catch (e: unknown) {
      // 409 = already exists → ask to overwrite
      if (e instanceof Error && e.message.includes('already exists')) {
        if (!confirm(t('admin.importOverwrite', { name: data.name }))) return
        await boardsApi.importBoard(data, authStore.accessToken!, true)
      } else {
        throw e
      }
    }
    await boardsStore.fetchBoards()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : t('admin.importFailed'))
  } finally {
    // Reset file input so the same file can be re-imported
    ;(event.target as HTMLInputElement).value = ''
  }
}

onMounted(() => boardsStore.fetchBoards())

// ---- Map Permissions ----

const permissionsMapName = ref<string | null>(null)
const permissionsRoles = ref<RoleRead[]>([])
const permissionsLoading = ref(false)
const permUpdating = reactive(new Set<string>())

async function openPermissions(mapName: string) {
  permissionsMapName.value = mapName
  permissionsLoading.value = true
  try {
    permissionsRoles.value = await rolesApi.list(authStore.accessToken!)
  } finally {
    permissionsLoading.value = false
  }
}

function hasWildcard(role: RoleRead, act: string): boolean {
  return role.permissions.some(p => p.mod === 'map' && p.act === act && p.obj === '*')
}

function hasDirectPerm(role: RoleRead, act: string): boolean {
  return role.permissions.some(p => p.mod === 'map' && p.act === act && p.obj === permissionsMapName.value)
}

function hasPerm(role: RoleRead, act: string): boolean {
  return hasDirectPerm(role, act) || hasWildcard(role, act)
}

async function togglePerm(role: RoleRead, act: string) {
  const mapName = permissionsMapName.value
  if (!mapName || hasWildcard(role, act)) return
  const key = `${role.role_id}-${act}`
  permUpdating.add(key)
  try {
    if (hasDirectPerm(role, act)) {
      // Remove the direct permission
      const perm = role.permissions.find(p => p.mod === 'map' && p.act === act && p.obj === mapName)!
      await rolesApi.removePermission(role.role_id, perm.perm_id, authStore.accessToken!)
    } else {
      // Find existing permission across all roles, or create it
      let existingPerm: PermissionRead | null = null
      for (const r of permissionsRoles.value) {
        const p = r.permissions.find(p => p.mod === 'map' && p.act === act && p.obj === mapName)
        if (p) { existingPerm = p; break }
      }
      if (!existingPerm) {
        existingPerm = await rolesApi.createPermission('map', act, mapName, authStore.accessToken!)
      }
      await rolesApi.assignPermission(role.role_id, existingPerm.perm_id, authStore.accessToken!)
    }
    // Reload roles to reflect change
    permissionsRoles.value = await rolesApi.list(authStore.accessToken!)
  } finally {
    permUpdating.delete(key)
  }
}
</script>
