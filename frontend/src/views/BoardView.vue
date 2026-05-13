<template>
    <div class="flex flex-col flex-1 overflow-hidden bg-[var(--bg)]">
        <!-- Slim map-specific topbar -->
        <div
            v-if="!isKiosk"
            class="bg-[var(--bg-surface)] border-b border-[var(--border)] flex items-center justify-between shrink-0 z-30"
            style="padding: 0 var(--dimension-6); height: 36px"
        >
            <!-- Left: back link (Checkmk/SSO mode) + board name -->
            <div class="flex items-center gap-[10px] min-w-0">
                <router-link
                    to="/"
                    class="shrink-0 flex items-center gap-[4px] text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
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
                            d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"
                        />
                    </svg>
                    <span class="text-xs font-medium">{{ t('nav.overview') }}</span>
                </router-link>
                <button
                    v-if="drawerObject"
                    type="button"
                    class="font-semibold text-[var(--text-muted)] hover:text-[var(--text)] text-sm truncate transition-colors cursor-pointer"
                    :title="t('board.detailDrawer.close')"
                    @click="closeAnyDrawer"
                >
                    {{ boardConfig?.alias || route.params.name }}
                </button>
                <span v-else class="font-semibold text-[var(--text)] text-sm truncate">
                    {{ boardConfig?.alias || route.params.name }}
                </span>
                <template v-if="drawerObject">
                    <span class="text-[var(--text-muted)] text-sm shrink-0">›</span>
                    <span class="font-semibold text-[var(--text)] text-sm truncate">
                        {{ getBoardObjectName(drawerObject) }}
                    </span>
                </template>
            </div>

            <div
                class="flex items-center gap-[5px] shrink-0 transition-opacity"
                :class="drawerObject ? 'opacity-40 hover:opacity-100' : ''"
            >
                <!-- Flow problems pill (informational; layout switch lives in
                     the dedicated bottom-right toggle, no need for a CTA here) -->
                <span
                    v-if="isFlowmap && flowProblems.total > 0"
                    class="flex items-center rounded-full text-xs font-medium ring-1"
                    style="gap: 4px; padding: 2px 7px"
                    :class="
                        flowProblems.critical > 0
                            ? 'bg-[var(--color-light-red-50)]/10 ring-[var(--color-light-red-50)]/30 text-[var(--color-light-red-40)]'
                            : 'bg-[var(--color-warning)]/10 ring-[var(--color-warning)]/30 text-[var(--color-yellow-50)]'
                    "
                    :title="t('board.flow.issuesBanner', flowProblems)"
                >
                    <svg
                        style="width: 10px; height: 10px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                        />
                    </svg>
                    {{ t('board.flow.problemsPill', flowProblems) }}
                </span>

                <!-- Connection status -->
                <div
                    class="flex items-center rounded-full text-xs font-medium ring-1 transition-all"
                    style="gap: 4px; padding: 2px 7px"
                    :class="
                        statesStore.connected
                            ? 'bg-[var(--color-corporate-green-50)]/8 ring-[var(--color-corporate-green-50)]/20 text-[var(--color-corporate-green-50)]'
                            : 'bg-[var(--color-light-red-50)]/8 ring-[var(--color-light-red-50)]/20 text-[var(--color-light-red-40)]'
                    "
                >
                    <span
                        class="rounded-full inline-block"
                        style="width: 5px; height: 5px"
                        :class="
                            statesStore.connected
                                ? 'bg-[var(--color-corporate-green-50)] animate-pulse'
                                : 'bg-[var(--color-light-red-40)]'
                        "
                    />
                    {{ statesStore.connected ? t('board.live') : t('board.offline') }}
                </div>

                <!-- Notification bell -->
                <button
                    v-if="!auth.ssoActive && !auth.isCheckmkDeployment"
                    class="p-[5px] rounded-lg transition-all duration-150"
                    :class="
                        statesStore.notificationsEnabled
                            ? 'text-[var(--color-yellow-50)] hover:bg-[var(--color-warning)]/10'
                            : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]'
                    "
                    :title="
                        statesStore.notificationsEnabled
                            ? t('board.notificationsOn')
                            : t('board.notificationsOff')
                    "
                    @click="statesStore.toggleNotifications()"
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
                            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
                        />
                    </svg>
                </button>

                <!-- Read-only badge -->
                <span
                    v-if="boardConfig?.readonly"
                    class="flex items-center rounded-lg text-xs font-semibold bg-[var(--bg-hover)] text-[var(--text-muted)] ring-1 ring-[var(--default-border-color)]"
                    style="gap: 3px; padding: 2px 6px"
                >
                    <svg
                        style="width: 10px; height: 10px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
                        />
                    </svg>
                    {{ t('board.readOnly') }}
                </span>

                <!-- Editing badge -->
                <span
                    v-if="editor.editMode.value"
                    class="flex items-center rounded-lg text-xs font-semibold bg-[var(--color-warning)]/10 text-[var(--color-yellow-50)] ring-1 ring-[var(--color-warning)]/20"
                    style="gap: 3px; padding: 2px 6px"
                >
                    <svg
                        style="width: 10px; height: 10px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                        />
                    </svg>
                    {{ t('board.editing') }}
                </span>

                <!-- Rotation countdown -->
                <button
                    v-if="boardConfig && boardConfig.rotation_interval > 0 && rotationCountdown > 0"
                    :title="rotationPaused ? t('board.rotationResume') : t('board.rotationPause')"
                    class="flex items-center rounded-full text-xs font-medium ring-1 transition-all"
                    style="gap: 3px; padding: 2px 7px"
                    :class="
                        rotationPaused
                            ? 'bg-[var(--bg-hover)] ring-[var(--default-border-color)] text-[var(--text-muted)]'
                            : 'bg-[var(--color-corporate-green-50)]/8 ring-[var(--color-corporate-green-50)]/20 text-[var(--color-corporate-green-50)]'
                    "
                    @click="toggleRotationPause"
                >
                    <svg
                        style="width: 10px; height: 10px; animation-duration: 3s"
                        :class="rotationPaused ? '' : 'animate-spin'"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
                        />
                    </svg>
                    {{ rotationCountdown }}{{ t('board.rotationSuffix') }}
                </button>

                <!-- Fullscreen: browser fullscreen in standalone, new-tab kiosk in Checkmk -->
                <button
                    v-if="auth.ssoActive || auth.isCheckmkDeployment"
                    class="p-[5px] rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150"
                    :title="t('board.openInNewTab')"
                    @click="openKioskInNewTab"
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
                            d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                        />
                    </svg>
                </button>
                <button
                    v-else
                    class="p-[5px] rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150"
                    :title="t('board.fullscreen')"
                    @click="enterFullscreen"
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
                            d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                        />
                    </svg>
                </button>

                <!-- Settings button (admin only, not for read-only boards) -->
                <button
                    v-if="auth.isAdmin && !boardConfig?.readonly"
                    data-tour="board-settings"
                    class="p-[5px] rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150"
                    :title="t('board.boardSettings')"
                    @click="openSettings"
                >
                    <svg
                        style="width: 14px; height: 14px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="1.5"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
                        />
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                        />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Kiosk exit button (top-right, visible on hover) -->
        <button
            v-if="isKiosk"
            class="fixed z-50 p-[5px] rounded-lg bg-black/40 text-white/60 hover:text-white hover:bg-black/60 transition-colors duration-150"
            style="top: 12px; right: 12px"
            :title="t('board.exitFullscreen')"
            @click="exitFullscreen"
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
                    d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25"
                />
            </svg>
        </button>

        <!-- Map area + optional edit panel. Acts as the portal target for the
             shared CmkSlideIn-based detail drawer so the slide-in stays under
             the topbar. -->
        <div
            id="orbvis-board-shell"
            class="flex flex-1 overflow-hidden relative"
            data-tour="board-canvas"
        >
            <!-- Loading overlay (covers all board types) -->
            <div
                v-if="isLoading"
                class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--text-muted)] z-30 text-sm bg-[var(--bg)]"
            >
                <CmkLoading />
                <span>{{ t('board.loadingBoard') }}</span>
            </div>
            <!-- Worldmap -->
            <div
                v-if="isWorldmap"
                class="flex-1 overflow-hidden bg-[var(--bg)] relative"
                @click="closeWorldmapMenus"
            >
                <div
                    v-if="boardsStore.error"
                    class="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10 text-sm"
                >
                    <span class="text-[var(--color-light-red-40)]">{{ boardsStore.error }}</span>
                    <router-link
                        to="/"
                        class="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors text-xs"
                    >
                        {{ t('board.backToOverview') }}
                    </router-link>
                </div>
                <WorldMapCanvas
                    v-else-if="boardConfig"
                    ref="worldmapCanvasRef"
                    :config="boardConfig"
                    :states="statesStore.states"
                    :edit-mode="editor.editMode.value"
                    :placing="editor.placing.value"
                    :selected-object-id="editor.selectedObjectId.value"
                    :filter-needle="boardFilterNeedle"
                    @object-click="onObjectClick"
                    @object-contextmenu="onObjectContextMenu"
                    @object-contextmenu-view="onWorldmapContextMenuView"
                    @object-hover="onWorldmapHover"
                    @object-hover-leave="onWorldmapHoverLeave"
                    @canvas-latlng-click="onCanvasLatLngClick"
                    @latlng-drag-end="onLatLngDragEnd"
                    @latlng2-drag-end="onLatLng2DragEnd"
                />
                <BoardSearch
                    v-if="
                        boardConfig &&
                        boardConfig.objects.length > 0 &&
                        !editor.editMode.value &&
                        !boardsStore.error
                    "
                    v-model="boardFilterNeedle"
                />
                <!-- Fit all button -->
                <button
                    v-if="boardConfig && boardConfig.objects.some((o) => o.lat != null)"
                    :title="t('board.fitAll')"
                    class="absolute z-[1000] leaflet-control-fit-all bg-white hover:bg-zinc-100 text-zinc-700 border border-[var(--border)] rounded text-xs font-medium shadow transition-colors"
                    style="padding: 2px 4px; top: 80px; left: 10px"
                    @click.stop="worldmapCanvasRef?.fitAll()"
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
                            d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"
                        />
                    </svg>
                </button>
                <div
                    v-else-if="!boardConfig"
                    class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--text-muted)]"
                >
                    <span>{{ t('board.boardNotFound') }}</span>
                    <router-link
                        to="/"
                        class="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors text-xs"
                    >
                        {{ t('board.backToOverview') }}
                    </router-link>
                </div>
            </div>

            <!-- Radar -->
            <div v-else-if="isRadar" class="flex-1 relative overflow-hidden">
                <RadarCanvas
                    :states="statesStore.states"
                    :checkmk-url="checkmkUrl"
                    :readonly="isKiosk || boardConfig?.readonly"
                    :filter-needle="boardFilterNeedle"
                    @object-click="onObjectClick"
                />
                <BoardSearch
                    v-if="boardConfig && !editor.editMode.value"
                    v-model="boardFilterNeedle"
                />
            </div>

            <!-- Flowmap -->
            <div v-else-if="isFlowmap" class="flex-1 relative overflow-hidden">
                <FlowBoard
                    v-if="boardConfig?.connection_id"
                    ref="flowBoardRef"
                    :connection-id="boardConfig.connection_id"
                    :service-layout="serviceLayout"
                    :readonly="isKiosk || boardConfig?.readonly"
                    :click-action="boardConfig.click_action"
                    :checkmk-url="checkmkUrl"
                    :flow-view="boardConfig.view.type === 'flow' ? boardConfig.view : null"
                    @update:service-layout="onServiceLayoutChanged"
                    @update:problems="flowProblems = $event"
                    @drawer-object="flowDrawerObject = $event"
                    @positions-changed="onFlowPositionsChanged"
                />
                <div
                    v-else
                    class="flex items-center justify-center h-full text-[var(--text-muted)] text-sm"
                >
                    {{ t('board.noConnectionConfigured') }}
                </div>
            </div>

            <!-- Static map -->
            <div
                v-else
                class="flex-1 bg-[var(--bg)] relative overflow-auto"
                @click="onContainerClick"
            >
                <div
                    v-if="boardsStore.error"
                    class="flex flex-col items-center justify-center h-full gap-3 text-sm"
                >
                    <span class="text-[var(--color-light-red-40)]">{{ boardsStore.error }}</span>
                    <router-link
                        to="/"
                        class="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors text-xs"
                    >
                        {{ t('board.backToOverview') }}
                    </router-link>
                </div>
                <template v-else-if="boardConfig">
                    <BoardSearch
                        v-if="boardConfig.objects.length > 0 && !editor.editMode.value"
                        v-model="boardFilterNeedle"
                    />
                    <!-- Empty board hint -->
                    <div
                        v-if="boardConfig.objects.length === 0 && !editor.editMode.value"
                        class="absolute inset-0 flex flex-col items-center justify-center gap-2 pointer-events-none select-none z-10"
                    >
                        <svg
                            style="width: 32px; height: 32px"
                            class="text-[var(--text-muted)]"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="1.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0H3"
                            />
                        </svg>
                        <p class="text-sm text-[var(--text-muted)]">
                            <template v-if="auth.isAdmin">{{
                                t('board.emptyBoardAdmin')
                            }}</template>
                            <template v-else>{{ t('board.emptyBoard') }}</template>
                        </p>
                    </div>
                    <BoardCanvas
                        ref="canvasRef"
                        :config="boardConfig"
                        :states="statesStore.states"
                        :edit-mode="editor.editMode.value"
                        :placing="editor.placing.value"
                        :line-drag-positions="editor.lineDragPositions"
                        :selected-object-id="editor.selectedObjectId.value"
                        :checkmk-url="checkmkUrl"
                        :is-admin="auth.isAdmin && !isKiosk"
                        :icon-size-override="undefined"
                        :snap-grid="editor.snapGrid.value"
                        :filter-needle="boardFilterNeedle"
                        @object-drag-start="isDragging = true"
                        @object-drag-end="
                            (id, x, y) => {
                                isDragging = false;
                                onObjectDragEnd(id, x, y);
                            }
                        "
                        @object-click="onObjectClick"
                        @object-contextmenu="onObjectContextMenu"
                        @object-dblclick="onObjectDblclick"
                        @object-delete="onObjectDelete"
                        @object-duplicate="onObjectDuplicate"
                        @line-drag-start="onLineDragStart"
                        @canvas-click="onCanvasClick"
                        @graph-resize-end="onGraphResizeEnd"
                    />
                </template>
                <div
                    v-else
                    class="flex flex-col items-center justify-center h-full gap-3 text-[var(--text-muted)]"
                >
                    <span>{{ t('board.boardNotFound') }}</span>
                    <router-link
                        to="/"
                        class="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors text-xs"
                    >
                        {{ t('board.backToOverview') }}
                    </router-link>
                </div>
            </div>

            <!-- Shared detail drawer for static / worldmap / radar boards -->
            <DetailDrawer
                v-if="!isFlowmap"
                :object="detailDrawerObject"
                :state="detailDrawerState"
                :checkmk-url="checkmkUrl"
                :connection-id="boardConfig?.connection_id ?? null"
                :selectable-hosts="selectableHostNames"
                portal-target="#orbvis-board-shell"
                @close="closeDetail"
                @acknowledge="onDetailAck"
                @remove-ack="onDetailRemoveAck"
                @schedule-downtime="onDetailDowntime"
                @remove-downtime="onDetailRemoveDowntime"
                @force-check="onDetailForceCheck"
                @add-comment="onDetailAddComment"
                @enable-notifications="onDetailToggleNotifications(true)"
                @disable-notifications="onDetailToggleNotifications(false)"
                @select-host="onSelectHost"
                @bulk-acknowledge="onDetailBulkAcknowledge"
            />
        </div>

        <!-- Shared drawer-action modals -->
        <AckModal
            v-if="detailActions.ackModalObject.value && checkmkUrl"
            :object="detailActions.ackModalObject.value"
            :checkmk-url="checkmkUrl"
            @close="
                detailActions.ackModalObject.value = null;
                statesStore.refreshAfterCommand();
            "
        />
        <DowntimeModal
            v-if="detailActions.downtimeModalObject.value && checkmkUrl"
            :object="detailActions.downtimeModalObject.value"
            :checkmk-url="checkmkUrl"
            @close="
                detailActions.downtimeModalObject.value = null;
                statesStore.refreshAfterCommand();
            "
        />
        <CommentModal
            v-if="detailActions.commentModalObject.value && checkmkUrl"
            :object="detailActions.commentModalObject.value"
            :checkmk-url="checkmkUrl"
            @close="detailActions.commentModalObject.value = null"
        />
        <RemoveDowntimeModal
            v-if="detailActions.removeDowntimeModal.visible && checkmkUrl"
            :downtimes="detailActions.removeDowntimeModal.downtimes"
            :checkmk-url="checkmkUrl"
            :object-name="detailActions.removeDowntimeModal.objectName"
            @close="
                detailActions.removeDowntimeModal.visible = false;
                statesStore.refreshAfterCommand();
            "
        />

        <BulkAckModal
            v-if="bulkAckModal && checkmkUrl"
            :aggregation-id="bulkAckModal.aggregationId"
            :targets="bulkAckModal.targets"
            :checkmk-url="checkmkUrl"
            @close="
                bulkAckModal = null;
                statesStore.refreshAfterCommand();
            "
        />

        <!-- FAB + Add Object panel + action bar (all bottom-right). Hidden
             while the detail drawer is open so it doesn't overlap triage. -->
        <Teleport to="body">
            <div
                v-if="
                    auth.isAdmin &&
                    !isKiosk &&
                    boardConfig &&
                    !boardConfig.readonly &&
                    !isFlowmap &&
                    !isRadar &&
                    !drawerObject
                "
                class="fixed z-40 flex flex-col items-end gap-[10px]"
                style="bottom: 24px; right: 24px"
            >
                <!-- Add Object panel — expands upward from FAB -->
                <Transition
                    enter-from-class="opacity-0 scale-y-75 scale-x-95 translate-y-4"
                    enter-active-class="transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] origin-bottom-right"
                    leave-to-class="opacity-0 scale-y-75 scale-x-95 translate-y-4"
                    leave-active-class="transition-all duration-200 ease-[cubic-bezier(0.4,0,1,1)] origin-bottom-right"
                    @after-leave="editor.resetDraft()"
                >
                    <div
                        v-if="editor.editMode.value && !!editor.draft.type"
                        class="w-64 max-h-[calc(100vh-10rem)] flex flex-col bg-[var(--bg-surface)] backdrop-blur-xl ring-1 ring-white/8 shadow-2xl shadow-black/60 rounded-2xl"
                        data-tour="edit-panel"
                    >
                        <EditPanel
                            :draft="editor.draft"
                            :placing="editor.placing.value"
                            :connection-id="boardConfig?.connection_id ?? ''"
                            :snap-grid="editor.snapGrid.value"
                            @start-placing="onStartPlacing()"
                            @update:snap-grid="editor.snapGrid.value = $event"
                            @cancel-add="editor.resetDraft()"
                        />
                    </div>
                </Transition>

                <!-- Action bar moved out — now anchored to selected object via separate Teleport -->

                <!-- FAB: Add object (with type picker popover) -->
                <Transition
                    enter-from-class="opacity-0 scale-y-75 scale-x-95 translate-y-4"
                    enter-active-class="transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] origin-bottom-right"
                    leave-to-class="opacity-0 scale-y-75 scale-x-95 translate-y-4"
                    leave-active-class="transition-all duration-200 ease-[cubic-bezier(0.4,0,1,1)] origin-bottom-right"
                >
                    <div
                        v-if="editor.editMode.value && !editor.placing.value"
                        ref="addPickerWrapperRef"
                        class="relative"
                    >
                        <Transition
                            enter-from-class="opacity-0 translate-y-1 scale-95"
                            enter-active-class="transition-all duration-150 ease-out origin-bottom-right"
                            leave-to-class="opacity-0 translate-y-1 scale-95"
                            leave-active-class="transition-all duration-100 ease-in origin-bottom-right"
                        >
                            <div
                                v-if="addPickerOpen"
                                class="absolute right-0 mb-[8px] w-56 bg-[var(--bg-surface)] backdrop-blur-xl ring-1 ring-white/8 shadow-2xl shadow-black/60 rounded-xl overflow-hidden"
                                style="bottom: 100%"
                                role="menu"
                                :aria-label="t('boardSettings.selectType')"
                            >
                                <button
                                    v-for="opt in placeableTypeOptions"
                                    :key="opt.name"
                                    role="menuitem"
                                    class="w-full flex items-center gap-[10px] text-[13px] text-left text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                                    style="padding: 8px 12px"
                                    @click="chooseAddType(opt.name)"
                                >
                                    <svg
                                        class="text-[var(--text-muted)] shrink-0"
                                        style="width: 12px; height: 12px"
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
                                    <span>{{ opt.title }}</span>
                                </button>
                            </div>
                        </Transition>
                        <button
                            data-tour="add-object-fab"
                            class="rounded-xl shadow-lg shadow-black/30 flex items-center justify-center transition-all duration-200 active:scale-95 ring-1 bg-[var(--color-corporate-green-50)]/90 hover:bg-[var(--color-corporate-green-50)] ring-[var(--color-corporate-green-50)]/60 text-white"
                            style="width: 40px; height: 40px"
                            :title="t('boardSettings.addObject')"
                            :aria-expanded="addPickerOpen"
                            aria-haspopup="menu"
                            @click="onAddFabClick"
                        >
                            <svg
                                style="width: 18px; height: 18px"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M12 4.5v15m7.5-7.5h-15"
                                />
                            </svg>
                        </button>
                    </div>
                </Transition>

                <!-- FAB: Edit toggle -->
                <button
                    data-tour="edit-fab"
                    class="rounded-xl shadow-lg shadow-black/30 flex items-center justify-center transition-all duration-200 active:scale-95 ring-1"
                    style="width: 40px; height: 40px"
                    :class="
                        editor.editMode.value
                            ? 'bg-[var(--bg-input)] hover:bg-[var(--bg-hover)] ring-[var(--default-border-color)] text-[var(--text)] hover:text-white'
                            : 'bg-[var(--bg-surface)]/80 hover:bg-[var(--bg-surface)] ring-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text)]'
                    "
                    :title="editor.editMode.value ? t('board.editing') : t('board.edit')"
                    @click="onToggleEditMode"
                >
                    <svg
                        v-if="!editor.editMode.value"
                        style="width: 18px; height: 18px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="1.75"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                        />
                    </svg>
                    <svg
                        v-else
                        style="width: 18px; height: 18px"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="1.75"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                        />
                    </svg>
                </button>
            </div>
        </Teleport>

        <!-- Action bar anchored to selected object (edit mode) -->
        <Teleport to="body">
            <Transition
                enter-from-class="opacity-0 translate-y-1 scale-95"
                enter-active-class="transition-all duration-150 ease-out"
                leave-to-class="opacity-0 translate-y-1 scale-95"
                leave-active-class="transition-all duration-100 ease-in"
            >
                <div
                    v-if="
                        editor.editMode.value &&
                        editor.selectedObjectId.value &&
                        selectedObject &&
                        !isDragging &&
                        !propsModalObject &&
                        !editor.draft.type &&
                        actionBarStyle
                    "
                    class="fixed z-40 flex items-center bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl shadow-2xl shadow-black/40 backdrop-blur-md"
                    style="gap: 3px; padding: 4px 6px"
                    :style="actionBarStyle"
                >
                    <span
                        class="text-[10px] font-bold text-[var(--text-muted)] capitalize px-[4px]"
                        >{{ selectedObject!.type }}</span
                    >
                    <div
                        class="bg-[var(--border)]"
                        style="width: 1px; height: 14px; margin: 0 1px"
                    />
                    <button
                        title="Edit properties"
                        class="p-[7px] rounded-lg text-[var(--text-muted)] hover:text-[var(--color-corporate-green-40)] hover:bg-[var(--color-corporate-green-50)]/10 transition-all"
                        @click="openPropsModal(selectedObject!, selectedObjectAnchor)"
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
                                d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
                            />
                        </svg>
                    </button>
                    <button
                        title="Duplicate"
                        class="p-[7px] rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
                        @click="editor.duplicateSelected()"
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
                        title="Delete"
                        class="p-[7px] rounded-lg text-[var(--text-muted)] hover:text-[var(--color-light-red-40)] hover:bg-[var(--color-light-red-50)]/10 transition-all"
                        @click="deleteTargetObject = selectedObject"
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
            </Transition>
        </Teleport>

        <!-- Services-layout toggle (Flow Board only). Hidden during triage. -->
        <Teleport to="body">
            <div
                v-if="isFlowmap && !drawerObject"
                class="fixed z-40"
                style="bottom: 24px; right: 24px"
            >
                <div class="relative">
                    <!-- Backdrop to close dropdown on outside click -->
                    <div
                        v-if="serviceLayoutOpen"
                        class="fixed inset-0 z-0"
                        @click="serviceLayoutOpen = false"
                    />

                    <button
                        class="relative z-10 flex items-center rounded-xl text-xs font-medium ring-1 shadow-lg shadow-black/30 transition-all duration-200"
                        style="gap: 5px; padding: 5px 10px"
                        :class="
                            serviceLayout !== 'off'
                                ? 'bg-[var(--color-corporate-green-50)]/15 text-[var(--color-corporate-green-40)] ring-[var(--color-corporate-green-50)]/40'
                                : 'bg-[var(--bg-surface)]/80 text-[var(--text-muted)] ring-[var(--border)] hover:text-[var(--text)] hover:bg-[var(--bg-surface)]'
                        "
                        @click="serviceLayoutOpen = !serviceLayoutOpen"
                    >
                        {{ t('board.services') }}
                        <svg
                            style="width: 10px; height: 10px"
                            class="transition-transform duration-150"
                            :class="serviceLayoutOpen ? 'rotate-180' : ''"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                            />
                        </svg>
                    </button>

                    <!-- Dropdown -->
                    <Transition
                        enter-from-class="opacity-0 scale-95 translate-y-1"
                        enter-active-class="transition-all duration-150 ease-out origin-bottom-right"
                        leave-to-class="opacity-0 scale-95 translate-y-1"
                        leave-active-class="transition-all duration-100 ease-in origin-bottom-right"
                    >
                        <div
                            v-if="serviceLayoutOpen"
                            class="absolute bottom-full right-0 z-10 w-[120px] bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl shadow-2xl shadow-black/50 overflow-hidden"
                            style="margin-bottom: 6px"
                        >
                            <button
                                v-for="opt in serviceLayoutOptions"
                                :key="opt.value"
                                class="w-full flex items-center justify-between text-xs transition-colors"
                                style="padding: 5px 10px"
                                :class="
                                    serviceLayout === opt.value
                                        ? 'text-[var(--color-corporate-green-40)] bg-[var(--color-corporate-green-50)]/10'
                                        : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)]'
                                "
                                @click="
                                    onServiceLayoutChanged(opt.value);
                                    serviceLayoutOpen = false;
                                "
                            >
                                {{ opt.label }}
                                <svg
                                    v-if="serviceLayout === opt.value"
                                    style="width: 12px; height: 12px"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2.5"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M4.5 12.75l6 6 9-13.5"
                                    />
                                </svg>
                            </button>
                        </div>
                    </Transition>
                </div>
            </div>
        </Teleport>

        <!-- Delete confirmation -->
        <OrbConfirmDialog
            :open="!!deleteTargetObject"
            :title="deleteDialogTitle"
            :message="t('board.cannotBeUndone')"
            :confirm-label="t('common.delete')"
            @confirm="confirmObjectDelete"
            @cancel="deleteTargetObject = null"
        />

        <!-- Worldmap HoverMenu -->
        <HoverMenu
            v-if="isWorldmap && worldmapHover.visible && worldmapHover.object"
            :object="worldmapHover.object"
            :state="statesStore.states[worldmapHover.object.id]"
            :x="worldmapHover.x"
            :y="worldmapHover.y"
            :connection-id="boardConfig?.connection_id"
            :template="
                resolveTemplate(
                    worldmapHover.object.hover_template,
                    boardConfig?.hover_template,
                    settingsStore.settings.hover_template,
                )
            "
        />

        <!-- Worldmap ContextMenu -->
        <ContextMenu
            v-if="isWorldmap && worldmapCtxMenu.visible && worldmapCtxMenu.object"
            :object="worldmapCtxMenu.object"
            :state="statesStore.states[worldmapCtxMenu.object.id]"
            :x="worldmapCtxMenu.x"
            :y="worldmapCtxMenu.y"
            :checkmk-url="checkmkUrl"
            :show-edit="auth.isAdmin && !editor.editMode.value"
            :template="
                resolveTemplate(
                    worldmapCtxMenu.object.context_template,
                    boardConfig?.context_template,
                    settingsStore.settings.context_template,
                )
            "
            @close="closeWorldmapMenus"
            @edit="onWorldmapCtxEdit"
            @delete="onWorldmapCtxDelete"
            @duplicate="onWorldmapCtxDuplicate"
            @acknowledge="onWorldmapCtxAck"
            @remove-ack="onWorldmapCtxRemoveAck"
            @schedule-downtime="onWorldmapCtxDowntime"
            @remove-downtime="onWorldmapCtxRemoveDowntime"
            @force-check="onWorldmapCtxForceCheck"
            @add-comment="onWorldmapCtxAddComment"
            @enable-notifications="onWorldmapCtxToggleNotifications(true)"
            @disable-notifications="onWorldmapCtxToggleNotifications(false)"
        />
        <AckModal
            v-if="worldmapAckModal && checkmkUrl"
            :object="worldmapAckModal"
            :checkmk-url="checkmkUrl"
            @close="
                worldmapAckModal = null;
                statesStore.refreshAfterCommand();
            "
        />
        <DowntimeModal
            v-if="worldmapDowntimeModal && checkmkUrl"
            :object="worldmapDowntimeModal"
            :checkmk-url="checkmkUrl"
            @close="
                worldmapDowntimeModal = null;
                statesStore.refreshAfterCommand();
            "
        />
        <CommentModal
            v-if="worldmapCommentModal && checkmkUrl"
            :object="worldmapCommentModal"
            :checkmk-url="checkmkUrl"
            @close="worldmapCommentModal = null"
        />
        <RemoveDowntimeModal
            v-if="worldmapRemoveDowntimeModal.visible && checkmkUrl"
            :downtimes="worldmapRemoveDowntimeModal.downtimes"
            :checkmk-url="checkmkUrl"
            :object-name="worldmapRemoveDowntimeModal.objectName"
            @close="
                worldmapRemoveDowntimeModal.visible = false;
                statesStore.refreshAfterCommand();
            "
        />

        <!-- Object Properties Modal -->
        <Teleport to="body">
            <ObjectPropertiesModal
                v-if="propsModalObject"
                :object="propsModalObject"
                :state="statesStore.states[propsModalObject.id]"
                :connection-id="boardConfig?.connection_id ?? ''"
                :map-type="boardConfig?.view.type"
                :board-icon-size="boardConfig?.icon_size ?? settingsStore.settings.icon_size"
                :checkmk-url="checkmkUrl"
                :anchor-rect="propsModalAnchor"
                @close="_closePropsModal()"
                @save="onPropsModalSave"
                @delete="onPropsModalDelete"
            />
        </Teleport>

        <!-- Map Settings Modal -->
        <BoardSettingsModal
            v-if="showSettings && boardConfigAsRead"
            :board="boardConfigAsRead"
            :worldmap-view="settingsWorldmapView"
            @close="showSettings = false"
            @updated="onSettingsUpdated"
        />

        <OnboardingTour
            v-if="showBoardTour && auth.user"
            :steps="boardTourSteps"
            :storage-key="`orbvis_board_toured_${auth.user.user_id}`"
            @close="showBoardTour = false"
            @step-click="onBoardTourStepClick"
            @step-back="onBoardTourStepBack"
        />
    </div>
