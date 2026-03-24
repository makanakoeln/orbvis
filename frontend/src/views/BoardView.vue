<template>
  <div class="flex flex-col flex-1 overflow-hidden bg-[var(--bg)]">
    <!-- Slim map-specific topbar -->
    <div class="bg-[var(--bg-surface)] border-b border-[var(--border)] px-4 py-2 flex items-center justify-between shrink-0 z-30">
      <!-- Left: back link (Checkmk/SSO mode) + board name -->
      <div class="flex items-center gap-2.5 min-w-0">
        <router-link to="/"
          class="shrink-0 flex items-center gap-1 text-zinc-500 hover:text-zinc-300 transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          <span class="text-xs font-medium">{{ t('nav.overview') }}</span>
        </router-link>
        <span class="font-semibold text-[var(--text)] text-sm truncate">
          {{ boardConfig?.alias || route.params.name }}
        </span>
      </div>

      <div class="flex items-center gap-1.5 shrink-0">
        <!-- Connection status -->
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ring-1 transition-all"
          :class="statesStore.connected
            ? 'bg-green-500/8 ring-green-500/20 text-green-400'
            : 'bg-red-500/8 ring-red-500/20 text-red-400'">
          <span class="w-1.5 h-1.5 rounded-full inline-block"
            :class="statesStore.connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'" />
          {{ statesStore.connected ? t('board.live') : t('board.offline') }}
        </div>

        <!-- Notification bell -->
        <button @click="statesStore.toggleNotifications()"
          class="p-1.5 rounded-lg transition-all duration-150"
          :class="statesStore.notificationsEnabled
            ? 'text-amber-400 hover:bg-amber-500/10'
            : 'text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)]'"
          :title="statesStore.notificationsEnabled ? t('board.notificationsOn') : t('board.notificationsOff')">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
          </svg>
        </button>

        <!-- Read-only badge -->
        <span v-if="boardConfig?.readonly"
          class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold bg-zinc-700/50 text-zinc-400 ring-1 ring-zinc-700">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
          </svg>
          {{ t('board.readOnly') }}
        </span>

        <!-- Editing badge -->
        <span v-if="editor.editMode.value"
          class="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20">
          <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
          </svg>
          {{ t('board.editing') }}
        </span>

        <!-- Rotation countdown -->
        <button v-if="boardConfig && boardConfig.rotation_interval > 0 && rotationCountdown > 0"
          @click="toggleRotationPause"
          :title="rotationPaused ? t('board.rotationResume') : t('board.rotationPause')"
          class="flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ring-1 transition-all"
          :class="rotationPaused
            ? 'bg-zinc-700/50 ring-zinc-700 text-zinc-400'
            : 'bg-indigo-500/8 ring-indigo-500/20 text-indigo-400'">
          <svg class="w-3 h-3" :class="rotationPaused ? '' : 'animate-spin'" style="animation-duration:3s" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          {{ rotationCountdown }}{{ t('board.rotationSuffix') }}
        </button>

        <!-- Settings button (admin only) -->
        <button v-if="auth.isAdmin" @click="openSettings"
          class="p-1.5 rounded-lg text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all duration-150"
          :title="t('board.boardSettings')">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Map area + optional edit panel -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Worldmap -->
      <div v-if="isWorldmap" class="flex-1 overflow-hidden bg-[var(--bg)] relative" @click="closeWorldmapMenus">
        <div v-if="boardsStore.loading" class="absolute inset-0 flex items-center justify-center text-zinc-500 z-10 text-sm">
          {{ t('board.loadingBoard') }}
        </div>
        <div v-else-if="boardsStore.error" class="absolute inset-0 flex items-center justify-center text-red-400 z-10 text-sm">
          {{ boardsStore.error }}
        </div>
        <WorldMapCanvas
          v-else-if="boardConfig"
          ref="worldmapCanvasRef"
          :config="boardConfig"
          :states="statesStore.states"
          :edit-mode="editor.editMode.value"
          :placing="editor.placing.value"
          :selected-object-id="editor.selectedObjectId.value"
          @object-click="onObjectClick"
          @object-contextmenu="onObjectContextMenu"
          @object-contextmenu-view="onWorldmapContextMenuView"
          @object-hover="onWorldmapHover"
          @object-hover-leave="onWorldmapHoverLeave"
          @canvas-latlng-click="onCanvasLatLngClick"
          @latlng-drag-end="onLatLngDragEnd"
        />
        <!-- Fit all button -->
        <button
          v-if="boardConfig && boardConfig.objects.some(o => o.lat != null)"
          @click.stop="worldmapCanvasRef?.fitAll()"
          :title="t('board.fitAll')"
          class="absolute z-[1000] leaflet-control-fit-all bg-white hover:bg-zinc-100 text-zinc-700 border border-zinc-300 rounded px-1.5 py-1 text-xs font-medium shadow transition-colors"
          style="top: 80px; left: 10px;"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
          </svg>
        </button>
        <div v-else-if="!boardConfig" class="absolute inset-0 flex items-center justify-center text-zinc-600">{{ t('board.boardNotFound') }}</div>
      </div>

      <!-- Radar -->
      <RadarCanvas
        v-else-if="isRadar"
        :states="statesStore.states"
      />

      <!-- Automap -->
      <div v-else-if="isAutomap" class="flex-1 relative overflow-hidden">
        <AutomapCanvas
          v-if="boardConfig?.backend_id"
          :backend-id="boardConfig.backend_id"
          :service-layout="serviceLayout"
        />
        <div v-else class="flex items-center justify-center h-full text-zinc-500 text-sm">{{ t('board.noConnectionConfigured') }}</div>
      </div>

      <!-- Static map -->
      <div v-else class="flex-1 bg-[var(--bg)] relative" :class="boardConfig?.background_image ? 'overflow-hidden' : 'overflow-auto'"
        @click="onContainerClick">
        <div v-if="boardsStore.loading" class="flex items-center justify-center h-full text-zinc-500 text-sm">
          {{ t('board.loadingBoard') }}
        </div>
        <div v-else-if="boardsStore.error" class="flex items-center justify-center h-full text-red-400 text-sm">
          {{ boardsStore.error }}
        </div>
        <template v-else-if="boardConfig">
          <!-- Empty board hint -->
          <div v-if="boardConfig.objects.length === 0 && !editor.editMode.value"
            class="absolute inset-0 flex flex-col items-center justify-center gap-2 pointer-events-none select-none z-10">
            <svg class="w-10 h-10 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0H3" />
            </svg>
            <p class="text-sm text-zinc-600">
              <template v-if="auth.isAdmin">{{ t('board.emptyBoardAdmin') }}</template>
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
            :is-admin="auth.isAdmin"
            :icon-size-override="undefined"
            :snap-grid="editor.snapGrid.value"
            @object-drag-end="onObjectDragEnd"
            @object-click="onObjectClick"
            @object-contextmenu="onObjectContextMenu"
            @object-dblclick="onObjectDblclick"
            @object-delete="onObjectDelete"
            @object-duplicate="onObjectDuplicate"
            @line-drag-start="onLineDragStart"
            @canvas-click="onCanvasClick"
          />
        </template>
        <div v-else class="flex items-center justify-center h-full text-zinc-600">{{ t('board.boardNotFound') }}</div>
      </div>

    </div>

    <!-- FAB + Add Object panel + action bar (all bottom-right) -->
    <Teleport to="body">
      <div v-if="auth.isAdmin && boardConfig && !boardConfig.readonly && !isAutomap && !isRadar"
        class="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-3">

        <!-- Add Object panel — expands upward from FAB -->
        <Transition
          enter-from-class="opacity-0 scale-y-75 scale-x-95 translate-y-4"
          enter-active-class="transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] origin-bottom-right"
          leave-to-class="opacity-0 scale-y-75 scale-x-95 translate-y-4"
          leave-active-class="transition-all duration-200 ease-[cubic-bezier(0.4,0,1,1)] origin-bottom-right">
          <div v-if="editor.editMode.value"
            class="w-72 max-h-[calc(100vh-10rem)] flex flex-col overflow-hidden
                   bg-[var(--bg-surface)] backdrop-blur-xl
                   ring-1 ring-white/8 shadow-2xl shadow-black/60
                   rounded-2xl">
            <EditPanel
              :draft="editor.draft"
              :placing="editor.placing.value"
              :backend-id="boardConfig?.backend_id ?? ''"
              :snap-grid="editor.snapGrid.value"
              @start-placing="onStartPlacing()"
              @update:snap-grid="editor.snapGrid.value = $event"
              @close-edit-mode="editor.toggleEditMode()"
            />
          </div>
        </Transition>

        <!-- Object action bar (appears when object selected in edit mode) -->
        <Transition
          enter-from-class="opacity-0 translate-y-1 scale-95"
          enter-active-class="transition-all duration-150 ease-out"
          leave-to-class="opacity-0 translate-y-1 scale-95"
          leave-active-class="transition-all duration-100 ease-in">
          <div v-if="editor.editMode.value && editor.selectedObjectId.value && selectedObject"
            class="flex items-center gap-1 px-2 py-1.5 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl shadow-2xl shadow-black/40 backdrop-blur-md">
            <span class="text-[10px] font-bold text-zinc-500 capitalize px-1.5">{{ selectedObject.type }}</span>
            <div class="w-px h-4 bg-zinc-700 mx-0.5" />
            <button @click="openPropsModal(selectedObject!)" title="Edit properties"
              class="p-2 rounded-lg text-zinc-400 hover:text-indigo-300 hover:bg-indigo-500/10 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
              </svg>
            </button>
            <button @click="editor.duplicateSelected()" title="Duplicate"
              class="p-2 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700/60 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75" />
              </svg>
            </button>
            <button @click="deleteTargetObject = selectedObject" title="Delete"
              class="p-2 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
              </svg>
            </button>
          </div>
        </Transition>

        <!-- FAB: Edit toggle -->
        <button @click="onToggleEditMode"
          class="w-12 h-12 rounded-xl shadow-lg shadow-black/30 flex items-center justify-center transition-all duration-200 active:scale-95 ring-1"
          :class="editor.editMode.value
            ? 'bg-zinc-700 hover:bg-zinc-600 ring-zinc-600 text-zinc-200 hover:text-white'
            : 'bg-[var(--bg-surface)]/80 hover:bg-[var(--bg-surface)] ring-[var(--border)] text-zinc-500 hover:text-zinc-300'"
          :title="editor.editMode.value ? t('board.editing') : t('board.edit')">
          <svg v-if="!editor.editMode.value" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

      </div>
    </Teleport>

    <!-- Bottom row: Services toggle (Flow Board only) -->
    <Teleport to="body">
      <div v-if="isAutomap" class="fixed bottom-6 right-6 z-40">
        <div class="relative">
        <!-- Backdrop to close dropdown on outside click -->
        <div v-if="serviceLayoutOpen" class="fixed inset-0 z-0" @click="serviceLayoutOpen = false" />

        <button @click="serviceLayoutOpen = !serviceLayoutOpen"
          class="relative z-10 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium ring-1 shadow-lg shadow-black/30 transition-all duration-200"
          :class="serviceLayout !== 'off'
            ? 'bg-indigo-500/15 text-indigo-300 ring-indigo-500/40'
            : 'bg-[var(--bg-surface)]/80 text-zinc-400 ring-[var(--border)] hover:text-[var(--text)] hover:bg-[var(--bg-surface)]'">
          {{ t('board.services') }}
          <svg class="w-3 h-3 transition-transform duration-150" :class="serviceLayoutOpen ? 'rotate-180' : ''"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>

        <!-- Dropdown -->
        <Transition
          enter-from-class="opacity-0 scale-95 translate-y-1"
          enter-active-class="transition-all duration-150 ease-out origin-bottom-right"
          leave-to-class="opacity-0 scale-95 translate-y-1"
          leave-active-class="transition-all duration-100 ease-in origin-bottom-right">
          <div v-if="serviceLayoutOpen"
            class="absolute bottom-full mb-2 right-0 z-10 w-36 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl shadow-2xl shadow-black/50 overflow-hidden">
            <button v-for="opt in serviceLayoutOptions"
              :key="opt.value"
              @click="serviceLayout = opt.value; serviceLayoutOpen = false"
              class="w-full flex items-center justify-between px-3 py-2 text-xs transition-colors"
              :class="serviceLayout === opt.value
                ? 'text-indigo-300 bg-indigo-500/10'
                : 'text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)]'">
              {{ opt.label }}
              <svg v-if="serviceLayout === opt.value" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"
                stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </button>
          </div>
        </Transition>
        </div>
      </div>
    </Teleport>


    <!-- Delete confirmation -->
    <ConfirmDialog
      v-if="deleteTargetObject"
      :title="t('board.deleteObject')"
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
      :template="resolveTemplate(worldmapHover.object.hover_template, boardConfig?.hover_template, settingsStore.settings.hover_template)"
    />

    <!-- Worldmap ContextMenu -->
    <ContextMenu
      v-if="isWorldmap && worldmapCtxMenu.visible && worldmapCtxMenu.object"
      :object="worldmapCtxMenu.object"
      :state="statesStore.states[worldmapCtxMenu.object.id]"
      :x="worldmapCtxMenu.x"
      :y="worldmapCtxMenu.y"
      :checkmk-url="checkmkUrl"
      :show-edit="auth.isAdmin"
      :template="resolveTemplate(worldmapCtxMenu.object.context_template, boardConfig?.context_template, settingsStore.settings.context_template)"
      @close="closeWorldmapMenus"
      @edit="onWorldmapCtxEdit"
      @delete="onWorldmapCtxDelete"
    />

    <!-- Object Properties Modal -->
    <Teleport to="body">
      <ObjectPropertiesModal
        v-if="propsModalObject"
        :object="propsModalObject"
        :state="statesStore.states[propsModalObject.id]"
        :backend-id="boardConfig?.backend_id ?? ''"
        :map-type="boardConfig?.view.type"
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, reactive, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { connectionsApi } from '@/api/client'
import { useBoardsStore } from '@/stores/boards'
import { useStatesStore } from '@/stores/states'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import { useBoardEditor } from '@/composables/useBoardEditor'
import { resolveTemplate } from '@/utils/template'
import BoardCanvas from '@/components/board/BoardCanvas.vue'
import WorldMapCanvas from '@/components/board/WorldMapCanvas.vue'
import HoverMenu from '@/components/board/HoverMenu.vue'
import ContextMenu from '@/components/board/ContextMenu.vue'
import AutomapCanvas from '@/components/board/AutomapCanvas.vue'
import RadarCanvas from '@/components/board/RadarCanvas.vue'
import EditPanel from '@/components/board/EditPanel.vue'
import ObjectPropertiesModal from '@/components/board/ObjectPropertiesModal.vue'
import BoardSettingsModal from '@/components/board/BoardSettingsModal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import UserSettingsPanel from '@/components/UserSettingsPanel.vue'
import type { BoardObject } from '@/types/api'

