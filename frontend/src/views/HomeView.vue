<template>
    <div class="flex-1 min-h-0 overflow-y-auto bg-[var(--bg)]">
        <main style="padding: 20px 24px 40px">
            <div class="flex items-center" style="max-width: 960px; margin: 0 auto 20px; gap: 8px">
                <h2
                    class="text-base font-semibold text-[var(--text)] tracking-tight"
                    style="margin-right: 8px"
                >
                    {{ t('home.title') }}
                </h2>
                <div class="relative" style="width: 200px">
                    <svg
                        class="absolute top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none"
                        style="left: 8px; width: 13px; height: 13px"
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
                        :placeholder="t('home.search')"
                        class="w-full bg-[var(--bg-input)] ring-1 ring-[var(--default-form-element-border-color)]/50 rounded text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] transition-all"
                        style="font-size: 12px; padding: 5px 8px 5px 26px"
                        :style="searchQuery ? 'padding-right: 24px' : ''"
                    />
                    <button
                        v-if="searchQuery"
                        class="absolute top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 transition-colors"
                        style="right: 6px"
                        :title="t('home.clearSearch')"
                        @click="searchQuery = ''"
                    >
                        <svg
                            style="width: 12px; height: 12px"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>
                <button
                    v-if="auth.isAdmin"
                    data-tour="new-board"
                    class="flex items-center bg-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-60)] rounded font-semibold text-[var(--button-primary-text-color,#000)] transition-all"
                    style="gap: 5px; padding: 5px 10px; font-size: 12px"
                    @click="showCreate = true"
                >
                    <svg
                        style="width: 11px; height: 11px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 4.5v15m7.5-7.5h-15"
                        />
                    </svg>
                    {{ t('admin.newBoard') }}
                </button>
            </div>

            <!-- Loading -->
            <div
                v-if="boardsStore.loading"
                class="flex items-center text-zinc-500 text-sm justify-center"
                style="gap: 8px; padding: 48px 0"
            >
                <svg
                    class="animate-spin w-4 h-4 text-[var(--color-corporate-green-50)]"
                    fill="none"
                    viewBox="0 0 24 24"
                >
                    <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                    />
                    <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                </svg>
                {{ t('common.loading') }}
            </div>

            <!-- Error -->
            <div
                v-else-if="boardsStore.error"
                class="flex items-center bg-red-500/8 ring-1 ring-red-500/20 rounded-xl text-red-400 text-sm"
                style="gap: 6px; padding: 8px 12px"
            >
                {{ boardsStore.error }}
            </div>

            <!-- Empty state -->
            <div
                v-else-if="boardsStore.boards.length === 0"
                class="flex flex-col items-center justify-center text-center"
                style="padding: 80px 0"
            >
                <div
                    class="rounded-xl bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] flex items-center justify-center"
                    style="width: 40px; height: 40px; margin-bottom: 16px"
                >
                    <svg
                        class="text-zinc-600"
                        style="width: 22px; height: 22px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="1.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"
                        />
                    </svg>
                </div>
                <p class="text-zinc-300 font-semibold">{{ t('home.noBoardsTitle') }}</p>
                <p class="text-zinc-600 text-sm" style="margin-top: 6px">
                    <span v-if="auth.isAdmin" class="text-[var(--color-corporate-green-50)]">{{
                        t('home.noBoardsAdmin')
                    }}</span>
                    <span v-else>{{ t('home.noBoardsUser') }}</span>
                </p>
            </div>

            <!-- Board grid -->
            <VueDraggable
                v-else
                v-model="draggableBoards"
                :disabled="!isDragEnabled"
                data-tour="boards-grid"
                class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
                style="max-width: 960px; margin: 0 auto; gap: 16px"
                @end="onDragEnd"
            >
                <p
                    v-if="searchQuery && !filteredBoards.length"
                    class="col-span-full text-center text-zinc-600 text-sm"
                    style="padding: 40px 0"
                >
                    {{ t('home.noSearchResults', { q: searchQuery }) }}
                </p>
                <div
                    v-for="map in draggableBoards"
                    :key="map.name"
                    :class="isDragEnabled ? 'cursor-grab active:cursor-grabbing' : ''"
                    class="group relative bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] hover:ring-[var(--color-corporate-green-50)]/40 rounded-xl overflow-hidden transition-all duration-200 hover:-translate-y-[2px] hover:shadow-lg hover:shadow-[var(--color-corporate-green-100)]/10"
                >
                    <router-link :to="`/boards/${map.name}`" class="block">
                        <!-- Thumbnail -->
                        <div
                            class="relative w-full overflow-hidden bg-[var(--default-form-element-bg-color)]"
                            style="height: 144px"
                        >
                            <img
                                v-if="map.background_image && !map.name.startsWith('demo-')"
                                :src="`${baseUrl}boards/backgrounds/${map.background_image}`"
                                :alt="map.alias || map.name"
                                class="w-full h-full object-cover opacity-70 group-hover:opacity-90 transition-opacity duration-200"
                            />
                            <!-- Worldmap thumbnail -->
                            <WorldMapThumbnail
                                v-else-if="map.view.type === 'worldmap'"
                                :lat="worldmapLat(map)"
                                :lng="worldmapLng(map)"
                                :zoom="worldmapZoom(map)"
                                class="opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none"
                            />
                            <!-- Flow Board thumbnail -->
                            <svg
                                v-else-if="map.view.type === 'flow'"
                                viewBox="0 0 256 128"
                                class="w-full h-full opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none"
                            >
                                <rect width="256" height="128" fill="#18181b" />
                                <line
                                    x1="128"
                                    y1="28"
                                    x2="72"
                                    y2="66"
                                    stroke="#3f3f46"
                                    stroke-width="1.5"
                                />
                                <line
                                    x1="128"
                                    y1="28"
                                    x2="184"
                                    y2="66"
                                    stroke="#3f3f46"
                                    stroke-width="1.5"
                                />
                                <line
                                    x1="72"
                                    y1="66"
                                    x2="36"
                                    y2="100"
                                    stroke="#3f3f46"
                                    stroke-width="1.5"
                                />
                                <line
                                    x1="72"
                                    y1="66"
                                    x2="108"
                                    y2="100"
                                    stroke="#3f3f46"
                                    stroke-width="1.5"
                                />
                                <line
                                    x1="184"
                                    y1="66"
                                    x2="148"
                                    y2="100"
                                    stroke="#3f3f46"
                                    stroke-width="1.5"
                                />
                                <line
                                    x1="184"
                                    y1="66"
                                    x2="220"
                                    y2="100"
                                    stroke="#3f3f46"
                                    stroke-width="1.5"
                                />
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
                                class="w-full h-full opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none"
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
                                <rect
                                    x="13"
                                    y="30"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="73"
                                    y="30"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="193"
                                    y="30"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="13"
                                    y="68"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="133"
                                    y="68"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="193"
                                    y="68"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="73"
                                    y="106"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="133"
                                    y="106"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(34,197,94,0.12)"
                                />
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
                                <rect
                                    x="133"
                                    y="30"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(239,68,68,0.12)"
                                />
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
                                <rect
                                    x="13"
                                    y="106"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(239,68,68,0.12)"
                                />
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
                                <rect
                                    x="83"
                                    y="56.5"
                                    width="30"
                                    height="3.5"
                                    rx="1.5"
                                    fill="rgba(255,208,0,0.3)"
                                />
                                <rect
                                    x="73"
                                    y="68"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(255,208,0,0.12)"
                                />
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
                                <rect
                                    x="193"
                                    y="106"
                                    width="32"
                                    height="7"
                                    rx="2"
                                    fill="rgba(255,208,0,0.12)"
                                />
                                <circle cx="197.5" cy="109.5" r="1.5" fill="#ffd000" />
                            </svg>
                            <!-- Static board thumbnail — scattered host/service objects, no tree structure -->
                            <svg
                                v-else
                                viewBox="0 0 256 128"
                                class="w-full h-full opacity-70 group-hover:opacity-90 transition-opacity duration-200 pointer-events-none"
                                font-family="system-ui,-apple-system,sans-serif"
                            >
                                <rect width="256" height="128" fill="#18181b" />
                                <!-- subtle grid -->
                                <line
                                    x1="64"
                                    y1="0"
                                    x2="64"
                                    y2="128"
                                    stroke="#27272a"
                                    stroke-width="0.5"
                                />
                                <line
                                    x1="128"
                                    y1="0"
                                    x2="128"
                                    y2="128"
                                    stroke="#27272a"
                                    stroke-width="0.5"
                                />
                                <line
                                    x1="192"
                                    y1="0"
                                    x2="192"
                                    y2="128"
                                    stroke="#27272a"
                                    stroke-width="0.5"
                                />
                                <line
                                    x1="0"
                                    y1="43"
                                    x2="256"
                                    y2="43"
                                    stroke="#27272a"
                                    stroke-width="0.5"
                                />
                                <line
                                    x1="0"
                                    y1="86"
                                    x2="256"
                                    y2="86"
                                    stroke="#27272a"
                                    stroke-width="0.5"
                                />
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
                                <rect
                                    x="18"
                                    y="48"
                                    width="36"
                                    height="7"
                                    rx="2"
                                    fill="rgba(0,0,0,0.55)"
                                />
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
                                <rect
                                    x="193"
                                    y="40"
                                    width="38"
                                    height="7"
                                    rx="2"
                                    fill="rgba(0,0,0,0.55)"
                                />
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
                                <rect
                                    x="98"
                                    y="77"
                                    width="40"
                                    height="7"
                                    rx="2"
                                    fill="rgba(0,0,0,0.55)"
                                />
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
                                <rect
                                    x="38"
                                    y="116"
                                    width="40"
                                    height="7"
                                    rx="2"
                                    fill="rgba(0,0,0,0.55)"
                                />
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
                                <rect
                                    x="170"
                                    y="98"
                                    width="40"
                                    height="7"
                                    rx="2"
                                    fill="rgba(0,0,0,0.55)"
                                />
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
                            <div
                                class="absolute flex items-center"
                                style="bottom: 8px; left: 8px; gap: 5px"
                            >
                                <span
                                    class="rounded-md font-medium backdrop-blur-sm"
                                    style="font-size: 11px; padding: 2px 6px"
                                    :class="
                                        map.view.type === 'worldmap'
                                            ? 'bg-cyan-500/20 text-cyan-300 ring-1 ring-cyan-500/30'
                                            : map.view.type === 'radar'
                                              ? 'bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30'
                                              : map.view.type === 'flow'
                                                ? 'bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/30'
                                                : 'bg-zinc-800/70 text-zinc-400 ring-1 ring-[var(--default-border-color)]/60'
                                    "
                                >
                                    {{ boardTypeLabel(map.view.type) }}
                                </span>
                            </div>
                            <div
                                class="absolute flex items-center"
                                style="top: 8px; right: 8px; gap: 5px"
                            >
                                <span
                                    v-if="map.show_in_lists === false && auth.isAdmin"
                                    class="text-[10px] rounded-md font-medium bg-zinc-800/80 text-zinc-500 ring-1 ring-[var(--default-border-color)]/60 backdrop-blur-sm"
                                    style="padding: 2px 5px"
                                    :title="t('home.hiddenBoard')"
                                >
                                    {{ t('home.hidden') }}
                                </span>
                                <span
                                    v-if="map.rotation_interval > 0"
                                    class="rounded-full font-medium bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30 backdrop-blur-sm"
                                    style="font-size: 11px; padding: 2px 6px"
                                    :title="
                                        t('home.rotationBadgeTitle', { n: map.rotation_interval })
                                    "
                                >
                                    ↻ {{ map.rotation_interval }}s
                                </span>
                            </div>
                        </div>

                        <!-- Card body -->
                        <div style="padding: 10px 12px">
                            <div
                                class="font-semibold text-[var(--text)] group-hover:text-white transition-colors truncate"
                                style="font-size: 13px; margin-bottom: 5px"
                                :title="map.alias || map.name"
                            >
                                {{ map.alias || map.name }}
                            </div>
                            <div class="flex items-center min-w-0" style="gap: 6px">
                                <svg
                                    class="shrink-0 text-zinc-600"
                                    style="width: 12px; height: 12px"
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
                                <span
                                    class="text-sm text-zinc-500 font-mono truncate"
                                    :title="map.connection_id"
                                    >{{ map.connection_id }}</span
                                >
                                <span class="text-zinc-700 shrink-0">·</span>
                                <span
                                    v-if="
                                        map.readonly ||
                                        ['flow', 'radar', 'worldmap'].includes(map.view.type)
                                    "
                                    class="text-sm text-zinc-500 shrink-0 italic"
                                    >{{ t('home.dynamicObjects') }}</span
                                >
                                <span v-else class="text-sm text-zinc-500 shrink-0">{{
                                    t('common.objects', map.object_count)
                                }}</span>
                            </div>
                        </div>
                    </router-link>

                    <div
                        v-if="auth.isAdmin"
                        class="flex items-center justify-end border-t border-[var(--border)] max-h-0 overflow-hidden group-hover:max-h-[36px] group-focus-within:max-h-[36px] transition-[max-height] duration-150"
                        style="gap: 2px; padding: 0 6px"
                    >
                        <button
                            v-if="!map.readonly"
                            class="p-1 rounded text-zinc-600 hover:text-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
                            :title="t('board.settingsTitle')"
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
                            class="p-1 rounded text-zinc-600 hover:text-amber-400 hover:bg-amber-500/10 transition-all"
                            :title="t('admin.cloneBoard')"
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
                            class="p-1 rounded text-zinc-600 hover:text-zinc-300 hover:bg-white/5 transition-all"
                            :title="t('admin.exportBoard')"
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
                            class="p-1 rounded text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                            :title="t('admin.deleteBoard', { name: map.alias || map.name })"
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
            </VueDraggable>
        </main>
    </div>
    <!-- Delete confirmation -->
    <Teleport to="body">
        <div v-if="confirmDelete" class="fixed inset-0 z-50 flex items-center justify-center">
            <div
                class="absolute inset-0 bg-black/60 backdrop-blur-sm"
                @click="confirmDelete = null"
            />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-xl"
                style="padding: 16px; width: 320px"
            >
                <h3 class="text-base font-bold text-[var(--text)]" style="margin-bottom: 4px">
                    {{ t('admin.deleteBoardTitle') }}
                </h3>
                <p class="text-sm text-zinc-400" style="margin-bottom: 16px">
                    {{
                        t('admin.deleteBoardConfirm', {
                            name: confirmDelete.alias || confirmDelete.name,
                        })
                    }}
                </p>
                <div class="flex justify-end gap-[8px]">
                    <CmkButton variant="secondary" @click="confirmDelete = null">
                        {{ t('common.cancel') }}
                    </CmkButton>
                    <CmkButton variant="danger" @click="doDelete">
                        {{ t('common.delete') }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>

    <!-- Clone Board Modal -->
    <Teleport to="body">
        <div v-if="confirmClone" class="fixed inset-0 z-50 flex items-center justify-center">
            <div
                class="absolute inset-0 bg-black/60 backdrop-blur-sm"
                @click="confirmClone = null"
            />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-xl"
                style="padding: 16px; width: 320px"
            >
                <div class="flex items-center justify-between" style="margin-bottom: 12px">
                    <h3 class="text-base font-bold text-[var(--text)]">
                        {{ t('admin.cloneBoard') }}
                    </h3>
                    <button
                        class="rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
                        style="padding: 5px"
                        @click="confirmClone = null"
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
                                d="M6 18L18 6M6 6l12 12"
                            />
                        </svg>
                    </button>
                </div>
                <div style="margin-bottom: 10px">
                    <label
                        class="block text-sm font-medium text-zinc-400"
                        style="margin-bottom: 4px"
                        >{{ t('admin.boardId') }}</label
                    >
                    <input
                        ref="cloneInputEl"
                        :value="cloneNewName"
                        class="w-full bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] font-mono"
                        style="padding: 5px 10px"
                        spellcheck="false"
                        @input="onCloneNameInput"
                        @keydown.enter="doClone"
                        @keydown.esc="confirmClone = null"
                        @focus="($event.target as HTMLInputElement).select()"
                    />
                </div>
                <div style="margin-bottom: 10px">
                    <label
                        class="block text-sm font-medium text-zinc-400"
                        style="margin-bottom: 4px"
                        >{{ t('admin.alias') }}</label
                    >
                    <input
                        v-model="cloneAlias"
                        class="w-full bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)]"
                        style="padding: 5px 10px"
                        spellcheck="false"
                    />
                </div>
                <p v-if="cloneError" class="text-sm text-red-400" style="margin-bottom: 8px">
                    {{ cloneError }}
                </p>
                <div class="flex justify-end gap-[8px] border-t border-[var(--border)] pt-[10px]">
                    <CmkButton variant="secondary" @click="confirmClone = null">
                        {{ t('common.cancel') }}
                    </CmkButton>
                    <CmkButton variant="primary" :disabled="!cloneNewName" @click="doClone">
                        {{ t('admin.cloneBoardAction') }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>

    <BoardSettingsModal
        v-if="settingsBoard"
        :board="settingsBoard"
        @close="settingsBoard = null"
        @updated="boardsStore.fetchBoards()"
    />

    <!-- Import FAB (admin only) -->
    <label
        v-if="auth.isAdmin"
        class="group fixed z-40 flex items-center rounded bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] ring-1 ring-[var(--border)] shadow-lg text-zinc-500 hover:text-zinc-300 transition-all cursor-pointer"
        style="bottom: 20px; right: 20px; gap: 6px; padding: 6px 12px"
        :title="t('admin.importBoard')"
    >
        <svg
            class="shrink-0"
            style="width: 14px; height: 14px"
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
        <span class="text-xs font-medium">{{ t('admin.importBoard') }}</span>
        <input
            type="file"
            accept=".json,.cfg,application/json"
            class="hidden"
            @change="importBoard"
        />
    </label>
    <Teleport to="body">
        <div v-if="importConflict" class="fixed inset-0 z-50 flex items-center justify-center">
            <div
                class="absolute inset-0 bg-black/60 backdrop-blur-sm"
                @click="importConflict = null"
            />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-xl"
                style="padding: 16px; width: 360px"
            >
                <h3 class="text-base font-bold text-[var(--text)]" style="margin-bottom: 4px">
                    {{ t('admin.importBoard') }}
                </h3>
                <p class="text-sm text-zinc-400" style="margin-bottom: 16px">
                    {{ t('admin.importOverwrite', { name: importConflict.name }) }}
                </p>
                <div class="flex justify-end gap-[8px]">
                    <CmkButton variant="secondary" @click="importConflict = null">
                        {{ t('common.cancel') }}
                    </CmkButton>
                    <CmkButton variant="warning" @click="confirmImportOverwrite">
                        {{ t('common.overwrite') }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>

    <CreateBoardModal v-if="showCreate" @close="showCreate = false" @created="onCreated" />
    <OnboardingTour
        v-if="showOnboarding && auth.user"
        :steps="tourSteps"
        :storage-key="`orbvis_onboarded_${auth.user.user_id}`"
        :show-create-board="auth.isAdmin"
        @close="showOnboarding = false"
        @create-board="
            showOnboarding = false;
            showCreate = true;
        "
    />
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { VueDraggable } from 'vue-draggable-plus';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { boardsApi } from '@/api/client';
import BoardSettingsModal from '@/components/board/BoardSettingsModal.vue';
import CreateBoardModal from '@/components/board/CreateBoardModal.vue';
import OnboardingTour from '@/components/OnboardingTour.vue';
import WorldMapThumbnail from '@/components/WorldMapThumbnail.vue';
import { useChangelog } from '@/composables/useChangelog';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import type { BoardConfig, BoardRead, WorldmapView } from '@/types/api';
import type { TourStep } from '@/types/tour';
import { sanitizeBoardName } from '@/utils/naming';

const { t } = useI18n();
const baseUrl = import.meta.env.BASE_URL;
const auth = useAuthStore();
const boardsStore = useBoardsStore();
const router = useRouter();
const { changelogVisible } = useChangelog();
const showCreate = ref(false);
const showOnboarding = ref(false);

const tourSteps = computed<TourStep[]>(() => {
    const all: TourStep[] = [
        { selector: null, title: t('onboarding.step1.title'), body: t('onboarding.step1.body') },
        {
            selector: '[data-tour="sidebar-nav"]',
            title: t('onboarding.step2.title'),
            body: auth.isAdmin ? t('onboarding.step2.bodyAdmin') : t('onboarding.step2.bodyUser'),
        },
        {
            selector: '[data-tour="boards-grid"]',
            title: t('onboarding.step3.title'),
            body: t('onboarding.step3.body'),
        },
        {
            selector: auth.isAdmin ? '[data-tour="new-board"]' : null,
            title: t('onboarding.step4.title'),
            body: auth.isAdmin ? t('onboarding.step4.bodyAdmin') : t('onboarding.step4.bodyUser'),
        },
    ];
    return auth.ssoActive || auth.isCheckmkDeployment
        ? all.filter((s) => s.selector !== '[data-tour="sidebar-nav"]')
        : all;
});
const confirmDelete = ref<{ name: string; alias: string } | null>(null);

function onCreated(name: string) {
    showCreate.value = false;
    router.push(`/boards/${name}`);
}

function deleteBoard(map: { name: string; alias: string }) {
    confirmDelete.value = map;
}

async function doDelete() {
    if (!confirmDelete.value) return;
    await boardsStore.deleteBoard(confirmDelete.value.name);
    confirmDelete.value = null;
}

const importConflict = ref<{ name: string; action: () => Promise<unknown> } | null>(null);

async function importBoard(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    try {
        if (file.name.toLowerCase().endsWith('.cfg')) {
            try {
                await boardsApi.importCfg(file, auth.accessToken!, false);
            } catch (e: unknown) {
                if (e instanceof Error && e.message.includes('already exists')) {
                    const name = file.name.replace(/\.cfg$/i, '');
                    importConflict.value = {
                        name,
                        action: () => boardsApi.importCfg(file, auth.accessToken!, true),
                    };
                    return;
                } else {
                    throw e;
                }
            }
        } else {
            const text = await file.text();
            const data: BoardConfig = JSON.parse(text);
            try {
                await boardsApi.importBoard(data, auth.accessToken!, false);
            } catch (e: unknown) {
                if (e instanceof Error && e.message.includes('already exists')) {
                    importConflict.value = {
                        name: data.name,
                        action: () => boardsApi.importBoard(data, auth.accessToken!, true),
                    };
                    return;
                } else {
                    throw e;
                }
            }
        }
        await boardsStore.fetchBoards();
    } catch (e: unknown) {
        alert(e instanceof Error ? e.message : t('admin.importFailed'));
    } finally {
        (event.target as HTMLInputElement).value = '';
    }
}

async function confirmImportOverwrite() {
    if (!importConflict.value) return;
    const action = importConflict.value.action;
    importConflict.value = null;
    try {
        await action();
        await boardsStore.fetchBoards();
    } catch (e: unknown) {
        alert(e instanceof Error ? e.message : t('admin.importFailed'));
    }
}

async function exportBoard(name: string) {
    await boardsApi.exportBoard(name, auth.accessToken!);
}

const confirmClone = ref<string | null>(null);
const cloneNewName = ref('');
const cloneAlias = ref('');
const cloneError = ref('');
const cloneInputEl = ref<HTMLInputElement | null>(null);

function cloneBoard(map: BoardRead) {
    confirmClone.value = map.name;
    cloneNewName.value = `${map.name}_copy`;
    cloneAlias.value = map.alias ? `${map.alias} (Copy)` : '';
    cloneError.value = '';
    nextTick(() => {
        cloneInputEl.value?.select();
    });
}

function onCloneNameInput(e: Event) {
    cloneNewName.value = sanitizeBoardName((e.target as HTMLInputElement).value);
}

async function doClone() {
    if (!confirmClone.value || !cloneNewName.value) return;
    try {
        await boardsApi.clone(
            confirmClone.value,
            { new_name: cloneNewName.value, alias: cloneAlias.value || undefined },
            auth.accessToken!,
        );
        await boardsStore.fetchBoards();
        confirmClone.value = null;
    } catch (e: unknown) {
        cloneError.value = e instanceof Error ? e.message : t('admin.cloneFailed');
    }
}

const settingsBoard = ref<BoardRead | null>(null);

function openSettings(map: BoardRead) {
    settingsBoard.value = map;
}

const searchQuery = ref('');

const visibleBoards = computed(() =>
    auth.isAdmin ? boardsStore.boards : boardsStore.boards.filter((m) => m.show_in_lists !== false),
);

const filteredBoards = computed(() => {
    const q = searchQuery.value.trim().toLowerCase();
    if (!q) return visibleBoards.value;
    return visibleBoards.value.filter(
        (m) => m.name.toLowerCase().includes(q) || m.alias.toLowerCase().includes(q),
    );
});

const isDragEnabled = computed(() => auth.isAdmin && !searchQuery.value.trim());

const draggableBoards = computed({
    get: () => (isDragEnabled.value ? boardsStore.boards : filteredBoards.value),
    set: (val) => {
        boardsStore.boards.splice(0, boardsStore.boards.length, ...val);
    },
});

async function onDragEnd() {
    const order = boardsStore.boards.map((b, i) => ({ name: b.name, sort_order: i }));
    try {
        await boardsApi.reorder(order, auth.accessToken!);
    } catch {
        await boardsStore.fetchBoards();
    }
}

const TYPE_LABELS: Record<string, string> = {
    static: 'Static',
    worldmap: 'Geo Board',
    flow: 'Flow Board',
    radar: 'Radar',
};
function boardTypeLabel(type: string) {
    return TYPE_LABELS[type] ?? type;
}

function worldmapLat(map: BoardRead) {
    return map.view.type === 'worldmap' ? (map.view as WorldmapView).lat : 51;
}
function worldmapLng(map: BoardRead) {
    return map.view.type === 'worldmap' ? (map.view as WorldmapView).lng : 10;
}
function worldmapZoom(map: BoardRead) {
    return map.view.type === 'worldmap' ? (map.view as WorldmapView).zoom : 5;
}

onMounted(async () => {
    await boardsStore.fetchBoards();
    if (!auth.user) return;
    const storageKey = `orbvis_onboarded_${auth.user.user_id}`;
    if (localStorage.getItem(storageKey)) return;
    // Existing operators who already have boards have outgrown the
    // onboarding tour; mark them as onboarded so an upgrade doesn't
    // ambush them with it.
    if (boardsStore.boards.length > 0) {
        localStorage.setItem(storageKey, '1');
        return;
    }
    if (changelogVisible.value) {
        const stop = watch(changelogVisible, (val) => {
            if (!val) {
                showOnboarding.value = true;
                stop();
            }
        });
    } else {
        showOnboarding.value = true;
    }
});
</script>