</template>

<script setup lang="ts">
import { onClickOutside, useElementBounding, useEventListener } from '@vueuse/core';
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch, watchEffect } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';

import { boardsApi, cmkApi, connectionsApi } from '@/api/client';
import AckModal from '@/components/board/AckModal.vue';
import BoardCanvas from '@/components/board/BoardCanvas.vue';
import BoardSearch from '@/components/board/BoardSearch.vue';
import BoardSettingsModal from '@/components/board/BoardSettingsModal.vue';
import BulkAckModal from '@/components/board/BulkAckModal.vue';
import CommentModal from '@/components/board/CommentModal.vue';
import ContextMenu from '@/components/board/ContextMenu.vue';
import DetailDrawer from '@/components/board/DetailDrawer.vue';
import DowntimeModal from '@/components/board/DowntimeModal.vue';
import EditPanel from '@/components/board/EditPanel.vue';
import FlowBoard from '@/components/board/FlowBoard.vue';
import HoverMenu from '@/components/board/HoverMenu.vue';
import ObjectPropertiesModal from '@/components/board/ObjectPropertiesModal.vue';
import RadarCanvas from '@/components/board/RadarCanvas.vue';
import RemoveDowntimeModal from '@/components/board/RemoveDowntimeModal.vue';
import WorldMapCanvas from '@/components/board/WorldMapCanvas.vue';
import OnboardingTour from '@/components/OnboardingTour.vue';
import OrbConfirmDialog from '@/components/OrbConfirmDialog.vue';
import { useBoardEditor } from '@/composables/useBoardEditor';
import { useObjectActions } from '@/composables/useObjectActions';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import { useConnectionsStore } from '@/stores/connections';
import { useSettingsStore } from '@/stores/settings';
import { useStatesStore } from '@/stores/states';
import type {
    BoardObject,
    BulkAckTarget,
    DowntimeEntry,
    ObjectType,
    ServiceLayout,
} from '@/types/api';
import type { TourStep } from '@/types/tour';
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation';
import { placeableObjectTypes } from '@/utils/dropdownOptions';
import { getBoardObjectIdentifier, getBoardObjectName, getObjectTypeLabel } from '@/utils/naming';
import { resolveTemplate } from '@/utils/template';
import CmkLoading from '@/vendor/cmk/components/CmkLoading.vue';

