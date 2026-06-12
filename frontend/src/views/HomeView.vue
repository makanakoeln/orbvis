<template>
  <div class="orb-home">
    <main class="orb-home__main">
      <div class="orb-home__toolbar">
        <h2 class="orb-home__title">
          {{ _t('Boards') }}
        </h2>
        <div class="orb-home__search">
          <svg
            class="orb-home__search-icon"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <input
            v-model="searchQuery"
            :placeholder="_t('Search boards…')"
            class="orb-home__search-input"
            :style="searchQuery ? 'padding-right: var(--dimension-8)' : ''"
          />
          <button
            v-if="searchQuery"
            class="orb-home__search-clear"
            :title="_t('Clear search')"
            @click="searchQuery = ''"
          >
            <svg
              style="width: 12px; height: 12px"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div v-if="boardsStore.boards.length > 0" class="home-view-toggle">
          <CmkToggleButtonGroup
            v-if="capabilities.formSpecs"
            :model-value="viewMode"
            :options="viewModeOptions"
            @update:model-value="setViewMode($event)"
          />
          <div
            v-else
            class="orb-home__toggle-group"
            role="group"
            :aria-label="_t('Show as card grid')"
          >
            <button
              type="button"
              class="orb-home__toggle-btn"
              :class="viewMode === 'cards' ? 'orb-home__toggle-btn--active' : ''"
              :title="_t('Show as card grid')"
              :aria-pressed="viewMode === 'cards'"
              @click="setViewMode('cards')"
            >
              <svg
                style="width: 12px; height: 12px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z"
                />
              </svg>
              {{ _t('Cards') }}
            </button>
            <button
              type="button"
              class="orb-home__toggle-btn orb-home__toggle-btn--bordered"
              :class="viewMode === 'table' ? 'orb-home__toggle-btn--active' : ''"
              :title="_t('Show as table')"
              :aria-pressed="viewMode === 'table'"
              @click="setViewMode('table')"
            >
              <svg
                style="width: 12px; height: 12px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3.75 5.25h16.5m-16.5 4.5h16.5m-16.5 4.5h16.5m-16.5 4.5h16.5"
                />
              </svg>
              {{ _t('Table') }}
            </button>
          </div>
        </div>
        <button
          v-if="auth.canCreateBoards"
          data-tour="new-board"
          class="orb-home__new-btn"
          @click="showCreate = true"
        >
          <svg
            style="width: 11px; height: 11px"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2.5"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          {{ _t('New Board') }}
        </button>
      </div>

      <!-- Loading -->
      <div v-if="boardsStore.loading" class="orb-home__loading">
        <svg class="orb-home__spinner" fill="none" viewBox="0 0 24 24">
          <circle
            class="orb-home__spinner-track"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="orb-home__spinner-head"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        {{ _t('Loading…') }}
      </div>

      <!-- Error -->
      <div v-else-if="boardsStore.error" class="orb-home__error">
        {{ boardsStore.error }}
      </div>

      <!-- Empty state -->
      <div v-else-if="boardsStore.boards.length === 0" class="orb-home__empty">
        <div class="orb-home__empty-icon">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"
            />
          </svg>
        </div>
        <p class="orb-home__empty-title">{{ _t('No boards configured') }}</p>
        <p class="orb-home__empty-hint">
          <span v-if="auth.canCreateBoards" class="orb-home__empty-cta">{{
            _t('Create your first board')
          }}</span>
          <span v-else>{{ _t('Contact your administrator') }}</span>
        </p>
      </div>

      <!-- Board grid -->
      <div v-else-if="viewMode === 'cards'" data-tour="boards-grid" class="orb-home__grid">
        <p v-if="searchQuery && !filteredBoards.length" class="orb-home__no-results">
          {{ _t('No boards match "%{q}"', { q: searchQuery }) }}
        </p>
        <div
          v-for="(map, index) in draggableBoards"
          :key="map.name"
          :class="[
            isDragEnabled ? 'orb-home__card--draggable' : '',
            dragIndex === index ? 'orb-home__card--dragging' : ''
          ]"
          class="orb-home__card"
          :draggable="isDragEnabled"
          @dragstart="onDragStart($event, index)"
          @dragover="onDragOver($event, index)"
          @drop="onDrop"
          @dragend="onDragEnd"
        >
          <router-link :to="`/boards/${map.name}`" class="orb-home__card-link">
            <!-- Thumbnail -->
            <div class="orb-home__thumb">
              <img
                v-if="
                  map.background_image && !map.name.startsWith('demo-') && !bgImageFailed[map.name]
                "
                :src="`${baseUrl}boards/backgrounds/${map.background_image}`"
                :alt="map.alias || map.name"
                class="orb-home__thumb-img"
                draggable="false"
                @error="bgImageFailed[map.name] = true"
              />
              <!-- Worldmap thumbnail -->
              <WorldMapThumbnail
                v-else-if="map.view.type === 'worldmap'"
                :lat="worldmapLat(map)"
                :lng="worldmapLng(map)"
                :zoom="worldmapZoom(map)"
                class="orb-home__thumb-media"
              />
              <!-- Flow Board thumbnail -->
              <svg
                v-else-if="map.view.type === 'flow'"
                viewBox="0 0 256 128"
                class="orb-home__thumb-media orb-home__thumb-media--fill"
              >
                <rect width="256" height="128" fill="#18181b" />
                <line x1="128" y1="28" x2="72" y2="66" stroke="#3f3f46" stroke-width="1.5" />
                <line x1="128" y1="28" x2="184" y2="66" stroke="#3f3f46" stroke-width="1.5" />
                <line x1="72" y1="66" x2="36" y2="100" stroke="#3f3f46" stroke-width="1.5" />
                <line x1="72" y1="66" x2="108" y2="100" stroke="#3f3f46" stroke-width="1.5" />
                <line x1="184" y1="66" x2="148" y2="100" stroke="#3f3f46" stroke-width="1.5" />
                <line x1="184" y1="66" x2="220" y2="100" stroke="#3f3f46" stroke-width="1.5" />
                <circle cx="128" cy="28" r="11" fill="#22c55e" />
                <circle cx="72" cy="66" r="9" fill="#22c55e" />
                <circle cx="184" cy="66" r="9" fill="#ef4444" />
                <circle cx="36" cy="100" r="7" fill="#22c55e" />
                <circle cx="108" cy="100" r="7" fill="#ffd000" />
                <circle cx="148" cy="100" r="7" fill="#22c55e" />
                <circle cx="220" cy="100" r="7" fill="#22c55e" />
                <text
                  x="128"
                  y="32"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.9)"
                  font-size="8"
                  font-weight="700"
                >
                  H
                </text>
                <text
                  x="72"
                  y="70"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.9)"
                  font-size="7"
                  font-weight="700"
                >
                  H
                </text>
                <text
                  x="184"
                  y="70"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.9)"
                  font-size="7"
                  font-weight="700"
                >
                  H
                </text>
              </svg>
              <!-- Radar Board thumbnail — status card grid -->
              <svg
                v-else-if="map.view.type === 'radar'"
                viewBox="0 0 256 128"
                class="orb-home__thumb-media orb-home__thumb-media--fill"
              >
                <rect width="256" height="128" fill="#18181b" />
                <!-- OK cards -->
                <rect
                  x="10"
                  y="10"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="17" cy="21" r="2.5" fill="#22c55e" />
                <rect
                  x="23"
                  y="18.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="13" y="30" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="17.5" cy="33.5" r="1.5" fill="#22c55e" />
                <rect
                  x="70"
                  y="10"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="77" cy="21" r="2.5" fill="#22c55e" />
                <rect
                  x="83"
                  y="18.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="73" y="30" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="77.5" cy="33.5" r="1.5" fill="#22c55e" />
                <rect
                  x="190"
                  y="10"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="197" cy="21" r="2.5" fill="#22c55e" />
                <rect
                  x="203"
                  y="18.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="193" y="30" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="197.5" cy="33.5" r="1.5" fill="#22c55e" />
                <rect
                  x="10"
                  y="48"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="17" cy="59" r="2.5" fill="#22c55e" />
                <rect
                  x="23"
                  y="56.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="13" y="68" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="17.5" cy="71.5" r="1.5" fill="#22c55e" />
                <rect
                  x="130"
                  y="48"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="137" cy="59" r="2.5" fill="#22c55e" />
                <rect
                  x="143"
                  y="56.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="133" y="68" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="137.5" cy="71.5" r="1.5" fill="#22c55e" />
                <rect
                  x="190"
                  y="48"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="197" cy="59" r="2.5" fill="#22c55e" />
                <rect
                  x="203"
                  y="56.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="193" y="68" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="197.5" cy="71.5" r="1.5" fill="#22c55e" />
                <rect
                  x="70"
                  y="86"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="77" cy="97" r="2.5" fill="#22c55e" />
                <rect
                  x="83"
                  y="94.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="73" y="106" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="77.5" cy="109.5" r="1.5" fill="#22c55e" />
                <rect
                  x="130"
                  y="86"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(34,197,94,0.07)"
                  stroke="rgba(34,197,94,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="137" cy="97" r="2.5" fill="#22c55e" />
                <rect
                  x="143"
                  y="94.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(134,239,172,0.3)"
                />
                <rect x="133" y="106" width="32" height="7" rx="2" fill="rgba(34,197,94,0.12)" />
                <circle cx="137.5" cy="109.5" r="1.5" fill="#22c55e" />
                <!-- CRITICAL cards -->
                <rect
                  x="130"
                  y="10"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(239,68,68,0.07)"
                  stroke="rgba(239,68,68,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="137" cy="21" r="2.5" fill="#ef4444" />
                <rect
                  x="143"
                  y="18.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(252,165,165,0.3)"
                />
                <rect x="133" y="30" width="32" height="7" rx="2" fill="rgba(239,68,68,0.12)" />
                <circle cx="137.5" cy="33.5" r="1.5" fill="#ef4444" />
                <rect
                  x="10"
                  y="86"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(239,68,68,0.07)"
                  stroke="rgba(239,68,68,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="17" cy="97" r="2.5" fill="#ef4444" />
                <rect
                  x="23"
                  y="94.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(252,165,165,0.3)"
                />
                <rect x="13" y="106" width="32" height="7" rx="2" fill="rgba(239,68,68,0.12)" />
                <circle cx="17.5" cy="109.5" r="1.5" fill="#ef4444" />
                <!-- WARNING cards -->
                <rect
                  x="70"
                  y="48"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(255,208,0,0.07)"
                  stroke="rgba(255,208,0,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="77" cy="59" r="2.5" fill="#ffd000" />
                <rect x="83" y="56.5" width="30" height="3.5" rx="1.5" fill="rgba(255,208,0,0.3)" />
                <rect x="73" y="68" width="32" height="7" rx="2" fill="rgba(255,208,0,0.12)" />
                <circle cx="77.5" cy="71.5" r="1.5" fill="#ffd000" />
                <rect
                  x="190"
                  y="86"
                  width="56"
                  height="34"
                  rx="4"
                  fill="rgba(255,208,0,0.07)"
                  stroke="rgba(255,208,0,0.22)"
                  stroke-width="0.75"
                />
                <circle cx="197" cy="97" r="2.5" fill="#ffd000" />
                <rect
                  x="203"
                  y="94.5"
                  width="30"
                  height="3.5"
                  rx="1.5"
                  fill="rgba(255,208,0,0.3)"
                />
                <rect x="193" y="106" width="32" height="7" rx="2" fill="rgba(255,208,0,0.12)" />
                <circle cx="197.5" cy="109.5" r="1.5" fill="#ffd000" />
              </svg>
              <!-- Folder Tree thumbnail — nested SETUP folders with live severity -->
              <svg
                v-else-if="map.view.type === 'foldertree'"
                viewBox="0 0 256 128"
                class="orb-home__thumb-media orb-home__thumb-media--fill"
              >
                <rect width="256" height="128" fill="#18181b" />
                <!-- tree guide rails -->
                <path
                  d="M16 24 V102 M16 39 H26 M16 102 H26 M32 45 V81 M32 60 H42 M32 81 H42"
                  stroke="#3f3f46"
                  stroke-width="1"
                  fill="none"
                />
                <!-- row 1 (root, open) — green -->
                <path d="M10.5 15.5 h6 l-3 5 z" fill="#71717a" />
                <rect x="22" y="12" width="6" height="3" rx="1" fill="rgba(34,197,94,0.5)" />
                <rect
                  x="22"
                  y="14"
                  width="14"
                  height="9"
                  rx="1.5"
                  fill="rgba(34,197,94,0.18)"
                  stroke="rgba(34,197,94,0.6)"
                  stroke-width="0.75"
                />
                <rect x="40" y="16" width="78" height="5" rx="2" fill="rgba(255,255,255,0.22)" />
                <circle cx="240" cy="18" r="3.5" fill="#22c55e" />
                <!-- row 2 (open) — red -->
                <path d="M26.5 36.5 h6 l-3 5 z" fill="#71717a" />
                <rect x="38" y="33" width="6" height="3" rx="1" fill="rgba(239,68,68,0.5)" />
                <rect
                  x="38"
                  y="35"
                  width="14"
                  height="9"
                  rx="1.5"
                  fill="rgba(239,68,68,0.18)"
                  stroke="rgba(239,68,68,0.6)"
                  stroke-width="0.75"
                />
                <rect x="56" y="37" width="66" height="5" rx="2" fill="rgba(255,255,255,0.22)" />
                <circle cx="240" cy="39" r="3.5" fill="#ef4444" />
                <!-- row 3 (leaf) — red -->
                <rect x="44" y="54" width="6" height="3" rx="1" fill="rgba(239,68,68,0.5)" />
                <rect
                  x="44"
                  y="56"
                  width="14"
                  height="9"
                  rx="1.5"
                  fill="rgba(239,68,68,0.18)"
                  stroke="rgba(239,68,68,0.6)"
                  stroke-width="0.75"
                />
                <rect x="62" y="58" width="54" height="5" rx="2" fill="rgba(255,255,255,0.16)" />
                <circle cx="240" cy="60" r="3.5" fill="#ef4444" />
                <!-- row 4 (leaf) — green -->
                <rect x="44" y="75" width="6" height="3" rx="1" fill="rgba(34,197,94,0.5)" />
                <rect
                  x="44"
                  y="77"
                  width="14"
                  height="9"
                  rx="1.5"
                  fill="rgba(34,197,94,0.18)"
                  stroke="rgba(34,197,94,0.6)"
                  stroke-width="0.75"
                />
                <rect x="62" y="79" width="60" height="5" rx="2" fill="rgba(255,255,255,0.16)" />
                <circle cx="240" cy="81" r="3.5" fill="#22c55e" />
                <!-- row 5 (closed) — yellow -->
                <path d="M27 99 l4 3 l-4 3 z" fill="#71717a" />
                <rect x="38" y="96" width="6" height="3" rx="1" fill="rgba(255,208,0,0.5)" />
                <rect
                  x="38"
                  y="98"
                  width="14"
                  height="9"
                  rx="1.5"
                  fill="rgba(255,208,0,0.18)"
                  stroke="rgba(255,208,0,0.6)"
                  stroke-width="0.75"
                />
                <rect x="56" y="100" width="70" height="5" rx="2" fill="rgba(255,255,255,0.22)" />
                <circle cx="240" cy="102" r="3.5" fill="#ffd000" />
              </svg>
              <!-- Presentation thumbnail — design-first slide with title and gadgets -->
              <svg
                v-else-if="map.view.type === 'presentation'"
                viewBox="0 0 256 128"
                class="orb-home__thumb-media orb-home__thumb-media--fill"
              >
                <rect width="256" height="128" fill="#18181b" />
                <!-- slide canvas -->
                <rect
                  x="22"
                  y="12"
                  width="212"
                  height="104"
                  rx="6"
                  fill="#1f2430"
                  stroke="rgba(255,255,255,0.12)"
                  stroke-width="1"
                />
                <!-- title block -->
                <rect x="34" y="22" width="86" height="7" rx="2" fill="rgba(255,255,255,0.78)" />
                <rect x="34" y="33" width="54" height="4" rx="2" fill="rgba(255,255,255,0.3)" />
                <!-- gauge gadget -->
                <path
                  d="M44 96 A22 22 0 0 1 88 96"
                  fill="none"
                  stroke="#3f3f46"
                  stroke-width="5"
                  stroke-linecap="round"
                />
                <path
                  d="M44 96 A22 22 0 0 1 79 78.4"
                  fill="none"
                  stroke="#22c55e"
                  stroke-width="5"
                  stroke-linecap="round"
                />
                <rect x="58" y="88" width="16" height="4" rx="2" fill="rgba(255,255,255,0.5)" />
                <!-- bar gadget card -->
                <rect
                  x="110"
                  y="56"
                  width="46"
                  height="48"
                  rx="4"
                  fill="rgba(255,255,255,0.04)"
                  stroke="rgba(255,255,255,0.1)"
                  stroke-width="0.75"
                />
                <rect x="118" y="80" width="7" height="18" rx="1.5" fill="#22c55e" />
                <rect x="129" y="70" width="7" height="28" rx="1.5" fill="#ffd000" />
                <rect x="140" y="86" width="7" height="12" rx="1.5" fill="#22c55e" />
                <!-- value / light card -->
                <rect
                  x="164"
                  y="56"
                  width="46"
                  height="48"
                  rx="4"
                  fill="rgba(255,255,255,0.04)"
                  stroke="rgba(255,255,255,0.1)"
                  stroke-width="0.75"
                />
                <circle cx="187" cy="74" r="9" fill="rgba(239,68,68,0.22)" />
                <circle cx="187" cy="74" r="5" fill="#ef4444" />
                <rect x="174" y="90" width="26" height="6" rx="2" fill="rgba(255,255,255,0.28)" />
              </svg>
              <!-- Static board thumbnail — scattered host/service objects, no tree structure -->
              <svg
                v-else
                viewBox="0 0 256 128"
                class="orb-home__thumb-media orb-home__thumb-media--fill"
                font-family="system-ui,-apple-system,sans-serif"
              >
                <rect width="256" height="128" fill="#18181b" />
                <!-- subtle grid -->
                <line x1="64" y1="0" x2="64" y2="128" stroke="#27272a" stroke-width="0.5" />
                <line x1="128" y1="0" x2="128" y2="128" stroke="#27272a" stroke-width="0.5" />
                <line x1="192" y1="0" x2="192" y2="128" stroke="#27272a" stroke-width="0.5" />
                <line x1="0" y1="43" x2="256" y2="43" stroke="#27272a" stroke-width="0.5" />
                <line x1="0" y1="86" x2="256" y2="86" stroke="#27272a" stroke-width="0.5" />
                <!-- host OK top-left -->
                <circle cx="36" cy="30" r="13" fill="#22c55e" filter="url(#gs)" />
                <text
                  x="36"
                  y="30"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="9"
                  font-weight="700"
                >
                  H
                </text>
                <rect x="18" y="48" width="36" height="7" rx="2" fill="rgba(0,0,0,0.55)" />
                <text
                  x="36"
                  y="52"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.7)"
                  font-size="5"
                >
                  web-srv-01
                </text>
                <!-- service CRITICAL right -->
                <circle cx="212" cy="24" r="11" fill="#ef4444" filter="url(#rs)" />
                <text
                  x="212"
                  y="24"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="8"
                  font-weight="700"
                >
                  S
                </text>
                <rect x="193" y="40" width="38" height="7" rx="2" fill="rgba(0,0,0,0.55)" />
                <text
                  x="212"
                  y="44"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.7)"
                  font-size="5"
                >
                  HTTP Check
                </text>
                <!-- hostgroup OK center -->
                <circle cx="118" cy="58" r="14" fill="#22c55e" filter="url(#gs)" />
                <text
                  x="118"
                  y="58"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="7.5"
                  font-weight="700"
                  letter-spacing="-0.5"
                >
                  HG
                </text>
                <rect x="98" y="77" width="40" height="7" rx="2" fill="rgba(0,0,0,0.55)" />
                <text
                  x="118"
                  y="81"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.7)"
                  font-size="5"
                >
                  linux-servers
                </text>
                <!-- service WARNING bottom-left -->
                <circle cx="58" cy="100" r="11" fill="#ffd000" />
                <text
                  x="58"
                  y="100"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(0,0,0,0.75)"
                  font-size="8"
                  font-weight="700"
                >
                  S
                </text>
                <rect x="38" y="116" width="40" height="7" rx="2" fill="rgba(0,0,0,0.55)" />
                <text
                  x="58"
                  y="120"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.7)"
                  font-size="5"
                >
                  Disk Usage
                </text>
                <!-- service OK right-center -->
                <circle cx="190" cy="82" r="11" fill="#22c55e" filter="url(#gs)" />
                <text
                  x="190"
                  y="82"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="8"
                  font-weight="700"
                >
                  S
                </text>
                <rect x="170" y="98" width="40" height="7" rx="2" fill="rgba(0,0,0,0.55)" />
                <text
                  x="190"
                  y="102"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="rgba(255,255,255,0.7)"
                  font-size="5"
                >
                  CPU Load
                </text>
                <!-- map link top-center -->
                <circle cx="152" cy="20" r="9" fill="#71717a" />
                <text
                  x="152"
                  y="20"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="7"
                  font-weight="700"
                >
                  M
                </text>
                <!-- servicegroup bottom-right -->
                <circle cx="234" cy="108" r="10" fill="#22c55e" filter="url(#gs)" />
                <text
                  x="234"
                  y="108"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="6.5"
                  font-weight="700"
                  letter-spacing="-0.5"
                >
                  SG
                </text>
                <!-- host UNREACHABLE bottom-center -->
                <circle cx="96" cy="112" r="9" fill="#f97316" />
                <text
                  x="96"
                  y="112"
                  text-anchor="middle"
                  dominant-baseline="central"
                  fill="white"
                  font-size="7"
                  font-weight="700"
                >
                  H
                </text>
                <defs>
                  <filter id="gs" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow
                      dx="0"
                      dy="0"
                      stdDeviation="2.5"
                      flood-color="rgba(34,197,94,0.4)"
                    />
                  </filter>
                  <filter id="rs" x="-30%" y="-30%" width="160%" height="160%">
                    <feDropShadow
                      dx="0"
                      dy="0"
                      stdDeviation="2.5"
                      flood-color="rgba(239,68,68,0.5)"
                    />
                  </filter>
                </defs>
              </svg>
              <!-- Type + rotation badges overlaid on thumbnail -->
              <div class="orb-home__badges orb-home__badges--type">
                <span
                  class="orb-home__type-badge"
                  :class="
                    map.view.type === 'worldmap'
                      ? 'orb-home__type-badge--worldmap'
                      : map.view.type === 'radar'
                        ? 'orb-home__type-badge--radar'
                        : map.view.type === 'flow'
                          ? 'orb-home__type-badge--flow'
                          : map.view.type === 'static'
                            ? 'orb-home__type-badge--static'
                            : map.view.type === 'foldertree'
                              ? 'orb-home__type-badge--foldertree'
                              : map.view.type === 'presentation'
                                ? 'orb-home__type-badge--presentation'
                                : 'orb-home__type-badge--generic'
                  "
                >
                  {{ boardTypeLabel(map.view.type) }}
                </span>
              </div>
              <div v-if="auth.isAdmin" class="orb-home__badges orb-home__badges--admin">
                <span
                  v-if="map.show_in_lists === false"
                  class="orb-home__flag-badge"
                  :title="_t('Hidden from regular users')"
                >
                  {{ _t('hidden') }}
                </span>
                <span
                  v-if="map.readonly"
                  class="orb-home__flag-badge"
                  :title="_t('Demo board — cannot be edited')"
                >
                  {{ _t('read-only') }}
                </span>
                <span
                  v-if="map.rotation_interval > 0"
                  class="orb-home__rotation-badge"
                  :title="_t('Rotates every %{n} seconds', { n: map.rotation_interval })"
                >
                  ↻ {{ map.rotation_interval }}s
                </span>
              </div>
            </div>

            <!-- Card body -->
            <div class="orb-home__card-body">
              <div class="orb-home__card-name" :title="map.alias || map.name">
                {{ map.alias || map.name }}
              </div>
              <div class="orb-home__card-meta">
                <template v-if="auth.isAdmin">
                  <svg
                    class="orb-home__meta-icon"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3m0 3h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008zm-3 6h.008v.008h-.008v-.008zm0-6h.008v.008h-.008v-.008z"
                    />
                  </svg>
                  <span class="orb-home__card-conn" :title="map.connection_id">{{
                    connectionsStore.labelFor(map.connection_id)
                  }}</span>
                  <span class="orb-home__card-dot">·</span>
                </template>
                <span
                  v-if="map.readonly || ['flow', 'radar', 'worldmap'].includes(map.view.type)"
                  class="orb-home__card-count orb-home__card-count--dynamic"
                  >{{ _t('dynamic') }}</span
                >
                <span v-else class="orb-home__card-count">{{
                  _tn('%{n} object', '%{n} objects', map.object_count, { n: map.object_count })
                }}</span>
              </div>
            </div>
          </router-link>

          <div v-if="auth.isAdmin || map.can_edit" class="orb-home__card-actions">
            <button
              v-if="(auth.isAdmin || map.can_edit) && !map.readonly"
              class="orb-home__action orb-home__action--settings"
              :title="_t('Board Settings')"
              @click.stop="openSettings(map)"
            >
              <svg
                style="width: 14px; height: 14px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
                />
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                />
              </svg>
            </button>
            <button
              v-if="auth.canCreateBoards"
              class="orb-home__action orb-home__action--clone"
              :title="_t('Clone board')"
              @click.stop="cloneBoard(map)"
            >
              <svg
                style="width: 14px; height: 14px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
                />
              </svg>
            </button>
            <button
              v-if="auth.canCreateBoards"
              class="orb-home__action orb-home__action--export"
              :title="_t('Export board as JSON')"
              @click.stop="exportBoard(map.name)"
            >
              <svg
                style="width: 14px; height: 14px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                />
              </svg>
            </button>
            <button
              v-if="auth.canCreateBoards"
              class="orb-home__action orb-home__action--delete"
              :title="_t('Delete board &quot;%{name}&quot;?', { name: map.alias || map.name })"
              @click.stop="deleteBoard(map)"
            >
              <svg
                style="width: 14px; height: 14px"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Table view -->
      <BoardsTable
        v-else
        data-tour="boards-grid"
        :boards="filteredBoards"
        :selected-boards="selectedBoards"
        :search-query="searchQuery"
        :all-selected="allFilteredSelected"
        @toggle-select="toggleBoardSelection"
        @toggle-select-all="toggleSelectAllFiltered"
        @open-settings="openSettings"
        @clone="cloneBoard"
        @export="exportBoard"
        @delete="deleteBoard"
      />
    </main>
  </div>
  <OrbConfirmDialog
    :open="!!confirmDelete"
    :title="_t('Delete board')"
    :message="
      confirmDelete
        ? _t('Are you sure you want to delete &quot;%{name}&quot;? This action cannot be undone.', {
            name: confirmDelete.alias || confirmDelete.name
          })
        : ''
    "
    :confirm-label="_t('Delete')"
    @confirm="doDelete"
    @cancel="confirmDelete = null"
  />

  <template v-if="auth.canCreateBoards">
    <BoardBulkActionBar
      v-if="capabilities.formSpecs"
      :count="selectedCount"
      :busy="bulkBusy"
      :select-all-checked="allFilteredSelected"
      :select-all-label="_t('Select all (%{n} visible)', { n: filteredBoards.length })"
      :can-edit="true"
      @cancel="clearSelection"
      @edit="openBulkEdit"
      @export="doBulkExport"
      @delete="openBulkDelete"
      @toggle-select-all="toggleSelectAllFiltered($event)"
    />
    <BoardBulkActionBarLegacy
      v-else
      :count="selectedCount"
      :busy="bulkBusy"
      :select-all-checked="allFilteredSelected"
      :select-all-label="_t('Select all (%{n} visible)', { n: filteredBoards.length })"
      @cancel="clearSelection"
      @export="doBulkExport"
      @delete="openBulkDelete"
      @toggle-select-all="toggleSelectAllFiltered($event)"
    />
  </template>

  <BoardBulkEditSlideIn
    v-if="capabilities.formSpecs && showBulkEdit"
    :open="showBulkEdit"
    :names="editableSelectedNames"
    :aliases="editableSelectedAliases"
    :saving="bulkBusy"
    @cancel="showBulkEdit = false"
    @apply="doBulkEdit"
  />

  <BoardBulkDeleteDialog
    v-if="capabilities.formSpecs"
    :open="confirmBulkDelete"
    :names="selectedAliases"
    :busy="bulkBusy"
    @confirm="doBulkDelete"
    @cancel="confirmBulkDelete = false"
  />
  <BoardBulkDeleteDialogLegacy
    v-else
    :open="confirmBulkDelete"
    :names="selectedAliases"
    :busy="bulkBusy"
    @confirm="doBulkDelete"
    @cancel="confirmBulkDelete = false"
  />

  <OrbModal :open="!!confirmClone" :title="_t('Clone board')" closable @close="confirmClone = null">
    <div class="home-clone-modal__field">
      <label class="home-clone-modal__label">{{ _t('Board ID') }}</label>
      <input
        ref="cloneInputEl"
        :value="cloneNewName"
        class="home-clone-modal__input home-clone-modal__input--mono"
        spellcheck="false"
        @input="onCloneNameInput"
        @keydown.enter="doClone"
        @keydown.esc="confirmClone = null"
        @focus="($event.target as HTMLInputElement).select()"
      />
    </div>
    <div class="home-clone-modal__field">
      <label class="home-clone-modal__label">{{ _t('Display name') }}</label>
      <input v-model="cloneAlias" class="home-clone-modal__input" spellcheck="false" />
    </div>
    <p v-if="cloneError" class="home-clone-modal__error">{{ cloneError }}</p>

    <template #footer>
      <CmkButton variant="secondary" @click="confirmClone = null">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="!cloneNewName" @click="doClone">
        {{ _t('Clone') }}
      </CmkButton>
    </template>
  </OrbModal>

  <BoardSettingsModal
    v-if="settingsBoard"
    :board="settingsBoard"
    @close="settingsBoard = null"
    @updated="boardsStore.fetchBoards()"
  />

  <!-- Import FAB (board creators only) -->
  <label v-if="auth.canCreateBoards" class="orb-home__import-fab" :title="_t('Import')">
    <svg
      class="orb-home__import-icon"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      stroke-width="2.5"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
      />
    </svg>
    <span class="orb-home__import-label">{{ _t('Import') }}</span>
    <input
      type="file"
      accept=".json,.cfg,application/json"
      class="orb-home__import-input"
      @change="importBoard"
    />
  </label>
  <OrbConfirmDialog
    :open="!!importConflict"
    :title="_t('Import')"
    :message="
      importConflict
        ? _t('Board &quot;%{name}&quot; already exists. Overwrite?', { name: importConflict.name })
        : ''
    "
    :confirm-label="_t('Overwrite')"
    confirm-variant="warning"
    @confirm="confirmImportOverwrite"
    @cancel="importConflict = null"
  />

  <CreateBoardModal v-if="showCreate" @close="showCreate = false" @created="onCreated" />
  <OnboardingTour
    v-if="showOnboarding && auth.user"
    :steps="tourSteps"
    :storage-key="`orbvis_onboarded_${auth.user.user_id}`"
    :show-create-board="auth.canCreateBoards"
    @close="showOnboarding = false"
    @create-board="onTourCreateBoard"
  />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import OnboardingTour from '@/components/OnboardingTour.vue'
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue'
import OrbModal from '@/components/OrbModal.vue'
import WorldMapThumbnail from '@/components/WorldMapThumbnail.vue'
import BoardBulkActionBar from '@/components/board/BoardBulkActionBar.vue'
import BoardBulkActionBarLegacy from '@/components/board/BoardBulkActionBarLegacy.vue'
import BoardBulkDeleteDialog from '@/components/board/BoardBulkDeleteDialog.vue'
import BoardBulkDeleteDialogLegacy from '@/components/board/BoardBulkDeleteDialogLegacy.vue'
import BoardBulkEditSlideIn from '@/components/board/BoardBulkEditSlideIn.vue'
import BoardSettingsModal from '@/components/board/BoardSettingsModal.vue'
import BoardsTable from '@/components/board/BoardsTable.vue'
import CreateBoardModal from '@/components/board/CreateBoardModal.vue'
import CmkButton from '@/components/cmk/CmkButton'
import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup'

