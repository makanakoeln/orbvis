<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl w-[34rem] max-h-[85vh] flex flex-col">

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

            <!-- Alias -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.displayName') }}</label>
              <input v-model="form.alias"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <!-- Connection + Icon size -->
            <div class="grid grid-cols-[1fr_7rem] gap-3">
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
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.iconSize') }}</label>
                <div class="flex items-center gap-1.5">
                  <NumberInput v-model="form.icon_size" min="12" max="96" class="w-full" />
                  <span class="text-xs text-zinc-500 shrink-0">px</span>
                </div>
              </div>
            </div>

            <!-- Rotation interval -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.rotationInterval') }}</label>
              <div class="flex items-center gap-2">
                <NumberInput v-model="form.rotation_interval" min="0" max="3600" class="w-32" />
                <span class="text-xs text-zinc-500 shrink-0">{{ t('board.rotationSuffix') }}</span>
              </div>
              <p class="text-xs text-zinc-600">{{ t('board.rotationIntervalHint') }}</p>
            </div>

            <!-- Board type -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.boardType') }}</label>
              <div class="relative">
                <select v-model="form.map_type"
                  class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                  <option value="static">{{ t('board.boardTypeStatic') }}</option>
                  <option value="worldmap">{{ t('board.boardTypeGeoBoard') }}</option>
                  <option value="automap">{{ t('board.boardTypeFlowBoard') }}</option>
                  <option value="radar">{{ t('board.boardTypeRadar') }}</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>
            </div>

            <!-- Worldmap settings -->
            <template v-if="form.map_type === 'worldmap'">
              <div class="grid grid-cols-3 gap-3">
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.latitude') }}</label>
                  <NumberInput v-model="form.worldmap_lat" step="any" :precision="10" class="w-full" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.longitude') }}</label>
                  <NumberInput v-model="form.worldmap_lng" step="any" :precision="10" class="w-full" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.zoom') }}</label>
                  <NumberInput v-model="form.worldmap_zoom" min="1" max="18" class="w-full" />
                </div>
              </div>
              <p class="text-xs text-zinc-600">{{ t('board.worldmapHint') }}</p>
            </template>

            <!-- Radar settings -->
            <template v-if="form.map_type === 'radar'">
              <div class="grid grid-cols-2 gap-3">
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.filterType') }}</label>
                  <div class="relative">
                    <select v-model="form.radar_filter"
                      class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                      <option value="hostgroup">{{ t('board.filterTypeHostgroup') }}</option>
                      <option value="servicegroup">{{ t('board.filterTypeServicegroup') }}</option>
                      <option value="all_hosts">{{ t('board.filterTypeAllHosts') }}</option>
                      <option value="all_services">{{ t('board.filterTypeAllServices') }}</option>
                    </select>
                    <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                      <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                      </svg>
                    </div>
                  </div>
                </div>
                <div v-if="form.radar_filter === 'hostgroup' || form.radar_filter === 'servicegroup'" class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.groupName') }}</label>
                  <input v-model="form.radar_filter_value" placeholder="e.g. linux-servers"
                    class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                </div>
              </div>
            </template>

            <!-- Templates -->
            <div class="space-y-1.5 pt-1 border-t border-[var(--border)]">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider block mt-2">{{ t('boardSettings.templates') }}</label>
              <label class="text-xs text-zinc-400 block mt-3">{{ t('board.hoverTemplate') }}</label>
              <input v-model="form.hover_template" :placeholder="t('board.templatePlaceholder')"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              <label class="text-xs text-zinc-400 block mt-2">{{ t('board.contextTemplate') }}</label>
              <input v-model="form.context_template" :placeholder="t('board.templatePlaceholder')"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              <p class="text-xs text-zinc-600">{{ t('board.templateHint') }}</p>
            </div>

            <!-- Background image (static only) -->
            <div v-if="form.map_type === 'static'" class="space-y-1.5 pt-1 border-t border-[var(--border)]">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider block mt-2">{{ t('board.backgroundImage') }}</label>
              <div class="flex gap-2 mt-1.5">
                <input v-model="form.background_image" placeholder="filename.png"
                  class="flex-1 px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                <label class="flex items-center px-3 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 hover:ring-zinc-500 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 cursor-pointer transition-all shrink-0">
                  {{ t('common.upload') }}
                  <input type="file" accept="image/*" class="hidden" @change="uploadBackground" />
                </label>
                <button v-if="form.background_image" type="button" @click="deleteBackground"
                  class="px-3 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 hover:ring-red-500 rounded-lg text-sm text-zinc-500 hover:text-red-400 transition-all shrink-0"
                  :title="t('board.deleteBackground')">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </button>
              </div>
              <p v-if="uploadError" class="text-red-400 text-xs">{{ uploadError }}</p>
              <p v-if="uploadOk" class="text-green-400 text-xs">{{ t('board.uploadedSuccessfully') }}</p>
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
                        <span v-if="hasWildcard(role, 'view')" class="text-[10px] text-zinc-600" :title="t('admin.viaWildcardRule')">*</span>
                      </div>
                    </td>
                    <td class="px-3 py-2.5 text-center">
                      <div class="flex items-center justify-center gap-1">
                        <input type="checkbox" :checked="hasPerm(role, 'edit')"
                          :disabled="hasWildcard(role, 'edit') || permUpdating.has(`${role.role_id}-edit`)"
                          class="accent-indigo-500 w-4 h-4 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                          @change="togglePerm(role, 'edit')" />
                        <span v-if="hasWildcard(role, 'edit')" class="text-[10px] text-zinc-600" :title="t('admin.viaWildcardRule')">*</span>
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
import { ref, reactive, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { boardsApi, connectionsApi, rolesApi } from '@/api/client'
import type { BoardRead, BackendConfig, RoleRead, PermissionRead, WorldmapView, RadarView } from '@/types/api'
import NumberInput from '@/components/NumberInput.vue'

const props = defineProps<{
  board: BoardRead
  worldmapView?: { lat: number; lng: number; zoom: number } | null
}>()
const emit = defineEmits<{ close: []; updated: [] }>()

const { t } = useI18n()
const auth = useAuthStore()

const tabs: { id: 'general' | 'permissions'; label: string }[] = [
  { id: 'general', label: t('admin.settings') },
  { id: 'permissions', label: t('admin.boardPermissions') },
]
const activeTab = ref<'general' | 'permissions'>('general')

// ── General ────────────────────────────────────────────────────────────────

function initWorldmapCoords() {
  if (props.worldmapView) {
    return { lat: props.worldmapView.lat, lng: props.worldmapView.lng, zoom: props.worldmapView.zoom }
  }
  if (props.board.view.type === 'worldmap') {
    const wv = props.board.view as WorldmapView
    return { lat: wv.lat, lng: wv.lng, zoom: wv.zoom }
  }
  return { lat: 51.0, lng: 10.0, zoom: 5 }
}

const wm = initWorldmapCoords()
const rv = props.board.view.type === 'radar' ? props.board.view as RadarView : null

const form = ref({
  alias: props.board.alias,
  backend_id: props.board.backend_id,
  icon_size: props.board.icon_size,
  rotation_interval: props.board.rotation_interval,
  map_type: props.board.view.type,
  worldmap_lat: wm.lat,
  worldmap_lng: wm.lng,
  worldmap_zoom: wm.zoom,
  radar_filter: rv?.filter ?? 'hostgroup',
  radar_filter_value: rv?.filter_value ?? '',
  hover_template: props.board.hover_template ?? '',
  context_template: props.board.context_template ?? '',
  background_image: props.board.background_image ?? '',
})

const backends = ref<BackendConfig[]>([])
const saving = ref(false)
const saveError = ref('')
const uploadError = ref('')
const uploadOk = ref(false)

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    let view: Record<string, unknown>
    if (form.value.map_type === 'worldmap') {
      view = { type: 'worldmap', lat: form.value.worldmap_lat, lng: form.value.worldmap_lng, zoom: form.value.worldmap_zoom }
    } else if (form.value.map_type === 'radar') {
      view = { type: 'radar', filter: form.value.radar_filter, filter_value: form.value.radar_filter_value }
    } else {
      view = { type: form.value.map_type }
    }
    await boardsApi.update(props.board.name, {
      alias: form.value.alias,
      backend_id: form.value.backend_id,
      icon_size: form.value.icon_size,
      rotation_interval: form.value.rotation_interval,
      background_image: form.value.background_image || null,
      view,
      hover_template: form.value.hover_template || null,
      context_template: form.value.context_template || null,
    }, auth.accessToken!)
    emit('updated')
    emit('close')
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'An error occurred'
  } finally {
    saving.value = false
  }
}

async function uploadBackground(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploadError.value = ''
  uploadOk.value = false
  try {
    const result = await boardsApi.uploadBackground(props.board.name, file, auth.accessToken!)
    form.value.background_image = result.filename
    uploadOk.value = true
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
  }
}

async function deleteBackground() {
  uploadError.value = ''
  try {
    await boardsApi.deleteBackground(props.board.name, auth.accessToken!)
    form.value.background_image = ''
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Delete failed'
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
  // Re-apply backend_id after options are rendered (browser may reset select with no options)
  await nextTick()
  const saved = form.value.backend_id
  form.value.backend_id = ''
  await nextTick()
  form.value.backend_id = saved
})
</script>