type LineDragMode = 'move' | 'start' | 'end';

const { t } = useI18n();
const toast = useToast();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const boardsStore = useBoardsStore();
const statesStore = useStatesStore();
const connectionsStore = useConnectionsStore();
const settingsStore = useSettingsStore();

const boardName = computed(() => route.params.name as string);
const isKiosk = computed(() => !!route.meta.kiosk);

function openKioskInNewTab() {
    const url = router.resolve({ name: 'board-kiosk', params: { name: boardName.value } }).href;
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.rel = 'noreferrer';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function enterFullscreen() {
    router.push({ name: 'board-kiosk', params: { name: boardName.value } });
    document.documentElement.requestFullscreen().catch(() => {});
}

function exitFullscreen() {
    router.push({ name: 'board', params: { name: boardName.value } });
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
}

// ─── Board tour ───────────────────────────────────────────────────────────────

const showBoardTour = ref(false);

const boardTourSteps = computed<TourStep[]>(() => {
    const base: TourStep[] = [
        {
            selector: null,
            title: t('onboarding.boardStep1.title'),
            body: t('onboarding.boardStep1.body'),
        },
        {
            selector: '[data-tour="board-canvas"]',
            title: t('onboarding.boardStep2.title'),
            body: t('onboarding.boardStep2.body'),
        },
    ];
    if (!auth.isAdmin) return base;
    return [
        ...base,
        {
            selector: '[data-tour="board-settings"]',
            title: t('onboarding.boardStep3.title'),
            body: t('onboarding.boardStep3.body'),
        },
        {
            selector: '[data-tour="edit-fab"]',
            title: t('onboarding.boardStep4.title'),
            body: t('onboarding.boardStep4.body'),
        },
        {
            selector: '[data-tour="edit-panel"]',
            title: t('onboarding.boardStep5.title'),
            body: t('onboarding.boardStep5.body'),
        },
    ];
});

function onBoardTourStepClick(step: number) {
    // Step 4 = FAB — ensure edit mode is ON so EditPanel renders for step 5
    if (auth.isAdmin && step === 4 && !editor.editMode.value) {
        editor.toggleEditMode();
    }
}
function onBoardTourStepBack(step: number) {
    // Leaving step 5 backwards — ensure edit mode is OFF
    if (auth.isAdmin && step === 5 && editor.editMode.value) {
        editor.toggleEditMode();
    }
}
const boardConfig = computed(() => boardsStore.currentBoard);
const boardConfigAsRead = computed<import('@/types/api').BoardRead | null>(() => {
    const cfg = boardsStore.currentBoard;
    if (!cfg) return null;
    return {
        name: cfg.name,
        alias: cfg.alias,
        background_image: cfg.background_image,
        icon_size: cfg.icon_size,
        connection_id: cfg.connection_id,
        view_type: cfg.view.type,
        view: cfg.view,
        object_count: cfg.objects.length,
        rotation_interval: cfg.rotation_interval,
        sort_order: cfg.sort_order,
        click_action: cfg.click_action,
        readonly: cfg.readonly,
        hover_template: cfg.hover_template,
        context_template: cfg.context_template,
    };
});
const canvasRef = ref<InstanceType<typeof BoardCanvas> | null>(null);
const worldmapCanvasRef = ref<InstanceType<typeof WorldMapCanvas> | null>(null);

const isWorldmap = computed(() => boardConfig.value?.view.type === 'worldmap');
const isFlowmap = computed(() => boardConfig.value?.view.type === 'flow');
const isRadar = computed(() => boardConfig.value?.view.type === 'radar');

// Top-right search bar shared by static / worldmap / radar boards.
// FlowBoard ships its own search because it filters d3 nodes directly.
const boardFilterNeedle = ref('');
watch(boardName, () => {
    boardFilterNeedle.value = '';
});
const isLoading = computed(
    () => boardsStore.loading || (statesStore.initialLoad && !boardsStore.error),
);

const checkmkUrl = computed(() => {
    const bid = boardConfig.value?.connection_id;
    const connUrl = bid
        ? (connectionsStore.connections.find((b) => b.id === bid)?.checkmk_url ?? null)
        : null;
    return connUrl ?? settingsStore.settings.checkmk_url ?? null;
});

async function reloadBoard() {
    await boardsStore.fetchBoard(boardName.value);
}

const editor = useBoardEditor(boardName, reloadBoard);

// ---- Add-object type picker (anchored above the "+" FAB) ----

const addPickerOpen = ref(false);
const addPickerWrapperRef = ref<HTMLElement | null>(null);
const isDragging = ref(false);

// ---- Action bar position anchored to selected object ----
const selectedObjectEl = ref<HTMLElement | null>(null);
const selectedRect = useElementBounding(selectedObjectEl);

watch(
    () => editor.selectedObjectId.value,
    async (id) => {
        await nextTick();
        selectedObjectEl.value = id
            ? (document.querySelector(`[data-object-id="${CSS.escape(id)}"]`) as HTMLElement | null)
            : null;
    },
    { immediate: true },
);

useEventListener(window, 'resize', () => selectedRect.update());

const actionBarStyle = computed(() => {
    const top = selectedRect.top.value;
    const left = selectedRect.left.value;
    const width = selectedRect.width.value;
    const bottom = selectedRect.bottom.value;
    if (!selectedObjectEl.value || width === 0) return null;
    const barHeightApprox = 36;
    const gap = 8;
    const aboveTop = top - barHeightApprox - gap;
    const useAbove = aboveTop >= 8;
    return {
        top: `${useAbove ? aboveTop : bottom + gap}px`,
        left: `${left + width / 2}px`,
        transform: 'translateX(-50%)',
    };
});

const selectedObjectAnchor = computed<AnchorRect | null>(() => {
    if (!selectedObjectEl.value || selectedRect.width.value === 0) return null;
    return {
        left: selectedRect.left.value,
        top: selectedRect.top.value,
        right: selectedRect.right.value,
        bottom: selectedRect.bottom.value,
    };
});

const placeableTypeOptions = computed(() => placeableObjectTypes(t));

function chooseAddType(type: ObjectType) {
    editor.draft.type = type;
    addPickerOpen.value = false;
}

function onAddFabClick() {
    if (editor.draft.type) {
        editor.resetDraft();
        addPickerOpen.value = true;
    } else {
        addPickerOpen.value = !addPickerOpen.value;
    }
}

onClickOutside(addPickerWrapperRef, () => {
    addPickerOpen.value = false;
});

watch(
    () => editor.editMode.value,
    (on) => {
        if (!on) addPickerOpen.value = false;
    },
);

// ---- Object properties modal (right-click in view mode) ----

type AnchorRect = { left: number; top: number; right: number; bottom: number };

const propsModalObject = ref<BoardObject | null>(null);
const propsModalAnchor = ref<AnchorRect | null>(null);
const deleteTargetObject = ref<BoardObject | null>(null);

const deleteDialogTitle = computed(() => {
    const obj = deleteTargetObject.value;
    if (!obj) return t('board.deleteObject');
    const type = getObjectTypeLabel(obj);
    const name = obj.label?.text || getBoardObjectIdentifier(obj);
    if (!name || name === obj.id) return t('board.deleteObjectTitleUnnamed', { type });
    return t('board.deleteObjectTitle', { type, name });
});

function openPropsModal(obj: BoardObject, anchor?: AnchorRect | null) {
    editor.selectObject(obj.id);
    propsModalAnchor.value = anchor ?? null;
    propsModalObject.value = obj;
}

function onObjectContextMenu(obj: BoardObject, anchor?: AnchorRect | null) {
    openPropsModal(obj, anchor);
}

function onObjectDblclick(obj: BoardObject) {
    if (!editor.editMode.value) return;
    const el = document.querySelector(
        `[data-object-id="${CSS.escape(obj.id)}"]`,
    ) as HTMLElement | null;
    const r = el?.getBoundingClientRect();
    const anchor =
        r && (r.width > 0 || r.height > 0)
            ? { left: r.left, top: r.top, right: r.right, bottom: r.bottom }
            : null;
    openPropsModal(obj, anchor);
}

function onObjectDuplicate(obj: BoardObject) {
    editor.selectObject(obj.id);
    editor.duplicateSelected();
}

// ---- Worldmap hover & context menu ----

const worldmapHover = reactive({ visible: false, object: null as BoardObject | null, x: 0, y: 0 });
const worldmapCtxMenu = reactive({
    visible: false,
    object: null as BoardObject | null,
    x: 0,
    y: 0,
});

function onWorldmapHover(obj: BoardObject, event: MouseEvent) {
    worldmapHover.object = obj;
    worldmapHover.x = event.pageX + 12;
    worldmapHover.y = event.pageY + 12;
    worldmapHover.visible = true;
}

function onWorldmapHoverLeave() {
    worldmapHover.visible = false;
}

function onWorldmapContextMenuView(obj: BoardObject, x: number, y: number) {
    editor.selectObject(obj.id);
    worldmapCtxMenu.object = obj;
    worldmapCtxMenu.x = x;
    worldmapCtxMenu.y = y;
    worldmapCtxMenu.visible = true;
}

function onWorldmapCtxEdit() {
    const obj = worldmapCtxMenu.object;
    const x = worldmapCtxMenu.x;
    const y = worldmapCtxMenu.y;
    worldmapCtxMenu.visible = false;
    if (obj) openPropsModal(obj, { left: x, top: y, right: x, bottom: y });
}

function onWorldmapCtxDelete() {
    if (boardConfig.value?.readonly) return;
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (obj) {
        editor.selectObject(obj.id);
        editor.deleteSelected();
    }
}

function onWorldmapCtxDuplicate() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (obj) {
        editor.selectObject(obj.id);
        editor.duplicateSelected();
    }
}