import { boardsApi } from '@/api/client'
import { useBoardBulkActions } from '@/composables/useBoardBulkActions'
import { useBoardImportExport } from '@/composables/useBoardImportExport'
import { useBoardListViewMode } from '@/composables/useBoardListViewMode'
import { useChangelog } from '@/composables/useChangelog'
import { useDragReorder } from '@/composables/useDragReorder'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import type { BoardRead, WorldmapView } from '@/types/api'
import type { TourStep } from '@/types/tour'
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t, _tn } = usei18n()
const baseUrl = import.meta.env.BASE_URL
// Boards whose background image 404s (e.g. an imported map_image that was never
// uploaded) fall back to the board-type thumbnail.
const bgImageFailed = reactive<Record<string, boolean>>({})
const auth = useAuthStore()
const boardsStore = useBoardsStore()
const router = useRouter()

// Card meta shows the connection's display name, not the raw id — same
// treatment as the boards table; falls back to the id until loaded.
const connectionsStore = useConnectionsStore()
if (auth.isAdmin) void connectionsStore.ensureConnections()
const { changelogVisible } = useChangelog()
const showCreate = ref(false)
const showOnboarding = ref(false)

const tourSteps = computed<TourStep[]>(() => {
  const all: TourStep[] = [
    {
      selector: null,
      title: _t('Welcome to OrbVis'),
      body: _t(
        'OrbVis visualizes the status of your monitored infrastructure — hosts, services, groups and more — on customizable boards.'
      )
    },
    {
      selector: '[data-tour="sidebar-nav"]',
      title: _t('Navigation'),
      body: auth.isAdmin
        ? _t(
            '"Overview" in the sidebar brings you back to the board list. The admin section below gives access to connections, images, users and settings.'
          )
        : _t('"Overview" in the sidebar brings you back to the board list.')
    },
    {
      selector: '[data-tour="boards-grid"]',
      title: _t('Your boards'),
      body: _t(
        'Each card is a board — a visual map of your monitoring landscape. OrbVis supports static boards, Geo Boards, Radar views and Flow Boards.'
      )
    },
    {
      selector: auth.isAdmin ? '[data-tour="new-board"]' : null,
      title: _t('Ready to go!'),
      body: auth.isAdmin
        ? _t(
            'Create your first board here. Inside a board, click the pencil button (bottom-right) to enter edit mode and start placing monitoring objects.'
          )
        : _t(
            'Your administrator can create boards and grant you access. Once a board is available it will appear here.'
          )
    }
  ]
  return auth.ssoActive || auth.isCheckmkDeployment
    ? all.filter((s) => s.selector !== '[data-tour="sidebar-nav"]')
    : all
})
const confirmDelete = ref<{ name: string; alias: string } | null>(null)
const capabilities = useCapabilitiesStore()
const settingsStore = useSettingsStore()