type LineDragMode = 'move' | 'start' | 'end'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const boardsStore = useBoardsStore()
const statesStore = useStatesStore()
const connectionsStore = useConnectionsStore()
const settingsStore = useSettingsStore()

const boardName = computed(() => route.params.name as string)
const boardConfig = computed(() => boardsStore.currentBoard)
const boardConfigAsRead = computed<import('@/types/api').BoardRead | null>(() => {
  const cfg = boardsStore.currentBoard
  if (!cfg) return null
  return {
    name: cfg.name,
    alias: cfg.alias,
    background_image: cfg.background_image,
    icon_size: cfg.icon_size,
    backend_id: cfg.backend_id,
    view_type: cfg.view.type,
    view: cfg.view,
    object_count: cfg.objects.length,
    rotation_interval: cfg.rotation_interval,
    readonly: cfg.readonly,
    hover_template: cfg.hover_template,
    context_template: cfg.context_template,
  }
})
const canvasRef = ref<InstanceType<typeof BoardCanvas> | null>(null)
const worldmapCanvasRef = ref<InstanceType<typeof WorldMapCanvas> | null>(null)

const isWorldmap = computed(() => boardConfig.value?.view.type === 'worldmap')
const isAutomap  = computed(() => boardConfig.value?.view.type === 'automap')
const isRadar    = computed(() => boardConfig.value?.view.type === 'radar')