const worldmapAckModal = ref<BoardObject | null>(null);
const worldmapDowntimeModal = ref<BoardObject | null>(null);
const worldmapCommentModal = ref<BoardObject | null>(null);
const worldmapRemoveDowntimeModal = reactive<{
    visible: boolean;
    downtimes: DowntimeEntry[];
    objectName: string;
}>({
    visible: false,
    downtimes: [],
    objectName: '',
});

function onWorldmapCtxDowntime() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (obj) worldmapDowntimeModal.value = obj;
}

async function onWorldmapCtxRemoveDowntime() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (!obj || !checkmkUrl.value) return;
    let downtimes: DowntimeEntry[];
    try {
        if (obj.type === 'service' && obj.host_name && obj.service_description) {
            downtimes = await cmkApi.listDowntimesService(
                checkmkUrl.value,
                obj.host_name,
                obj.service_description,
            );
        } else if (obj.host_name) {
            downtimes = await cmkApi.listDowntimesHost(checkmkUrl.value, obj.host_name);
        } else {
            return;
        }
    } catch {
        toast.error(t('contextMenu.removeDowntimeFailed'));
        return;
    }
    if (downtimes.length === 0) {
        toast.error(t('contextMenu.noDowntimesFound'));
        return;
    }
    if (downtimes.length === 1) {
        await doWorldmapRemoveDowntime(downtimes[0]);
        return;
    }
    worldmapRemoveDowntimeModal.downtimes = downtimes;
    worldmapRemoveDowntimeModal.objectName = obj.host_name ?? '';
    worldmapRemoveDowntimeModal.visible = true;
}