// Cards-vs-table choice (per-user localStorage override + global default).
const { viewMode, viewModeOptions, setViewMode } = useBoardListViewMode()

// Multi-select + bulk delete/edit/export for the board list (table view).
const {
  selectedBoards,
  confirmBulkDelete,
  bulkBusy,
  showBulkEdit,
  clearSelection,
  toggleBoardSelection,
  selectedCount,
  allFilteredSelected,
  toggleSelectAllFiltered,
  selectedAliases,
  openBulkDelete,
  doBulkDelete,
  editableSelectedNames,
  editableSelectedAliases,
  openBulkEdit,
  doBulkEdit,
  doBulkExport
} = useBoardBulkActions({
  filteredBoards: () => filteredBoards.value,
  viewMode: () => viewMode.value,
  openSettings: (map) => openSettings(map)
})

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

// Single-board import / export / clone (with overwrite-conflict handling).
const cloneInputEl = ref<HTMLInputElement | null>(null)
const {
  importConflict,
  importBoard,
  confirmImportOverwrite,
  exportBoard,
  confirmClone,
  cloneNewName,
  cloneAlias,
  cloneError,
  cloneBoard,
  onCloneNameInput,
  doClone
} = useBoardImportExport({ cloneInputEl })

const settingsBoard = ref<BoardRead | null>(null)