const checkmkUrl = computed(() => {
  const bid = boardConfig.value?.backend_id
  if (!bid) return null
  return connectionsStore.backends.find(b => b.id === bid)?.checkmk_url ?? null
})

async function reloadBoard() {
  await boardsStore.fetchBoard(boardName.value)
}

const editor = useBoardEditor(boardName, reloadBoard)

// ---- Object properties modal (right-click in view mode) ----

type AnchorRect = { left: number; top: number; right: number; bottom: number }

const propsModalObject = ref<BoardObject | null>(null)
const propsModalAnchor = ref<AnchorRect | null>(null)
const deleteTargetObject = ref<BoardObject | null>(null)

function openPropsModal(obj: BoardObject, anchor?: AnchorRect | null) {
  editor.selectObject(obj.id)
  propsModalAnchor.value = anchor ?? null
  propsModalObject.value = obj
}

function onObjectContextMenu(obj: BoardObject, anchor?: AnchorRect | null) {
  openPropsModal(obj, anchor)
}

function onObjectDblclick(obj: BoardObject) {
  openPropsModal(obj)
}

function onObjectDuplicate(obj: BoardObject) {
  editor.selectObject(obj.id)
  editor.duplicateSelected()
}

// ---- Worldmap hover & context menu ----

const worldmapHover = reactive({ visible: false, object: null as BoardObject | null, x: 0, y: 0 })
const worldmapCtxMenu = reactive({ visible: false, object: null as BoardObject | null, x: 0, y: 0 })