async function doWorldmapRemoveDowntime(dt: DowntimeEntry) {
    if (!checkmkUrl.value) return;
    try {
        await cmkApi.removeDowntimeById(checkmkUrl.value, dt.id, dt.site_id);
        toast.success(t('contextMenu.removeDowntimeSuccess'));
        statesStore.refreshAfterCommand();
    } catch {
        toast.error(t('contextMenu.removeDowntimeFailed'));
    }
}

function onWorldmapCtxAck() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (obj) worldmapAckModal.value = obj;
}

function onWorldmapCtxAddComment() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (obj) worldmapCommentModal.value = obj;
}

async function onWorldmapCtxRemoveAck() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (!obj || !checkmkUrl.value) return;
    try {
        if (obj.type === 'service' && obj.host_name && obj.service_description) {
            await cmkApi.removeAcknowledgementService(
                checkmkUrl.value,
                obj.host_name,
                obj.service_description,
            );
        } else if (obj.host_name) {
            await cmkApi.removeAcknowledgementHost(checkmkUrl.value, obj.host_name);
        }
    } catch (err) {
        const detail = err instanceof Error ? err.message : '';
        toast.error(
            detail
                ? `${t('contextMenu.removeAckFailed')}: ${detail}`
                : t('contextMenu.removeAckFailed'),
        );
    }
}

