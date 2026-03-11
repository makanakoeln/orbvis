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
        <router-link
          v-for="map in filteredBoards"
          :key="map.name"
          :to="`/boards/${map.name}`"
          class="group relative bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] hover:ring-indigo-500/40 rounded-2xl overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-900/10"
        >
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
            <!-- Placeholder when no background image -->
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

            <div class="flex items-center gap-2 mt-2 text-xs text-zinc-600">
              <span>{{ t('common.objects', { n: map.object_count }) }}</span>
              <span class="text-zinc-800">·</span>
              <span class="font-mono truncate">{{ map.backend_id }}</span>
            </div>
          </div>
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import WorldMapThumbnail from '@/components/WorldMapThumbnail.vue'

const { t } = useI18n()
const baseUrl = import.meta.env.BASE_URL
const auth = useAuthStore()
const boardsStore = useBoardsStore()
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
