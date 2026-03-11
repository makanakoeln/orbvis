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
          <span v-if="auth.isAdmin" class="text-indigo-400">{{ t('home.noBoardsAdmin') }}</span>
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
            </div>
          </div>

          <!-- Card body -->
          <div class="p-4">
            <div class="flex items-center gap-2 min-w-0">
              <div class="font-semibold text-[var(--text)] group-hover:text-white transition-colors truncate">
                {{ map.alias || map.name }}
              </div>
              <span class="shrink-0 text-[11px] px-1.5 py-0.5 rounded-md font-medium"
                :class="map.map_type === 'worldmap'
                  ? 'bg-cyan-500/15 text-cyan-400 ring-1 ring-cyan-500/25'
                  : map.map_type === 'radar'
                  ? 'bg-violet-500/15 text-violet-400 ring-1 ring-violet-500/25'
                  : map.map_type === 'automap'
                  ? 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/25'
                  : 'bg-zinc-700/50 text-zinc-500 ring-1 ring-zinc-700/60'">
                {{ boardTypeLabel(map.map_type) }}
              </span>
            </div>
            <div v-if="!map.name.startsWith('demo-')" class="flex items-center gap-1.5 mt-1.5 text-[11px] text-zinc-600 truncate">
              <span class="text-zinc-700 font-medium uppercase tracking-wider text-[10px]">{{ t('board.connection') }}</span>
              <span class="font-mono">{{ map.backend_id }}</span>
            </div>

            <div class="flex items-center justify-between mt-2">
              <div class="flex items-center gap-2 text-xs text-zinc-600">
                <span v-if="!map.name.startsWith('demo-')">{{ t('common.objects', { n: map.object_count }) }}</span>
              </div>
              <div v-if="auth.isAdmin" class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                <!-- Permissions -->
                <button v-if="!map.readonly" @click.prevent.stop="openPermissions(map.name)"
                  class="p-1 rounded-md text-zinc-600 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
                  :title="t('admin.boardPermissions')">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                  </svg>
                </button>
                <!-- Clone -->
                <button @click.prevent.stop="cloneBoard(map.name)"
                  class="p-1 rounded-md text-zinc-600 hover:text-amber-400 hover:bg-amber-500/10 transition-all"
                  :title="t('admin.cloneBoard')">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
                  </svg>
                </button>
                <!-- Export -->
                <button @click.prevent.stop="exportBoard(map.name)"
                  class="p-1 rounded-md text-zinc-600 hover:text-emerald-400 hover:bg-emerald-500/10 transition-all"
                  :title="t('admin.exportBoard')">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                </button>
                <!-- Delete -->
                <button @click.prevent.stop="deleteBoard(map)"
                  class="p-1 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                  :title="t('admin.deleteBoard', { name: map.alias || map.name })">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          </router-link>
        </div>
      </div>
    </main>
  </div>
  <!-- Delete confirmation -->
  <Teleport to="body">
    <div v-if="confirmDelete" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="confirmDelete = null" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-80">
        <h3 class="text-base font-bold text-[var(--text)] mb-1">{{ t('admin.deleteBoardTitle') }}</h3>
        <p class="text-sm text-zinc-400 mb-5">
          {{ t('admin.deleteBoardConfirm', { name: confirmDelete.alias || confirmDelete.name }) }}
        </p>
        <div class="flex gap-3 justify-end">
          <button @click="confirmDelete = null"
            class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">
            {{ t('common.cancel') }}
          </button>
          <button @click="doDelete"
            class="px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 hover:bg-red-500 text-white transition-all">
            {{ t('common.delete') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>

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
          <p v-if="!permissionsRoles.length" class="text-center py-6 text-zinc-600 text-sm">{{ t('admin.noRoles') }}</p>
          <p class="text-xs text-zinc-600 mt-3 px-1">* {{ t('admin.wildcardNote') }}</p>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- FABs: import + create board (admin only) -->
  <div v-if="auth.isAdmin" class="fixed bottom-6 right-6 z-40 flex items-center gap-2">
    <label
      class="w-10 h-10 rounded-full bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] shadow-lg flex items-center justify-center text-zinc-400 hover:text-zinc-200 transition-all hover:scale-105 active:scale-95 cursor-pointer"
      :title="t('admin.importBoard')">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
      <input type="file" accept=".json,application/json" class="hidden" @change="importBoard" />
    </label>
    <button @click="showCreate = true"
      class="w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-900/40 flex items-center justify-center text-white transition-all hover:scale-105 active:scale-95"
      :title="t('admin.newBoard')">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
    </button>
  </div>
  <CreateBoardModal v-if="showCreate" @close="showCreate = false" @created="onCreated" />
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import { boardsApi, rolesApi } from '@/api/client'
import type { BoardConfig, RoleRead, PermissionRead } from '@/types/api'
import WorldMapThumbnail from '@/components/WorldMapThumbnail.vue'
import CreateBoardModal from '@/components/board/CreateBoardModal.vue'

const { t } = useI18n()
const baseUrl = import.meta.env.BASE_URL
const auth = useAuthStore()
const boardsStore = useBoardsStore()
const router = useRouter()
const showCreate = ref(false)
const confirmDelete = ref<{ name: string; alias: string } | null>(null)

function onCreated(name: string) {
  showCreate.value = false
  router.push(`/boards/${name}`)
}

function deleteBoard(map: { name: string; alias: string }) {
  confirmDelete.value = map
}

async function doDelete() {
  if (!confirmDelete.value) return
  await boardsStore.deleteBoard(confirmDelete.value.name)
  confirmDelete.value = null
}

async function importBoard(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const data: BoardConfig = JSON.parse(text)
    try {
      await boardsApi.importBoard(data, auth.accessToken!, false)
    } catch (e: unknown) {
      if (e instanceof Error && e.message.includes('already exists')) {
        if (!confirm(t('admin.importOverwrite', { name: data.name }))) return
        await boardsApi.importBoard(data, auth.accessToken!, true)
      } else {
        throw e
      }
    }
    await boardsStore.fetchBoards()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : t('admin.importFailed'))
  } finally {
    ;(event.target as HTMLInputElement).value = ''
  }
}