async function onWorldmapCtxToggleNotifications(enable: boolean) {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (!obj || !checkmkUrl.value) return;
    try {
        if (obj.type === 'service' && obj.host_name && obj.service_description) {
            await (enable ? cmkApi.enableNotificationsService : cmkApi.disableNotificationsService)(
                checkmkUrl.value,
                obj.host_name,
                obj.service_description,
            );
        } else if (obj.host_name) {
            await (enable ? cmkApi.enableNotificationsHost : cmkApi.disableNotificationsHost)(
                checkmkUrl.value,
                obj.host_name,
            );
        }
    } catch {
        toast.error(t('contextMenu.toggleNotificationsFailed'));
    }
}

async function onWorldmapCtxForceCheck() {
    const obj = worldmapCtxMenu.object;
    worldmapCtxMenu.visible = false;
    if (!obj || !checkmkUrl.value) return;
    try {
        if (obj.type === 'service' && obj.host_name && obj.service_description) {
            await cmkApi.forceCheckService(
                checkmkUrl.value,
                obj.host_name,
                obj.service_description,
            );
        } else if (obj.host_name) {
            await cmkApi.forceCheckHost(checkmkUrl.value, obj.host_name);
        }
    } catch {
        toast.error(t('contextMenu.forceCheckFailed'));
    }
}

function closeWorldmapMenus() {
    worldmapHover.visible = false;
    worldmapCtxMenu.visible = false;
}