function openSettings(map: BoardRead) {
  settingsBoard.value = map
}

const searchQuery = ref('')

const visibleBoards = computed(() =>
  auth.isAdmin ? boardsStore.boards : boardsStore.boards.filter((m) => m.show_in_lists !== false)
)

const filteredBoards = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return visibleBoards.value
  return visibleBoards.value.filter(
    (m) => m.name.toLowerCase().includes(q) || m.alias.toLowerCase().includes(q)
  )
})

const isDragEnabled = computed(() => auth.isAdmin && !searchQuery.value.trim())

const draggableBoards = computed(() =>
  isDragEnabled.value ? boardsStore.boards : filteredBoards.value
)

// Reorder operates on the FULL store list — never on the filtered subset.
// The isEnabled guard ensures drags only start when both lists are identical.
const { dragIndex, onDragStart, onDragOver, onDrop, onDragEnd } = useDragReorder(
  () => boardsStore.boards,
  (list) => {
    boardsStore.boards.splice(0, boardsStore.boards.length, ...list)
  },
  persistBoardOrder,
  () => isDragEnabled.value
)

function persistBoardOrder() {
  const order = boardsStore.boards.map((b, i) => ({ name: b.name, sort_order: i }))
  boardsApi.reorder(order, auth.accessToken!).catch(() => boardsStore.fetchBoards())
}

