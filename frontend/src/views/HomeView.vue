<template>
  <div class="min-h-screen bg-[var(--bg)]">
    <!-- Navbar -->
    <nav class="sticky top-0 z-40 bg-[var(--bg-glass)] backdrop-blur-md border-b border-[var(--border)] px-6 py-3 flex justify-between items-center">
      <div class="flex items-center gap-2.5">
        <div class="w-7 h-7 rounded-lg bg-indigo-600/20 ring-1 ring-indigo-500/30 flex items-center justify-center shrink-0">
          <svg class="w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
          </svg>
        </div>
        <span class="font-bold text-[var(--text)] tracking-tight">OrbVis</span>
      </div>
      <div class="flex items-center gap-1">
        <router-link
          v-if="auth.isAdmin"
          to="/admin/maps"
          class="px-3 py-1.5 rounded-lg text-sm font-medium text-[var(--accent)] border border-[var(--accent)] hover:bg-[var(--accent)] hover:text-white transition-all duration-150"
        >{{ t('nav.manage') }}</router-link>
        <button @click="showSettings = true"
          class="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150">
          {{ t('nav.userSettings') }}
        </button>
        <button v-if="!auth.ssoActive" @click="auth.logout()" :title="t('auth.logout')"
          class="p-1.5 rounded-lg text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
          </svg>
        </button>
      </div>

      <UserSettingsPanel
        v-if="showSettings && auth.user"
        :user-id="auth.user.user_id"
        :user-name="auth.user.name"
        :is-self="true"
        @close="showSettings = false"
      />
    </nav>

    <main class="max-w-5xl mx-auto py-10 px-6">
      <div class="mb-8">
        <h2 class="text-2xl font-bold text-[var(--text)] tracking-tight">{{ t('home.title') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('home.subtitle') }}</p>
      </div>

      <!-- Loading -->
      <div v-if="mapsStore.loading" class="flex items-center gap-3 text-zinc-500 text-sm py-12 justify-center">
        <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
        {{ t('common.loading') }}
      </div>

      <!-- Error -->
      <div v-else-if="mapsStore.error"
        class="flex items-center gap-2 px-4 py-3 bg-red-500/8 ring-1 ring-red-500/20 rounded-xl text-red-400 text-sm">
        {{ mapsStore.error }}
      </div>

      <!-- Empty state -->
      <div v-else-if="mapsStore.maps.length === 0"
        class="flex flex-col items-center justify-center py-24 text-center">
        <div class="w-14 h-14 rounded-2xl bg-[var(--bg-input)] ring-1 ring-zinc-700 flex items-center justify-center mb-5">
          <svg class="w-7 h-7 text-zinc-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
          </svg>
        </div>
        <p class="text-zinc-300 font-semibold">{{ t('home.noMapsTitle') }}</p>
        <p class="text-zinc-600 text-sm mt-1.5">
          <router-link v-if="auth.isAdmin" to="/admin/maps"
            class="text-indigo-400 hover:text-indigo-300 transition-colors">{{ t('home.noMapsAdmin') }}</router-link>
          <span v-else>{{ t('home.noMapsUser') }}</span>
        </p>
      </div>

      <!-- Map grid -->
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <router-link
          v-for="map in mapsStore.maps"
          :key="map.name"
          :to="`/maps/${map.name}`"
          class="group relative bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] hover:ring-indigo-500/40 rounded-2xl p-5 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-indigo-900/10"
        >
          <!-- Type + rotation badges -->
          <div class="absolute top-4 right-4 flex items-center gap-1.5">
            <span v-if="map.rotation_interval > 0"
              class="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20"
              :title="t('home.rotationBadgeTitle', { n: map.rotation_interval })">
              ↻ {{ map.rotation_interval }}s
            </span>
            <span class="text-xs px-2 py-0.5 rounded-full font-medium"
              :class="map.map_type === 'worldmap'
                ? 'bg-cyan-500/10 text-cyan-400 ring-1 ring-cyan-500/20'
                : map.map_type === 'radar'
                ? 'bg-violet-500/10 text-violet-400 ring-1 ring-violet-500/20'
                : 'bg-zinc-700/60 text-zinc-500 ring-1 ring-zinc-700'">
              {{ map.map_type }}
            </span>
          </div>

          <!-- Icon -->
          <div class="w-10 h-10 rounded-xl bg-indigo-600/10 ring-1 ring-indigo-500/20 flex items-center justify-center mb-4 group-hover:bg-indigo-600/15 transition-colors">
            <svg class="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
            </svg>
          </div>

          <div class="font-semibold text-[var(--text)] group-hover:text-white transition-colors">
            {{ map.alias || map.name }}
          </div>
          <div v-if="map.alias" class="text-[11px] text-zinc-600 font-mono mt-0.5">{{ map.name }}</div>

          <div class="flex items-center gap-2 mt-3 text-xs text-zinc-600">
            <span>{{ t('common.objects', { n: map.object_count }) }}</span>
            <span class="text-zinc-800">·</span>
            <span class="font-mono truncate">{{ map.backend_id }}</span>
          </div>
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useMapsStore } from '@/stores/maps'
import UserSettingsPanel from '@/components/UserSettingsPanel.vue'

const { t } = useI18n()
const auth = useAuthStore()
const mapsStore = useMapsStore()
const showSettings = ref(false)

onMounted(() => mapsStore.fetchMaps())
</script>