function _closePropsModal() {
    propsModalObject.value = null;
    propsModalAnchor.value = null;
}

async function onPropsModalSave(updates: Record<string, unknown>) {
    if (propsModalObject.value)
        await editor.updateObjectProperties(propsModalObject.value.id, updates);
    _closePropsModal();
}

async function onPropsModalDelete() {
    const obj = propsModalObject.value;
    _closePropsModal();
    if (obj) {
        editor.selectObject(obj.id);
        await editor.deleteSelected();
    }
}

function onToggleEditMode() {
    editor.toggleEditMode();
}

function onObjectDelete(obj: BoardObject) {
    deleteTargetObject.value = obj;
}

async function confirmObjectDelete() {
    const obj = deleteTargetObject.value;
    deleteTargetObject.value = null;
    if (obj) {
        editor.selectObject(obj.id);
        await editor.deleteSelected();
    }
}

const selectedObject = computed<BoardObject | null>(() => {
    if (!editor.selectedObjectId.value || !boardConfig.value) return null;
    return boardConfig.value.objects.find((o) => o.id === editor.selectedObjectId.value) ?? null;
});

// ---- Detail drawer (shared across static / worldmap / radar boards) ----

const detailDrawerObject = ref<BoardObject | null>(null);
const detailDrawerState = computed(() =>
    detailDrawerObject.value ? statesStore.states[detailDrawerObject.value.id] : undefined,
);
const detailActions = useObjectActions(
    () => checkmkUrl.value,
    () => {},
);

function openDetail(obj: BoardObject) {
    // A line is a visual relation between two endpoints, but in monitoring
    // terms it represents either the host or the host's service (whichever
    // is configured). Drawer logic keys off `type` to fetch state and
    // render the right tabs, so expose the line as its underlying
    // host/service for the drawer's purposes.
    if (obj.type === 'line' && obj.host_name) {
        detailDrawerObject.value = {
            ...obj,
            type: obj.service_description ? 'service' : 'host',
        };
    } else {
        detailDrawerObject.value = obj;
    }
    worldmapHover.visible = false;
    worldmapCtxMenu.visible = false;
}

// All host BoardObjects on this board, keyed by hostname so the Drawer's
// topology section can decide whether a parent/child entry can highlight on
// the board (vs. just linking to Checkmk).
const selectableHostNames = computed(() =>
    (boardConfig.value?.objects ?? [])
        .filter((o) => o.type === 'host' && o.host_name)
        .map((o) => o.host_name as string),
);

function onSelectHost(hostName: string, serviceDescription?: string | null) {
    // Prefer a real board-object so toolbar actions (ack/downtime) bind to the
    // operator's curated entry. Fall back to a synthesised object so members
    // discovered via the hostgroup drawer (often not placed on the board)
    // still open in the same slidein — the parent state cycle lifts onto the
    // standard host/service-detail-fetch watch automatically.
    const objs = boardConfig.value?.objects ?? [];
    const real = objs.find((o) => {
        if (o.type === 'service') {
            return (
                o.host_name === hostName &&
                (serviceDescription ? o.service_description === serviceDescription : true)
            );
        }
        return o.type === 'host' && o.host_name === hostName;
    });
    if (real) {
        detailDrawerObject.value = real;
        return;
    }
    detailDrawerObject.value = {
        id: serviceDescription
            ? `transient:${hostName};${serviceDescription}`
            : `transient:${hostName}`,
        type: serviceDescription ? 'service' : 'host',
        host_name: hostName,
        service_description: serviceDescription ?? undefined,
        x: 0,
        y: 0,
        z: 0,
        url_target: '_blank',
    };
}

function closeDetail() {
    detailDrawerObject.value = null;
}

function onDetailAck() {
    detailActions.handlers.acknowledge(detailDrawerObject.value);
}
function onDetailRemoveAck() {
    void detailActions.handlers.removeAck(detailDrawerObject.value);
}
function onDetailDowntime() {
    detailActions.handlers.scheduleDowntime(detailDrawerObject.value);
}
function onDetailRemoveDowntime() {
    void detailActions.handlers.removeDowntime(detailDrawerObject.value);
}
function onDetailForceCheck() {
    void detailActions.handlers.forceCheck(detailDrawerObject.value);
}
function onDetailAddComment() {
    detailActions.handlers.addComment(detailDrawerObject.value);
}
function onDetailToggleNotifications(enable: boolean) {
    void detailActions.handlers.toggleNotifications(detailDrawerObject.value, enable);
}

/**
 * Bulk-acknowledge contributing leaves of a BI aggregation. Opens the
 * BulkAckModal — that previews the targets, lets the operator review/edit
 * the comment (pre-filled with "Bulk-ack: <aggregation_id>" so audit logs
 * trace back to the originating aggregation), and runs the per-leaf ack
 * loop with progress feedback. The previous "fire immediately on click"
 * version was risky for misclicks since N acks have no atomic undo.
 */
function onDetailBulkAcknowledge(targets: BulkAckTarget[]) {
    if (!checkmkUrl.value || !targets.length) return;
    const obj = detailDrawerObject.value;
    const aggregationId = obj?.aggregation_id ?? obj?.id ?? 'unknown';
    bulkAckModal.value = { aggregationId, targets };
}

const bulkAckModal = ref<{
    aggregationId: string;
    targets: BulkAckTarget[];
} | null>(null);

// ---- Static map event handlers ----

async function onObjectDragEnd(id: string, x: number, y: number) {
    await editor.saveObjectPosition(id, x, y);
}

function onObjectClick(obj: BoardObject, event?: MouseEvent) {
    if (editor.editMode.value) {
        editor.selectObject(obj.id);
        return;
    }
    if (boardConfig.value?.click_action === 'none') return;
    if (obj.url) {
        openUrl(obj.url, obj.url_target || '_blank');
        return;
    }
    if (obj.type === 'map' && obj.map_name) {
        void router.push({ name: 'board', params: { name: obj.map_name } });
        return;
    }
    if (event && (event.ctrlKey || event.metaKey)) {
        const cmkUrl = buildCheckmkUrl(obj, checkmkUrl.value);
        if (cmkUrl) openUrl(cmkUrl, '_blank');
        return;
    }
    // Decorative objects without a monitored target have nothing to show in
    // the slide-in. Click is a no-op rather than an empty drawer.
    if (!objectHasMonitoringTarget(obj)) return;
    openDetail(obj);
}

function objectHasMonitoringTarget(obj: BoardObject): boolean {
    switch (obj.type) {
        case 'host':
        case 'service':
        case 'line':
            return Boolean(obj.host_name);
        case 'hostgroup':
        case 'servicegroup':
            return Boolean(obj.group_name);
        case 'aggregation':
            return Boolean(obj.aggregation_id);
        default:
            return false;
    }
}

async function onCanvasClick(event: MouseEvent) {
    if (!editor.editMode.value) return;
    if (!editor.placing.value) {
        editor.selectObject(null);
        return;
    }
    const pos = canvasRef.value?.getMapPosition(event);
    if (pos) {
        await editor.placeAt(pos.x, pos.y);
        if (selectedObject.value) openPropsModal(selectedObject.value);
    }
}

// Clicks on the scroll container outside the canvas bounds also trigger placing.
async function onContainerClick(event: MouseEvent) {
    if (!editor.editMode.value || !editor.placing.value) return;
    const pos = canvasRef.value?.getMapPosition(event);
    if (pos) {
        await editor.placeAt(pos.x, pos.y);
        if (selectedObject.value) openPropsModal(selectedObject.value);
    }
}

function onLineDragStart(event: MouseEvent, obj: BoardObject, mode: LineDragMode) {
    const canvas = canvasRef.value?.getCanvasEl();
    if (canvas) editor.startLineDrag(event, obj, mode, canvas);
}

async function onGraphResizeEnd(id: string, width: number, height: number) {
    const obj = boardConfig.value?.objects.find((o) => o.id === id);
    if (!obj) return;
    if (obj.type === 'textbox') {
        obj.textbox_width = width;
        obj.textbox_height = height;
        await editor.updateObjectProperties(id, { textbox_width: width, textbox_height: height });
        return;
    }
    obj.graph_width = width;
    obj.graph_height = height;
    await editor.updateObjectProperties(id, { graph_width: width, graph_height: height });
}