function onWorldmapHover(obj: BoardObject, event: MouseEvent) {
  worldmapHover.object = obj
  worldmapHover.x = event.pageX + 12
  worldmapHover.y = event.pageY + 12
  worldmapHover.visible = true
}

function onWorldmapHoverLeave() {
  worldmapHover.visible = false
}

function onWorldmapContextMenuView(obj: BoardObject, x: number, y: number) {
  editor.selectObject(obj.id)
  worldmapCtxMenu.object = obj
  worldmapCtxMenu.x = x
  worldmapCtxMenu.y = y
  worldmapCtxMenu.visible = true
}

function onWorldmapCtxEdit() {
  const obj = worldmapCtxMenu.object
  const x = worldmapCtxMenu.x
  const y = worldmapCtxMenu.y
  worldmapCtxMenu.visible = false
  if (obj) openPropsModal(obj, { left: x, top: y, right: x, bottom: y })
}

function onWorldmapCtxDelete() {
  if (boardConfig.value?.readonly) return
  const obj = worldmapCtxMenu.object
  worldmapCtxMenu.visible = false
  if (obj) {
    editor.selectObject(obj.id)
    editor.deleteSelected()
  }
}

function closeWorldmapMenus() {
  worldmapHover.visible = false
  worldmapCtxMenu.visible = false
}

