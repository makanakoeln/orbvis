<template>
  <div class="flex-1 overflow-y-auto bg-[var(--bg)]">
    <main class="max-w-5xl mx-auto py-10 px-6">
      <div class="mb-8 flex items-end justify-between gap-4">
        <div>
          <h2 class="text-2xl font-bold text-[var(--text)] tracking-tight">{{ t('home.title') }}</h2>
          <p class="text-sm text-zinc-500 mt-1">{{ t('home.subtitle') }}</p>
        </div>
        <div class="relative w-56 shrink-0">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input v-model="searchQuery"
            :placeholder="t('home.search')"
            class="w-full pl-8 pr-3 py-2 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
        </div>
      </div>

      <!-- Loading -->
      <div v-if="boardsStore.loading" class="flex items-center gap-3 text-zinc-500 text-sm py-12 justify-center">
        <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        {{ t('common.loading') }}
      </div>

      <!-- Error -->
      <div v-else-if="boardsStore.error"
        class="flex items-center gap-2 px-4 py-3 bg-red-500/8 ring-1 ring-red-500/20 rounded-xl text-red-400 text-sm">
        {{ boardsStore.error }}
      </div>

      <!-- Empty state -->
      <div v-else-if="boardsStore.boards.length === 0"
        class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-14 h-14 rounded-2xl bg-[var(--bg-input)] ring-1 ring-zinc-700 flex items-center justify-center mb-5">
          <svg class="w-7 h-7 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
          </svg>
        </div>
        <p class="text-zinc-300 font-semibold">{{ t('home.noBoardsTitle') }}</p>
        <p class="text-zinc-600 text-sm mt-1.5">
          <router-link v-if="auth.isAdmin" to="/admin/boards"
            class="text-indigo-400 hover:text-indigo-300 transition-colors">{{ t('home.noBoardsAdmin') }}</router-link>
          <span v-else>{{ t('home.noBoardsUser') }}</span>
        </p>
      </div>

      <!-- Board grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <p v-if="searchQuery && !filteredBoards.length" class="col-span-full text-center py-12 text-zinc-600 text-sm">
          {{ t('home.noSearchResults', { q: searchQuery }) }}
        </p>
        <div
          v-for="map in filteredBoards"
          :key="map.name"
          class="group relative bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] hover:ring-indigo-500/40 rounded-2xl overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-900/10"
        >
          <router-link :to="`/boards/${map.name}`" class="block">
          <!-- Thumbnail -->
          <div class="relative w-full h-32 overflow-hidden bg-[var(--bg-input)]">
            <img
              v-if="map.background_image"
              :src="`${baseUrl}boards/backgrounds/${map.background_image}`"
              :alt="map.alias || map.name"
              class="w-full h-full object-cover opacity-70 group-hover:opacity-90 transition-opacity duration-200"
            />
            <!-- Worldmap thumbnail -->
            <WorldMapThumbnail
              v-else-if="map.map_type === 'worldmap'"
              :lat="map.worldmap_lat ?? 51"
              :lng="map.worldmap_lng ?? 10"
              :zoom="map.worldmap_zoom ?? 5"
              class="opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none"
            />
            <!-- Flow Board thumbnail -->
            <svg v-else-if="map.map_type === 'automap'" viewBox="0 0 256 128"
              class="w-full h-full opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none">
              <rect width="256" height="128" fill="#18181b"/>
              <line x1="128" y1="28" x2="72" y2="66" stroke="#3f3f46" stroke-width="1.5"/>
              <line x1="128" y1="28" x2="184" y2="66" stroke="#3f3f46" stroke-width="1.5"/>
              <line x1="72" y1="66" x2="36" y2="100" stroke="#3f3f46" stroke-width="1.5"/>
              <line x1="72" y1="66" x2="108" y2="100" stroke="#3f3f46" stroke-width="1.5"/>
              <line x1="184" y1="66" x2="148" y2="100" stroke="#3f3f46" stroke-width="1.5"/>
              <line x1="184" y1="66" x2="220" y2="100" stroke="#3f3f46" stroke-width="1.5"/>
              <circle cx="128" cy="28" r="11" fill="#22c55e"/>
              <circle cx="72" cy="66" r="9" fill="#22c55e"/>
              <circle cx="184" cy="66" r="9" fill="#ef4444"/>
              <circle cx="36" cy="100" r="7" fill="#22c55e"/>
              <circle cx="108" cy="100" r="7" fill="#f59e0b"/>
              <circle cx="148" cy="100" r="7" fill="#22c55e"/>
              <circle cx="220" cy="100" r="7" fill="#22c55e"/>
              <text x="128" y="32" text-anchor="middle" dominant-baseline="central" fill="rgba(255,255,255,0.9)" font-size="8" font-weight="700">H</text>
              <text x="72" y="70" text-anchor="middle" dominant-baseline="central" fill="rgba(255,255,255,0.9)" font-size="7" font-weight="700">H</text>
              <text x="184" y="70" text-anchor="middle" dominant-baseline="central" fill="rgba(255,255,255,0.9)" font-size="7" font-weight="700">H</text>
            </svg>
            <!-- Radar Board thumbnail — status card grid -->
            <svg v-else-if="map.map_type === 'radar'" viewBox="0 0 256 128"
              class="w-full h-full opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none">
              <rect width="256" height="128" fill="#18181b"/>
              <!-- OK cards -->
              <rect x="10" y="10" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="17" cy="21" r="2.5" fill="#22c55e"/><rect x="23" y="18.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="13" y="30" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="17.5" cy="33.5" r="1.5" fill="#22c55e"/>
              <rect x="70" y="10" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="77" cy="21" r="2.5" fill="#22c55e"/><rect x="83" y="18.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="73" y="30" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="77.5" cy="33.5" r="1.5" fill="#22c55e"/>
              <rect x="190" y="10" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="197" cy="21" r="2.5" fill="#22c55e"/><rect x="203" y="18.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="193" y="30" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="197.5" cy="33.5" r="1.5" fill="#22c55e"/>
              <rect x="10" y="48" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="17" cy="59" r="2.5" fill="#22c55e"/><rect x="23" y="56.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="13" y="68" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="17.5" cy="71.5" r="1.5" fill="#22c55e"/>
              <rect x="130" y="48" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="137" cy="59" r="2.5" fill="#22c55e"/><rect x="143" y="56.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="133" y="68" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="137.5" cy="71.5" r="1.5" fill="#22c55e"/>
              <rect x="190" y="48" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="197" cy="59" r="2.5" fill="#22c55e"/><rect x="203" y="56.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="193" y="68" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="197.5" cy="71.5" r="1.5" fill="#22c55e"/>
              <rect x="70" y="86" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="77" cy="97" r="2.5" fill="#22c55e"/><rect x="83" y="94.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="73" y="106" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="77.5" cy="109.5" r="1.5" fill="#22c55e"/>
              <rect x="130" y="86" width="56" height="34" rx="4" fill="rgba(34,197,94,0.07)" stroke="rgba(34,197,94,0.22)" stroke-width="0.75"/>
              <circle cx="137" cy="97" r="2.5" fill="#22c55e"/><rect x="143" y="94.5" width="30" height="3.5" rx="1.5" fill="rgba(134,239,172,0.3)"/>
              <rect x="133" y="106" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)"/><circle cx="137.5" cy="109.5" r="1.5" fill="#22c55e"/>
              <!-- CRITICAL cards -->
              <rect x="130" y="10" width="56" height="34" rx="4" fill="rgba(239,68,68,0.07)" stroke="rgba(239,68,68,0.22)" stroke-width="0.75"/>
              <circle cx="137" cy="21" r="2.5" fill="#ef4444"/><rect x="143" y="18.5" width="30" height="3.5" rx="1.5" fill="rgba(252,165,165,0.3)"/>
              <rect x="133" y="30" width="32" height="7" rx="2" fill="rgba(239,68,68,0.12)"/><circle cx="137.5" cy="33.5" r="1.5" fill="#ef4444"/>
              <rect x="10" y="86" width="56" height="34" rx="4" fill="rgba(239,68,68,0.07)" stroke="rgba(239,68,68,0.22)" stroke-width="0.75"/>
              <circle cx="17" cy="97" r="2.5" fill="#ef4444"/><rect x="23" y="94.5" width="30" height="3.5" rx="1.5" fill="rgba(252,165,165,0.3)"/>
              <rect x="13" y="106" width="32" height="7" rx="2" fill="rgba(239,68,68,0.12)"/><circle cx="17.5" cy="109.5" r="1.5" fill="#ef4444"/>
              <!-- WARNING cards -->
              <rect x="70" y="48" width="56" height="34" rx="4" fill="rgba(234,179,8,0.07)" stroke="rgba(234,179,8,0.22)" stroke-width="0.75"/>
              <circle cx="77" cy="59" r="2.5" fill="#eab308"/><rect x="83" y="56.5" width="30" height="3.5" rx="1.5" fill="rgba(253,224,71,0.3)"/>
              <rect x="73" y="68" width="32" height="7" rx="2" fill="rgba(234,179,8,0.12)"/><circle cx="77.5" cy="71.5" r="1.5" fill="#eab308"/>
              <rect x="190" y="86" width="56" height="34" rx="4" fill="rgba(234,179,8,0.07)" stroke="rgba(234,179,8,0.22)" stroke-width="0.75"/>
              <circle cx="197" cy="97" r="2.5" fill="#eab308"/><rect x="203" y="94.5" width="30" height="3.5" rx="1.5" fill="rgba(253,224,71,0.3)"/>
              <rect x="193" y="106" width="32" height="7" rx="2" fill="rgba(234,179,8,0.12)"/><circle cx="197.5" cy="109.5" r="1.5" fill="#eab308"/>
            </svg>
            <!-- Placeholder for static without background -->
            <div v-else class="w-full h-full flex items-center justify-center">
              <svg class="w-10 h-10 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
              </svg>
            </div>
            <!-- Type + rotation badges overlaid on thumbnail -->
            <div class="absolute top-2 right-2 flex items-center gap-1.5">
              <span v-if="map.rotation_interval > 0"
                class="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30 backdrop-blur-sm"
                :title="t('home.rotationBadgeTitle', { n: map.rotation_interval })">
                ↻ {{ map.rotation_interval }}s
              </span>
              <span class="text-xs px-2 py-0.5 rounded-full font-medium backdrop-blur-sm"
                :class="map.map_type === 'worldmap'
                  ? 'bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/30'
                  : map.map_type === 'radar'
                  ? 'bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30'
                  : map.map_type === 'automap'
                  ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/30'
                  : 'bg-zinc-800/70 text-zinc-400 ring-1 ring-zinc-700/60'">
                {{ boardTypeLabel(map.map_type) }}
              </span>
            </div>
          </div>

          <!-- Card body -->
          <div class="p-4">
            <div class="font-semibold text-[var(--text)] group-hover:text-white transition-colors truncate">
              {{ map.alias || map.name }}
            </div>
            <div v-if="map.alias" class="text-[11px] text-zinc-600 font-mono mt-0.5 truncate">{{ map.name }}</div>

            <div class="flex items-center justify-between mt-2">
              <div class="flex items-center gap-2 text-xs text-zinc-600">
                <span>{{ t('common.objects', { n: map.object_count }) }}</span>
                <span class="text-zinc-800">·</span>
                <span class="font-mono truncate">{{ map.backend_id }}</span>
              </div>
              <button v-if="auth.isAdmin" @click.prevent.stop="deleteBoard(map)"
                class="opacity-0 group-hover:opacity-100 p-1 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                :title="t('admin.deleteBoard', { name: map.alias || map.name })">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                </svg>
              </button>
            </div>
          </div>
          </router-link>
        </div>
      </div>
    </main>
  </div>
  <!-- FAB: create board (admin only) -->
  <button v-if="auth.isAdmin" @click="showCreate = true"
    class="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-900/40 flex items-center justify-center text-white transition-all hover:scale-105 active:scale-95"
    :title="t('admin.newBoard')">
    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  </button>
  <CreateBoardModal v-if="showCreate" @close="showCreate = false" @created="onCreated" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import WorldMapThumbnail from '@/components/WorldMapThumbnail.vue'
import CreateBoardModal from '@/components/board/CreateBoardModal.vue'

const { t } = useI18n()
const baseUrl = import.meta.env.BASE_URL
const auth = useAuthStore()
const boardsStore = useBoardsStore()
const router = useRouter()
const showCreate = ref(false)

function onCreated(name: string) {
  showCreate.value = false
  router.push(`/boards/${name}`)
}

async function deleteBoard(map: { name: string; alias: string }) {
  if (!confirm(t('admin.deleteBoard', { name: map.alias || map.name }))) return
  await boardsStore.deleteBoard(map.name)
}
const searchQuery = ref('')

const filteredBoards = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return boardsStore.boards
  return boardsStore.boards.filter(m =>
    m.name.toLowerCase().includes(q) || m.alias.toLowerCase().includes(q)
  )
})

const TYPE_LABELS: Record<string, string> = {
  static: 'Static',
  worldmap: 'Geo Board',
  automap: 'Flow Board',
  radar: 'Radar',
}
function boardTypeLabel(type: string) {
  return TYPE_LABELS[type] ?? type
}

onMounted(() => boardsStore.fetchBoards())
</script>