// ---- Worldmap event handlers ----

async function onStartPlacing() {
    const d = editor.draft;
    const connectionId = boardConfig.value?.connection_id;
    if (boardConfig.value?.view.type === 'worldmap' && connectionId && d.host_name) {
        try {
            const geo = await connectionsApi.hostGeo(connectionId, d.host_name, auth.accessToken!);
            if (geo) {
                editor.startPlacing();
                await editor.placeAtLatLng(geo.lat, geo.lng);
                if (selectedObject.value) openPropsModal(selectedObject.value);
                return;
            }
        } catch {}
    }
    editor.startPlacing();
}

async function onCanvasLatLngClick(lat: number, lng: number) {
    if (!editor.editMode.value || !editor.placing.value) return;
    await editor.placeAtLatLng(lat, lng);
    if (selectedObject.value) openPropsModal(selectedObject.value);
}

function onLatLngDragEnd(id: string, lat: number, lng: number) {
    editor.moveObjectToLatLng(id, lat, lng);
}

function onLatLng2DragEnd(id: string, lat: number, lng: number) {
    editor.moveObjectToLatLng2(id, lat, lng);
}

// ---- Map Settings ----

const SERVICE_LAYOUT_DEFAULT: ServiceLayout = 'off';
const serviceLayout = ref<ServiceLayout>(SERVICE_LAYOUT_DEFAULT);
const serviceLayoutOpen = ref(false);

type FlowProblems = {
    critical: number;
    warning: number;
    hostsWithProblems: number;
    total: number;
};
const FLOW_PROBLEMS_DEFAULT: FlowProblems = {
    critical: 0,
    warning: 0,
    hostsWithProblems: 0,
    total: 0,
};
const flowProblems = ref<FlowProblems>({ ...FLOW_PROBLEMS_DEFAULT });
const flowDrawerObject = ref<BoardObject | null>(null);
const flowBoardRef = ref<{ closeDetail: () => void } | null>(null);
const drawerObject = computed<BoardObject | null>(
    () => detailDrawerObject.value ?? flowDrawerObject.value,
);
function closeAnyDrawer(): void {
    if (detailDrawerObject.value) closeDetail();
    if (flowDrawerObject.value) flowBoardRef.value?.closeDetail();
}

async function persistFlowView(patch: Record<string, unknown>): Promise<void> {
    const cfg = boardConfig.value;
    if (!cfg || cfg.readonly) return;
    if (cfg.view.type !== 'flow') return;
    const token = auth.accessToken;
    if (!token) return;
    const newView = { ...cfg.view, ...patch };
    cfg.view = newView;
    try {
        await boardsApi.update(cfg.name, { view: newView }, token);
    } catch (err) {
        // Layout edits are low-stakes — log and let the next change retry.
        console.warn('Failed to persist flow view:', err);
    }
}

function onFlowPositionsChanged(positions: Record<string, { x: number; y: number }>): void {
    void persistFlowView({ positions });
}

function onServiceLayoutChanged(layout: ServiceLayout): void {
    serviceLayout.value = layout;
    void persistFlowView({ service_layout: layout });
}

// Hydrate the local serviceLayout ref from the persisted view whenever the
// board config swaps. The watch on boardName below clears the ref before the
// new board arrives, so this fires once the new boardConfig is in place.
watch(
    () => boardConfig.value?.view,
    (view) => {
        if (view?.type === 'flow' && view.service_layout) {
            serviceLayout.value = view.service_layout;
        }
    },
    { immediate: true },
);

watch(boardName, () => {
    serviceLayout.value = SERVICE_LAYOUT_DEFAULT;
    serviceLayoutOpen.value = false;
    flowProblems.value = { ...FLOW_PROBLEMS_DEFAULT };
});
const serviceLayoutOptions = computed(() => [
    { value: 'off' as ServiceLayout, label: t('board.serviceLayoutOff') },
    { value: 'donut' as ServiceLayout, label: t('board.serviceLayoutDonut') },
    { value: 'fan' as ServiceLayout, label: t('board.serviceLayoutFan') },
    { value: 'orbit' as ServiceLayout, label: t('board.serviceLayoutOrbit') },
    { value: 'row' as ServiceLayout, label: t('board.serviceLayoutRow') },
]);
const showSettings = ref(false);
const settingsWorldmapView = ref<{ lat: number; lng: number; zoom: number } | null>(null);

function openSettings() {
    if (!boardConfig.value) return;
    const cfg = boardConfig.value;
    if (cfg.view.type === 'worldmap' && worldmapCanvasRef.value) {
        settingsWorldmapView.value = worldmapCanvasRef.value.getView() ?? null;
    } else {
        settingsWorldmapView.value = null;
    }
    showSettings.value = true;
}

async function onSettingsUpdated() {
    await reloadBoard();
    stopRotation();
    scheduleRotation(boardsStore.currentBoard?.rotation_interval ?? 0);
}

// ---- Rotation ----

let rotationTimer: ReturnType<typeof setInterval> | null = null;
const rotationCountdown = ref(0);
const rotationPaused = ref(false);

function stopRotation() {
    if (rotationTimer !== null) {
        clearInterval(rotationTimer);
        rotationTimer = null;
    }
    rotationCountdown.value = 0;
}

async function goToNextBoard() {
    if (boardsStore.boards.length === 0) await boardsStore.fetchBoards();
    const pool = boardsStore.boards.filter((b) => (b.rotation_interval ?? 0) > 0);
    if (pool.length < 2) return;
    const idx = pool.findIndex((b) => b.name === boardName.value);
    const next = pool[(idx + 1) % pool.length];
    router.push({ name: 'board', params: { name: next.name } });
}

function scheduleRotation(intervalSeconds: number) {
    stopRotation();
    rotationPaused.value = false;
    if (intervalSeconds <= 0 || editor.editMode.value) return;
    rotationCountdown.value = intervalSeconds;
    rotationTimer = setInterval(() => {
        if (rotationPaused.value || editor.editMode.value) return;
        rotationCountdown.value--;
        if (rotationCountdown.value <= 0) {
            stopRotation();
            goToNextBoard();
        }
    }, 1000);
}

function toggleRotationPause() {
    rotationPaused.value = !rotationPaused.value;
}

// Re-run whenever the map name changes (component is reused by Vue Router between maps).
// Reset all edit state so edit mode, selection, and unsaved changes from Map A
// don't carry over when navigating to Map B.
watchEffect(async () => {
    const name = boardName.value;
    stopRotation();
    editor.resetForNewMap();

    await boardsStore.fetchBoard(name);
    statesStore.connectToMap(name, auth.accessToken ?? undefined);
    scheduleRotation(boardsStore.currentBoard?.rotation_interval ?? 0);

    const cfg = boardsStore.currentBoard;
    if (
        auth.user &&
        cfg &&
        !cfg.readonly &&
        !localStorage.getItem(`orbvis_board_toured_${auth.user.user_id}`)
    ) {
        showBoardTour.value = true;
    }
});

function onKeyDown(e: KeyboardEvent) {
    if (!editor.editMode.value) return;
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT')
        return;
    if (e.key === 'Escape') {
        e.preventDefault();
        if (addPickerOpen.value) addPickerOpen.value = false;
        else if (editor.placing.value) editor.cancelPlacing();
        else editor.selectObject(null);
    } else if ((e.key === 'Delete' || e.key === 'Backspace') && editor.selectedObjectId.value) {
        e.preventDefault();
        editor.deleteSelected();
    } else if (e.key === 'd' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        editor.duplicateSelected();
    }
}

function onFullscreenChange() {
    if (!document.fullscreenElement && isKiosk.value) {
        router.push({ name: 'board', params: { name: boardName.value } });
    }
}

onMounted(() => {
    if (auth.isAdmin) connectionsStore.fetchConnections();
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('fullscreenchange', onFullscreenChange);
});

onUnmounted(() => {
    statesStore.disconnect();
    stopRotation();
    document.removeEventListener('keydown', onKeyDown);
    document.removeEventListener('fullscreenchange', onFullscreenChange);
});
</script>