function _closePropsModal() {
  propsModalObject.value = null
  propsModalAnchor.value = null
}

async function onPropsModalSave(updates: Record<string, unknown>) {
  if (propsModalObject.value)
    await editor.updateObjectProperties(propsModalObject.value.id, updates)
  _closePropsModal()
}

async function onPropsModalDelete() {
  const obj = propsModalObject.value
  _closePropsModal()
  if (obj) {
    editor.selectObject(obj.id)
    await editor.deleteSelected()
  }
}

function onToggleEditMode() {
  editor.toggleEditMode()
}

function onObjectDelete(obj: BoardObject) {
  deleteTargetObject.value = obj
}

async function confirmObjectDelete() {
  const obj = deleteTargetObject.value
  deleteTargetObject.value = null
  if (obj) {
    editor.selectObject(obj.id)
    await editor.deleteSelected()
  }
}

const selectedObject = computed<BoardObject | null>(() => {
  if (!editor.selectedObjectId.value || !boardConfig.value) return null
  return boardConfig.value.objects.find(o => o.id === editor.selectedObjectId.value) ?? null
})

// ---- Static map event handlers ----

async function onObjectDragEnd(id: string, x: number, y: number) {
  await editor.saveObjectPosition(id, x, y)
}

function onObjectClick(obj: BoardObject, _event?: MouseEvent) {
  editor.selectObject(obj.id)
}

async function onCanvasClick(event: MouseEvent) {
  if (!editor.editMode.value) return
  if (!editor.placing.value) { editor.selectObject(null); return }
  const pos = canvasRef.value?.getMapPosition(event)
  if (pos) {
    await editor.placeAt(pos.x, pos.y)
    if (selectedObject.value) openPropsModal(selectedObject.value)
  }
}

// Clicks on the scroll container outside the canvas bounds also trigger placing.
async function onContainerClick(event: MouseEvent) {
  if (!editor.editMode.value || !editor.placing.value) return
  const pos = canvasRef.value?.getMapPosition(event)
  if (pos) {
    await editor.placeAt(pos.x, pos.y)
    if (selectedObject.value) openPropsModal(selectedObject.value)
  }
}

function onLineDragStart(event: MouseEvent, obj: BoardObject, mode: LineDragMode) {
  const canvas = canvasRef.value?.getCanvasEl()
  if (canvas) editor.startLineDrag(event, obj, mode, canvas)
}

// ---- Worldmap event handlers ----

async function onStartPlacing() {
  const d = editor.draft
  const backendId = boardConfig.value?.backend_id
  if (boardConfig.value?.view.type === 'worldmap' && backendId && d.host_name) {
    try {
      const geo = await connectionsApi.hostGeo(backendId, d.host_name, auth.accessToken!)
      if (geo) {
        editor.startPlacing()
        await editor.placeAtLatLng(geo.lat, geo.lng)
        if (selectedObject.value) openPropsModal(selectedObject.value)
        return
      }
    } catch {}
  }
  editor.startPlacing()
}