const TYPE_LABELS: Record<string, string> = {
  static: 'Static',
  worldmap: 'Geo Board',
  flow: 'Flow Board',
  radar: 'Radar',
  foldertree: 'Folder Tree',
  presentation: 'Presentation'
}
function boardTypeLabel(type: string) {
  return TYPE_LABELS[type] ?? type
}

function worldmapLat(map: BoardRead) {
  return map.view.type === 'worldmap' ? (map.view as WorldmapView).lat : 51
}
function worldmapLng(map: BoardRead) {
  return map.view.type === 'worldmap' ? (map.view as WorldmapView).lng : 10
}
function worldmapZoom(map: BoardRead) {
  return map.view.type === 'worldmap' ? (map.view as WorldmapView).zoom : 5
}

onMounted(async () => {
  await Promise.all([boardsStore.fetchBoards(), settingsStore.load()])
  if (!auth.user) return
  const storageKey = `orbvis_onboarded_${auth.user.user_id}`
  if (localStorage.getItem(storageKey)) return
  // Existing operators who already have boards have outgrown the
  // onboarding tour; mark them as onboarded so an upgrade doesn't
  // ambush them with it.
  if (boardsStore.boards.length > 0) {
    localStorage.setItem(storageKey, '1')
    return
  }
  if (changelogVisible.value) {
    const stop = watch(changelogVisible, (val) => {
      if (!val) {
        showOnboarding.value = true
        stop()
      }
    })
  } else {
    showOnboarding.value = true
  }
})

