<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('admin.maps') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('admin.mapsSubtitle') }}</p>
      </div>
      <button @click="showCreate = true"
        class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('admin.newMap') }}
      </button>
    </div>

    <div v-if="mapsStore.loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
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
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.backends') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.objectsHeader') }}</th>
            <th class="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--border)]">
          <tr v-for="map in mapsStore.maps" :key="map.name"
            class="hover:bg-[var(--bg-hover)] transition-colors">
            <td class="px-4 py-3">
              <router-link :to="`/maps/${map.name}`"
                class="font-medium text-indigo-400 hover:text-indigo-300 transition-colors font-mono text-xs">
                {{ map.name }}
              </router-link>
            </td>
            <td class="px-4 py-3 text-zinc-400">{{ map.alias || '—' }}</td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded-full font-medium ring-1"
                :class="map.map_type === 'worldmap'
                  ? 'bg-cyan-500/10 text-cyan-400 ring-cyan-500/20'
                  : map.map_type === 'radar'
                  ? 'bg-violet-500/10 text-violet-400 ring-violet-500/20'
                  : 'bg-zinc-700/50 text-zinc-500 ring-zinc-700'">
                {{ map.map_type }}
              </span>
            </td>
            <td class="px-4 py-3 text-zinc-500 font-mono text-xs">{{ map.backend_id }}</td>
            <td class="px-4 py-3 text-zinc-500">{{ map.object_count }}</td>
            <td class="px-4 py-3 text-right">
              <button @click="deleteMap(map.name)"
                class="text-xs text-zinc-600 hover:text-red-400 transition-colors">{{ t('common.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!mapsStore.maps.length" class="text-center py-12 text-zinc-600 text-sm">
        {{ t('admin.noMaps') }}
      </div>
    </div>

    <!-- Create map dialog -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreate = false" />
        <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-[26rem]">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('admin.createMap') }}</h3>
            <button @click="showCreate = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <form @submit.prevent="createMap" class="space-y-4">
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                {{ t('admin.mapId') }} <span class="normal-case font-normal text-zinc-600">{{ t('admin.mapIdHint') }}</span>
              </label>
              <input v-model="newMap.name" placeholder="my-map" required pattern="[a-zA-Z0-9_-]+"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('admin.alias') }}</label>
              <input v-model="newMap.alias" placeholder="My Map"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('map.backend') }}</label>
              <div class="relative">
                <select v-model="newMap.backend_id" required
                  class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                  <option value="" disabled>{{ t('admin.selectBackend') }}</option>
                  <option v-for="b in backendsStore.backends" :key="b.id" :value="b.id">
                    {{ b.label || b.id }}
                  </option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('map.mapType') }}</label>
              <div class="relative">
                <select v-model="newMap.map_type"
                  class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                  <option value="static">{{ t('map.mapTypeStatic') }}</option>
                  <option value="worldmap">{{ t('map.mapTypeWorldmap') }}</option>
                  <option value="radar">{{ t('map.mapTypeRadar') }}</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-3 flex items-center">
                  <svg class="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </div>
            </div>
            <div class="flex gap-3 justify-end pt-2 border-t border-[var(--border)]">
              <button type="button" @click="showCreate = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">{{ t('common.cancel') }}</button>
              <button type="submit"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all">{{ t('common.create') }}</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMapsStore } from '@/stores/maps'
import { useBackendsStore } from '@/stores/backends'

const { t } = useI18n()
const mapsStore = useMapsStore()
const backendsStore = useBackendsStore()
const showCreate = ref(false)
const newMap = ref({ name: '', alias: '', backend_id: '', map_type: 'static' })

async function createMap() {
  await mapsStore.createMap(newMap.value.name, newMap.value.alias, newMap.value.backend_id, newMap.value.map_type)
  showCreate.value = false
  newMap.value = { name: '', alias: '', backend_id: backendsStore.backends[0]?.id ?? '', map_type: 'static' }
}

async function deleteMap(name: string) {
  if (!confirm(t('admin.deleteMap', { name }))) return
  await mapsStore.deleteMap(name)
}

onMounted(async () => {
  await Promise.all([mapsStore.fetchMaps(), backendsStore.fetchBackends()])
  if (!newMap.value.backend_id && backendsStore.backends.length > 0) {
    newMap.value.backend_id = backendsStore.backends[0].id
  }
})
</script>