async function onCanvasLatLngClick(lat: number, lng: number) {
  if (!editor.editMode.value || !editor.placing.value) return
  await editor.placeAtLatLng(lat, lng)
  if (selectedObject.value) openPropsModal(selectedObject.value)
}

function onLatLngDragEnd(id: string, lat: number, lng: number) {
  editor.moveObjectToLatLng(id, lat, lng)
}

async function onSaveProperties(updates: Record<string, unknown>) {
  if (editor.selectedObjectId.value)
    await editor.updateObjectProperties(editor.selectedObjectId.value, updates)
}

// ---- Map Settings ----

type ServiceLayout = 'off' | 'fan' | 'row' | 'orbit'
const serviceLayout = ref<ServiceLayout>('off')
const serviceLayoutOpen = ref(false)
const serviceLayoutOptions = computed(() => [
  { value: 'off' as ServiceLayout, label: t('board.serviceLayoutOff') },
  { value: 'fan' as ServiceLayout, label: t('board.serviceLayoutFan') },
  { value: 'orbit' as ServiceLayout, label: t('board.serviceLayoutOrbit') },
  { value: 'row' as ServiceLayout, label: t('board.serviceLayoutRow') },
])
const showSettings = ref(false)
const showUserSettings = ref(false)
const settingsWorldmapView = ref<{ lat: number; lng: number; zoom: number } | null>(null)

function openSettings() {
  if (!boardConfig.value) return
  const cfg = boardConfig.value
  if (cfg.view.type === 'worldmap' && worldmapCanvasRef.value) {
    settingsWorldmapView.value = worldmapCanvasRef.value.getView() ?? null
  } else {
    settingsWorldmapView.value = null
  }
  showSettings.value = true
}

async function onSettingsUpdated() {
  await reloadBoard()
  stopRotation()
  scheduleRotation(boardsStore.currentBoard?.rotation_interval ?? 0)
}

// ---- Rotation ----

let rotationTimer: ReturnType<typeof setInterval> | null = null
const rotationCountdown = ref(0)
const rotationPaused = ref(false)

function stopRotation() {
  if (rotationTimer !== null) {
    clearInterval(rotationTimer)
    rotationTimer = null
  }
  rotationCountdown.value = 0
}

async function goToNextBoard() {
  if (boardsStore.boards.length === 0) await boardsStore.fetchBoards()
  const pool = boardsStore.boards.filter(b => (b.rotation_interval ?? 0) > 0)
  if (pool.length < 2) return
  const idx = pool.findIndex(b => b.name === boardName.value)
  const next = pool[(idx + 1) % pool.length]
  router.push({ name: 'board', params: { name: next.name } })
}

function scheduleRotation(intervalSeconds: number) {
  stopRotation()
  rotationPaused.value = false
  if (intervalSeconds <= 0 || editor.editMode.value) return
  rotationCountdown.value = intervalSeconds
  rotationTimer = setInterval(() => {
    if (rotationPaused.value || editor.editMode.value) return
    rotationCountdown.value--
    if (rotationCountdown.value <= 0) {
      stopRotation()
      goToNextBoard()
    }
  }, 1000)
}

function toggleRotationPause() {
  rotationPaused.value = !rotationPaused.value
}

// Re-run whenever the map name changes (component is reused by Vue Router between maps).
// Reset all edit state so edit mode, selection, and unsaved changes from Map A
// don't carry over when navigating to Map B.
watchEffect(async () => {
  const name = boardName.value
  stopRotation()
  editor.resetForNewMap()

  await boardsStore.fetchBoard(name)
  statesStore.connectToMap(name, auth.accessToken ?? undefined)
  scheduleRotation(boardsStore.currentBoard?.rotation_interval ?? 0)
})

function onKeyDown(e: KeyboardEvent) {
  if (!editor.editMode.value) return
  const target = e.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') return
  if (e.key === 'Escape') {
    e.preventDefault()
    if (editor.placing.value) editor.cancelPlacing()
    else editor.selectObject(null)
  } else if ((e.key === 'Delete' || e.key === 'Backspace') && editor.selectedObjectId.value) {
    e.preventDefault()
    editor.deleteSelected()
  } else if (e.key === 'd' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    editor.duplicateSelected()
  }
}

onMounted(() => {
  if (auth.isAdmin) connectionsStore.fetchBackends()
  document.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  statesStore.disconnect()
  stopRotation()
  document.removeEventListener('keydown', onKeyDown)
})
</script>