function onTourCreateBoard(): void {
  showOnboarding.value = false
  showCreate.value = true
}
</script>

<style scoped>
.orb-home {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--bg);
}

.orb-home__main {
  padding: var(--dimension-7) 24px 40px;
}

.orb-home__toolbar {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  max-width: 960px;
  margin: 0 auto 20px;
}

.orb-home__title {
  margin-right: var(--dimension-4);
  font-size: var(--font-size-xlarge);
  line-height: 24px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.025em;
}

.orb-home__search {
  position: relative;
  width: 200px;
}

.orb-home__search-icon {
  position: absolute;
  top: 50%;
  left: 8px;
  width: 13px;
  height: 13px;
  color: var(--text-muted);
  pointer-events: none;
  transform: translateY(-50%);
}

.orb-home__search-input {
  width: 100%;
  padding: 5px 8px 5px 26px;
  font-size: 12px;
  color: var(--text);
  background: var(--bg-input);
  border-radius: 4px;
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--default-form-element-border-color) 50%, transparent);
  transition: all 0.15s;
}

.orb-home__search-input::placeholder {
  color: var(--default-form-element-placeholder-color);
}

.orb-home__search-input:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--color-corporate-green-50);
}

.orb-home__search-clear {
  position: absolute;
  top: 50%;
  right: 6px;
  color: var(--text-muted);
  transform: translateY(-50%);
  transition: color 0.15s;
}

