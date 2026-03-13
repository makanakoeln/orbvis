<template>
  <div class="flex flex-col flex-1 overflow-hidden bg-[var(--bg)]">
    <!-- Slim map-specific topbar -->
    <div class="bg-[var(--bg-surface)] border-b border-[var(--border)] px-4 py-2 flex items-center justify-between shrink-0 z-30">
      <!-- Left: back link (Checkmk/SSO mode) + board name -->
      <div class="flex items-center gap-2.5 min-w-0">
        <router-link v-if="auth.ssoActive" to="/"
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

        <!-- Settings button (admin only) -->
        <button v-if="auth.isAdmin && !boardConfig?.readonly" @click="openSettings"
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
        <div v-else class="absolute inset-0 flex items-center justify-center text-zinc-600">{{ t('board.boardNotFound') }}</div>
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
        <BoardCanvas
          v-else-if="boardConfig"
          ref="canvasRef"
          :config="boardConfig"
          :states="statesStore.states"
          :edit-mode="editor.editMode.value"
          :placing="editor.placing.value"
          :line-drag-positions="editor.lineDragPositions"
          :selected-object-id="editor.selectedObjectId.value"
          :checkmk-url="checkmkUrl"
          :is-admin="auth.isAdmin"
          :icon-size-override="showSettings ? settingsForm.icon_size : undefined"
          :snap-grid="editor.snapGrid.value"
          @object-drag-end="onObjectDragEnd"
          @object-click="onObjectClick"
          @object-contextmenu="onObjectContextMenu"
          @object-delete="onObjectDelete"
          @line-drag-start="onLineDragStart"
          @canvas-click="onCanvasClick"
        />
        <div v-else class="flex items-center justify-center h-full text-zinc-600">{{ t('board.boardNotFound') }}</div>
      </div>

    </div>

    <!-- FAB + Add Object panel + action bar (all bottom-right) -->
    <Teleport to="body">
      <div v-if="auth.isAdmin && !boardConfig?.readonly && !isAutomap && !isRadar && !boardConfig?.name.startsWith('demo-')"
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
              @start-placing="editor.startPlacing()"
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
          <div v-if="auth.isAdmin && !boardConfig?.readonly && editor.editMode.value && editor.selectedObjectId.value && selectedObject"
            class="flex items-center gap-1 px-2 py-1.5 bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl shadow-2xl shadow-black/40 backdrop-blur-md">
            <span class="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-1.5">{{ selectedObject.type }}</span>
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

        <!-- Bottom row: Services toggle + FAB -->
        <div class="flex items-center gap-2">
          <!-- Services layout picker (Flow Board only) -->
          <div v-if="isAutomap" class="relative">
            <!-- Backdrop to close dropdown on outside click -->
            <div v-if="serviceLayoutOpen" class="fixed inset-0 z-0" @click="serviceLayoutOpen = false" />

            <button @click="serviceLayoutOpen = !serviceLayoutOpen"
              class="relative z-10 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium ring-1 shadow-lg shadow-black/30 transition-all duration-200"
              :class="serviceLayout !== 'off'
                ? 'bg-indigo-500/15 text-indigo-300 ring-indigo-500/40'
                : 'bg-[var(--bg-surface)]/80 text-zinc-400 ring-[var(--border)] hover:text-[var(--text)] hover:bg-[var(--bg-surface)]'">
              Services
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
                <button v-for="opt in ([['off', 'Aus'], ['fan', 'Fächer'], ['orbit', 'Orbit'], ['row', 'Reihe']] as const)"
                  :key="opt[0]"
                  @click="serviceLayout = opt[0]; serviceLayoutOpen = false"
                  class="w-full flex items-center justify-between px-3 py-2 text-xs transition-colors"
                  :class="serviceLayout === opt[0]
                    ? 'text-indigo-300 bg-indigo-500/10'
                    : 'text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)]'">
                  {{ opt[1] }}
                  <svg v-if="serviceLayout === opt[0]" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"
                    stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                </button>
              </div>
            </Transition>
          </div>

          <!-- FAB: Edit toggle (admin only) -->
          <button v-if="auth.isAdmin && !boardConfig?.readonly" @click="onToggleEditMode"
            class="w-12 h-12 rounded-xl shadow-lg shadow-black/30 flex items-center justify-center transition-all duration-200 active:scale-95 ring-1"
            :class="editor.editMode.value
              ? 'bg-zinc-700 hover:bg-zinc-600 ring-zinc-600 text-zinc-300 hover:text-white'
              : 'bg-[var(--bg-surface)]/80 hover:bg-[var(--bg-surface)] ring-[var(--border)] text-zinc-500 hover:text-zinc-300'"
            :title="editor.editMode.value ? t('board.editing') : t('boardSettings.addObject')">
            <svg v-if="!editor.editMode.value" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
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
    <Teleport to="body">
      <div v-if="showSettings" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showSettings = false" />
        <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-[34rem] max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('board.settingsTitle') }}</h3>
            <button @click="showSettings = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="saveSettings" class="space-y-4">
            <!-- Alias -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.displayName') }}</label>
              <input v-model="settingsForm.alias"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <!-- Backend + Icon size -->
            <div class="grid grid-cols-[1fr_6rem] gap-3">
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.connection') }}</label>
                <div class="relative">
                  <select v-model="settingsForm.backend_id"
                    class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                    <option v-for="b in connectionsStore.backends" :key="b.id" :value="b.id">
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
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.iconSize') }}</label>
                <NumberInput v-model="settingsForm.icon_size" min="12" max="96" class="w-full" />
              </div>
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.rotationInterval') }}</label>
                <div class="flex items-center gap-2">
                  <NumberInput v-model="settingsForm.rotation_interval" min="0" max="3600" class="w-full" />
                  <span class="text-xs text-zinc-500 shrink-0">{{ t('board.rotationSuffix') }}</span>
                </div>
                <p class="text-xs text-zinc-500">{{ t('board.rotationIntervalHint') }}</p>
              </div>
            </div>

            <!-- Map type -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.boardType') }}</label>
              <div class="relative">
                <select v-model="settingsForm.map_type"
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
            <template v-if="settingsForm.map_type === 'worldmap'">
              <div class="grid grid-cols-[1fr_1fr_5rem] gap-3">
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.latitude') }}</label>
                  <NumberInput v-model="settingsForm.worldmap_lat" step="any" :precision="10" class="w-full" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.longitude') }}</label>
                  <NumberInput v-model="settingsForm.worldmap_lng" step="any" :precision="10" class="w-full" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.zoom') }}</label>
                  <NumberInput v-model="settingsForm.worldmap_zoom" min="1" max="18" class="w-full" />
                </div>
              </div>
              <p class="text-xs text-zinc-600">{{ t('board.worldmapHint') }}</p>
            </template>

            <!-- Radar settings -->
            <template v-if="settingsForm.map_type === 'radar'">
              <div class="grid grid-cols-[1fr_1fr] gap-3">
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.filterType') }}</label>
                  <div class="relative">
                    <select v-model="settingsForm.radar_type"
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
                <div v-if="settingsForm.radar_type === 'hostgroup' || settingsForm.radar_type === 'servicegroup'" class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.groupName') }}</label>
                  <input v-model="settingsForm.radar_value" placeholder="e.g. linux-servers"
                    class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                </div>
              </div>
            </template>

            <!-- Templates -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.hoverTemplate') }}</label>
              <input v-model="settingsForm.hover_template" :placeholder="t('board.templatePlaceholder')"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.contextTemplate') }}</label>
              <input v-model="settingsForm.context_template" :placeholder="t('board.templatePlaceholder')"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              <p class="text-xs text-zinc-600">{{ t('board.templateHint') }}</p>
            </div>

            <!-- Background image (static only) -->
            <div v-if="settingsForm.map_type === 'static'" class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('board.backgroundImage') }}</label>
              <div class="flex gap-2">
                <input v-model="settingsForm.background_image" placeholder="filename.png"
                  class="flex-1 px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                <label class="flex items-center px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 hover:ring-zinc-500 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 cursor-pointer transition-all">
                  {{ t('common.upload') }}
                  <input type="file" accept="image/*" class="hidden" @change="uploadBackground" />
                </label>
                <button v-if="settingsForm.background_image" type="button"
                  @click="deleteBackground"
                  class="px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 hover:ring-red-500 rounded-lg text-sm text-zinc-500 hover:text-red-400 transition-all"
                  :title="t('board.deleteBackground')">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </button>
              </div>
              <p v-if="uploadError" class="text-red-400 text-xs flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                {{ uploadError }}
              </p>
              <p v-if="uploadOk" class="text-green-400 text-xs flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                {{ t('board.uploadedSuccessfully') }}
              </p>
            </div>

            <!-- Actions -->
            <div class="flex gap-3 justify-end pt-2 border-t border-[var(--border)]">
              <button type="button" @click="showSettings = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">{{ t('common.cancel') }}</button>
              <button type="submit" :disabled="settingsSaving"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
                {{ settingsSaving ? t('common.saving') : t('board.saveChanges') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed, ref, reactive, watch, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import { useStatesStore } from '@/stores/states'
import { useConnectionsStore } from '@/stores/connections'
import { useSettingsStore } from '@/stores/settings'
import { useBoardEditor } from '@/composables/useBoardEditor'
import { boardsApi } from '@/api/client'
import { resolveTemplate } from '@/utils/template'
import BoardCanvas from '@/components/board/BoardCanvas.vue'
import WorldMapCanvas from '@/components/board/WorldMapCanvas.vue'
import HoverMenu from '@/components/board/HoverMenu.vue'
import ContextMenu from '@/components/board/ContextMenu.vue'
import NumberInput from '@/components/NumberInput.vue'
import AutomapCanvas from '@/components/board/AutomapCanvas.vue'
import RadarCanvas from '@/components/board/RadarCanvas.vue'
import EditPanel from '@/components/board/EditPanel.vue'
import ObjectPropertiesModal from '@/components/board/ObjectPropertiesModal.vue'
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
const showSettings = ref(false)
const showUserSettings = ref(false)
const settingsSaving = ref(false)
const uploadError = ref('')
const uploadOk = ref(false)

const settingsForm = reactive({
  alias: '',
  backend_id: '',
  icon_size: 22,
  background_image: '',
  map_type: 'static',
  worldmap_lat: 51.0,
  worldmap_lng: 10.0,
  worldmap_zoom: 5,
  radar_type: 'hostgroup',
  radar_value: '',
  hover_template: '',
  context_template: '',
  rotation_interval: 0,
})

function openSettings() {
  if (!boardConfig.value) return
  const cfg = boardConfig.value
  settingsForm.alias = cfg.alias ?? ''
  settingsForm.backend_id = cfg.backend_id ?? ''
  settingsForm.icon_size = cfg.icon_size ?? 22
  settingsForm.background_image = cfg.background_image ?? ''
  settingsForm.map_type = cfg.view.type ?? 'static'
  settingsForm.hover_template = cfg.hover_template ?? ''
  settingsForm.context_template = cfg.context_template ?? ''
  settingsForm.rotation_interval = cfg.rotation_interval ?? 0
  uploadError.value = ''
  uploadOk.value = false

  if (cfg.view.type === 'radar') {
    const rv = cfg.view as import('@/types/api').RadarView
    settingsForm.radar_type = rv.filter ?? 'hostgroup'
    settingsForm.radar_value = rv.filter_value ?? ''
  } else {
    settingsForm.radar_type = 'hostgroup'
    settingsForm.radar_value = ''
  }

  if (cfg.view.type === 'worldmap' && worldmapCanvasRef.value) {
    const view = worldmapCanvasRef.value.getView()
    const wv = cfg.view as import('@/types/api').WorldmapView
    if (view) {
      settingsForm.worldmap_lat = view.lat
      settingsForm.worldmap_lng = view.lng
      settingsForm.worldmap_zoom = view.zoom
    } else {
      settingsForm.worldmap_lat = wv.lat ?? 51
      settingsForm.worldmap_lng = wv.lng ?? 10
      settingsForm.worldmap_zoom = wv.zoom ?? 5
    }
  } else if (cfg.view.type === 'worldmap') {
    const wv = cfg.view as import('@/types/api').WorldmapView
    settingsForm.worldmap_lat = wv.lat ?? 51
    settingsForm.worldmap_lng = wv.lng ?? 10
    settingsForm.worldmap_zoom = wv.zoom ?? 5
  } else {
    settingsForm.worldmap_lat = 51.0
    settingsForm.worldmap_lng = 10.0
    settingsForm.worldmap_zoom = 5
  }

  showSettings.value = true
}

async function saveSettings() {
  settingsSaving.value = true
  try {
    let view: Record<string, unknown>
    if (settingsForm.map_type === 'worldmap') {
      view = { type: 'worldmap', lat: settingsForm.worldmap_lat, lng: settingsForm.worldmap_lng, zoom: settingsForm.worldmap_zoom }
    } else if (settingsForm.map_type === 'radar') {
      view = { type: 'radar', filter: settingsForm.radar_type, filter_value: settingsForm.radar_value }
    } else {
      view = { type: settingsForm.map_type }
    }
    const updated = await boardsApi.update(boardName.value, {
      alias: settingsForm.alias,
      backend_id: settingsForm.backend_id,
      icon_size: settingsForm.icon_size,
      background_image: settingsForm.background_image || null,
      view,
      hover_template: settingsForm.hover_template || null,
      context_template: settingsForm.context_template || null,
      rotation_interval: settingsForm.rotation_interval,
    }, auth.accessToken!)
    if (boardsStore.currentBoard) Object.assign(boardsStore.currentBoard, updated)
    stopRotation()
    scheduleRotation(settingsForm.rotation_interval)
    showSettings.value = false
  } finally {
    settingsSaving.value = false
  }
}

async function uploadBackground(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploadError.value = ''
  uploadOk.value = false
  try {
    const result = await boardsApi.uploadBackground(boardName.value, file, auth.accessToken!)
    settingsForm.background_image = result.filename
    await reloadBoard()
    uploadOk.value = true
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
  }
}

async function deleteBackground() {
  try {
    await boardsApi.deleteBackground(boardName.value, auth.accessToken!)
    settingsForm.background_image = ''
    await reloadBoard()
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Delete failed'
  }
}

// ---- Rotation ----

const rotationTimer = ref<ReturnType<typeof setTimeout> | null>(null)

function stopRotation() {
  if (rotationTimer.value !== null) {
    clearTimeout(rotationTimer.value)
    rotationTimer.value = null
  }
}

function scheduleRotation(intervalSeconds: number) {
  stopRotation()
  if (intervalSeconds <= 0 || editor.editMode.value) return
  rotationTimer.value = setTimeout(async () => {
    // Ensure map list is loaded
    if (boardsStore.boards.length === 0) await boardsStore.fetchBoards()
    const all = boardsStore.boards
    if (all.length < 2) return
    const idx = all.findIndex(m => m.name === boardName.value)
    const next = all[(idx + 1) % all.length]
    router.push({ name: 'board', params: { name: next.name } })
  }, intervalSeconds * 1000)
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