async function exportBoard(name: string) {
  await boardsApi.exportBoard(name, auth.accessToken!)
}

async function cloneBoard(name: string) {
  const newName = prompt(t('admin.cloneBoardPrompt', { name }), `${name}_copy`)
  if (!newName) return
  try {
    await boardsApi.clone(name, { new_name: newName }, auth.accessToken!)
    await boardsStore.fetchBoards()
  } catch (e: unknown) {
    alert(e instanceof Error ? e.message : t('admin.cloneFailed'))
  }
}

// ---- Permissions ----
const permissionsMapName = ref<string | null>(null)
const permissionsRoles = ref<RoleRead[]>([])
const permissionsLoading = ref(false)
const permUpdating = reactive(new Set<string>())

async function openPermissions(mapName: string) {
  permissionsMapName.value = mapName
  permissionsLoading.value = true
  try {
    permissionsRoles.value = await rolesApi.list(auth.accessToken!)
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
      const perm = role.permissions.find(p => p.mod === 'map' && p.act === act && p.obj === mapName)!
      await rolesApi.removePermission(role.role_id, perm.perm_id, auth.accessToken!)
    } else {
      let existingPerm: PermissionRead | null = null
      for (const r of permissionsRoles.value) {
        const p = r.permissions.find(p => p.mod === 'map' && p.act === act && p.obj === mapName)
        if (p) { existingPerm = p; break }
      }
      if (!existingPerm) {
        existingPerm = await rolesApi.createPermission('map', act, mapName, auth.accessToken!)
      }
      await rolesApi.assignPermission(role.role_id, existingPerm.perm_id, auth.accessToken!)
    }
    permissionsRoles.value = await rolesApi.list(auth.accessToken!)
  } finally {
    permUpdating.delete(key)
  }
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