.orb-home__search-clear:hover {
  color: var(--text);
}

.orb-home__toggle-group {
  display: inline-flex;
  align-items: center;
  overflow: hidden;
  background: var(--bg-input);
  border-radius: 4px;
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--default-form-element-border-color) 60%, transparent);
}

.orb-home__toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  font-size: 12px;
  color: var(--text-muted);
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-home__toggle-btn:hover {
  color: var(--text);
}

.orb-home__toggle-btn--bordered {
  border-left: 1px solid
    color-mix(in srgb, var(--default-form-element-border-color) 60%, transparent);
}

.orb-home__toggle-btn--active,
.orb-home__toggle-btn--active:hover {
  color: var(--button-primary-text-color, #000);
  background: var(--color-corporate-green-50);
}

.orb-home__new-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--button-primary-text-color, #000);
  background: var(--color-corporate-green-50);
  border-radius: 4px;
  transition: all 0.15s;
}

.orb-home__new-btn:hover {
  background: var(--color-corporate-green-60);
}

.orb-home__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--dimension-4);
  padding: 48px 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-home__spinner {
  width: 16px;
  height: 16px;
  color: var(--color-corporate-green-50);
  animation: orb-home-spin 1s linear infinite;
}

@keyframes orb-home-spin {
  to {
    transform: rotate(360deg);
  }
}

.orb-home__spinner-track {
  opacity: 0.25;
}

.orb-home__spinner-head {
  opacity: 0.75;
}

.orb-home__error {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--dimension-4) 12px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
  border-radius: 12px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-light-red-50) 20%, transparent);
}

.orb-home__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  text-align: center;
}

.orb-home__empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin-bottom: var(--dimension-6);
  background: var(--default-form-element-bg-color);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--default-form-element-border-color);
}

.orb-home__empty-icon svg {
  width: 22px;
  height: 22px;
  color: var(--text-muted);
}

.orb-home__empty-title {
  font-weight: 600;
  color: var(--text);
}

.orb-home__empty-hint {
  margin-top: 6px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-home__empty-cta {
  color: var(--color-corporate-green-50);
}

.orb-home__grid {
  display: grid;
  grid-template-columns: repeat(1, minmax(0, 1fr));
  gap: var(--dimension-6);
  max-width: 960px;
  margin: 0 auto;
}

@media (width >= 640px) {
  .orb-home__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (width >= 1024px) {
  .orb-home__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.orb-home__no-results {
  grid-column: 1 / -1;
  padding: 40px 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  text-align: center;
}

.orb-home__card {
  position: relative;
  overflow: hidden;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
  transition: all 0.2s;
}

.orb-home__card:hover {
  background: var(--bg-hover);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent),
    0 10px 15px -3px color-mix(in srgb, var(--color-corporate-green-100) 10%, transparent),
    0 4px 6px -4px color-mix(in srgb, var(--color-corporate-green-100) 10%, transparent);
  transform: translateY(-2px);
}

.orb-home__card--draggable {
  cursor: grab;
}

.orb-home__card--draggable:active {
  cursor: grabbing;
}

.orb-home__card--dragging {
  opacity: 0.5;
}

.orb-home__card-link {
  display: block;
}

.orb-home__thumb {
  position: relative;
  width: 100%;
  height: 144px;
  overflow: hidden;
  background: var(--default-form-element-bg-color);
}

.orb-home__thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.orb-home__thumb-media {
  pointer-events: none;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.orb-home__thumb-media--fill {
  width: 100%;
  height: 100%;
}

.orb-home__card:hover .orb-home__thumb-img,
.orb-home__card:hover .orb-home__thumb-media {
  opacity: 0.9;
}

.orb-home__badges {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 5px;
}

.orb-home__badges--type {
  bottom: 8px;
  left: 8px;
}

.orb-home__badges--admin {
  top: 8px;
  right: 8px;
}

.orb-home__type-badge {
  padding: var(--dimension-2) 6px;
  font-size: 11px;
  font-weight: 500;
  backdrop-filter: blur(4px);
  border-radius: 6px;
}

.orb-home__type-badge--worldmap {
  color: var(--color-cyan-80);
  background: color-mix(in srgb, var(--color-cyan-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-cyan-60) 40%, transparent);
}

.dark .orb-home__type-badge--worldmap {
  color: var(--color-cyan-30);
  background: color-mix(in srgb, var(--color-cyan-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-cyan-50) 30%, transparent);
}

.orb-home__type-badge--radar {
  color: var(--color-purple-80);
  background: color-mix(in srgb, var(--color-purple-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-purple-60) 40%, transparent);
}

.dark .orb-home__type-badge--radar {
  color: var(--color-purple-30);
  background: color-mix(in srgb, var(--color-purple-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-purple-50) 30%, transparent);
}

.orb-home__type-badge--flow {
  color: var(--color-corporate-green-80);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-70) 40%, transparent);
}

.dark .orb-home__type-badge--flow {
  color: var(--color-corporate-green-30);
  background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

.orb-home__type-badge--static {
  color: var(--color-mid-grey-70);
  background: color-mix(in srgb, var(--color-mid-grey-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-mid-grey-50) 40%, transparent);
}

.dark .orb-home__type-badge--static {
  color: var(--color-mid-grey-30);
  background: color-mix(in srgb, var(--color-mid-grey-40) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-mid-grey-40) 30%, transparent);
}

.orb-home__type-badge--foldertree {
  color: var(--color-yellow-80);
  background: color-mix(in srgb, var(--color-yellow-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-yellow-60) 40%, transparent);
}

.dark .orb-home__type-badge--foldertree {
  color: var(--color-yellow-30);
  background: color-mix(in srgb, var(--color-yellow-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-yellow-50) 30%, transparent);
}

.orb-home__type-badge--presentation {
  color: var(--color-pink-80);
  background: color-mix(in srgb, var(--color-pink-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-pink-60) 40%, transparent);
}

.dark .orb-home__type-badge--presentation {
  color: var(--color-pink-30);
  background: color-mix(in srgb, var(--color-pink-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-pink-50) 30%, transparent);
}

.orb-home__type-badge--generic {
  color: var(--text);
  background: color-mix(in srgb, var(--bg-surface) 85%, transparent);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.orb-home__flag-badge {
  padding: var(--dimension-2) 5px;
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  background: color-mix(in srgb, var(--bg-surface) 80%, transparent);
  backdrop-filter: blur(4px);
  border-radius: 6px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--default-border-color) 60%, transparent);
}

.orb-home__rotation-badge {
  padding: var(--dimension-2) 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 20%, transparent);
  backdrop-filter: blur(4px);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}

.orb-home__card-body {
  padding: 10px 12px;
}

.orb-home__card-name {
  overflow: hidden;
  margin-bottom: 5px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-home__card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.orb-home__meta-icon {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  color: var(--text-muted);
}

.orb-home__card-conn {
  overflow: hidden;
  font-family: monospace;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-home__card-dot {
  flex-shrink: 0;
  color: var(--text-muted);
}

.orb-home__card-count {
  flex-shrink: 0;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text-muted);
}

.orb-home__card-count--dynamic {
  font-style: italic;
}

.orb-home__card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--dimension-2);
  max-height: 0;
  padding: 0 6px;
  overflow: hidden;
  border-top: 1px solid var(--border);
  transition: max-height 0.15s;
}

.orb-home__card:hover .orb-home__card-actions,
.orb-home__card:focus-within .orb-home__card-actions {
  max-height: 36px;
}

.orb-home__action {
  padding: var(--dimension-3);
  color: var(--text-muted);
  border-radius: 4px;
  transition: all 0.15s;
}

.orb-home__action--settings:hover {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-home__action--clone:hover {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
}

.orb-home__action--export:hover {
  color: var(--text);
  background: var(--color-white-0);
}

.orb-home__action--delete:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

.orb-home__import-fab {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  color: var(--text-muted);
  cursor: pointer;
  background: var(--bg-surface);
  border-radius: 4px;
  box-shadow:
    0 0 0 1px var(--border),
    0 10px 15px -3px rgb(0 0 0 / 10%),
    0 4px 6px -4px rgb(0 0 0 / 10%);
  transition: all 0.15s;
}

.orb-home__import-fab:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.orb-home__import-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

.orb-home__import-label {
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
}

.orb-home__import-input {
  display: none;
}

.home-clone-modal__field {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  margin-bottom: var(--dimension-4);
  min-width: 320px;
}

.home-clone-modal__label {
  font-size: var(--font-size-large);
  font-weight: 500;
  color: var(--text-muted);
}

.home-clone-modal__input {
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  background: var(--default-form-element-bg-color);
  border: 1px solid var(--default-form-element-border-color);
  border-radius: var(--dimension-3);
  font-size: var(--font-size-large);
  color: var(--text);
}

.home-clone-modal__input--mono {
  font-family: monospace;
}

.home-clone-modal__input:focus {
  outline: none;
  border-color: var(--color-corporate-green-50);
  box-shadow: 0 0 0 2px var(--color-corporate-green-50);
}

.home-clone-modal__error {
  font-size: var(--font-size-large);
  color: var(--color-light-red-40);
  margin-bottom: var(--dimension-4);
}

.home-view-toggle {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.home-view-toggle :deep(.cmk-toggle-button-group__container) {
  margin-bottom: 0;
  padding: 2px;
  border-radius: 4px;
}

.home-view-toggle :deep(.cmk-toggle-button-group__toggle-option) {
  min-width: 60px;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 3px;
}
</style>
