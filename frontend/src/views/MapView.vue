<template>
  <div class="h-screen bg-zinc-950 flex flex-col">
    <!-- Navbar -->
    <nav class="bg-zinc-900/90 backdrop-blur-md border-b border-white/5 px-5 py-2.5 flex justify-between items-center shrink-0 z-30">
      <div class="flex items-center gap-2 min-w-0">
        <router-link to="/"
          class="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors shrink-0">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Maps
        </router-link>
        <svg class="w-3 h-3 text-zinc-700 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
        </svg>
        <span class="font-semibold text-zinc-100 text-sm truncate">{{ mapConfig?.globals.alias || route.params.name }}</span>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <!-- Connection status -->
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ring-1 transition-all"
          :class="statesStore.connected
            ? 'bg-green-500/8 ring-green-500/20 text-green-400'
            : 'bg-red-500/8 ring-red-500/20 text-red-400'">
          <span class="w-1.5 h-1.5 rounded-full inline-block"
            :class="statesStore.connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'" />
          {{ statesStore.connected ? 'Live' : 'Offline' }}
        </div>

        <!-- Divider -->
        <span v-if="auth.isAdmin" class="w-px h-4 bg-zinc-700" />

        <!-- Settings button -->
        <button v-if="auth.isAdmin" @click="openSettings"
          class="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all duration-150"
          title="Map settings">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        <!-- Edit toggle -->
        <button v-if="auth.isAdmin" @click="onToggleEditMode"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
          :class="editor.editMode.value
            ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30 hover:bg-amber-500/20'
            : 'bg-zinc-800 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700'">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
          </svg>
          {{ editor.editMode.value ? 'Editing' : 'Edit' }}
        </button>

        <template v-if="!auth.ssoActive">
          <span class="w-px h-4 bg-zinc-700" />
          <button @click="auth.logout"
            class="px-3 py-1.5 rounded-lg text-xs text-zinc-500 hover:text-zinc-100 hover:bg-zinc-800 transition-all duration-150">
            Logout
          </button>
        </template>
      </div>
    </nav>

    <!-- Map area + optional edit panel -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Worldmap -->
      <div v-if="isWorldmap" class="flex-1 overflow-hidden bg-zinc-950 relative">
        <div v-if="mapsStore.loading" class="absolute inset-0 flex items-center justify-center text-zinc-500 z-10 text-sm">
          Loading map…
        </div>
        <div v-else-if="mapsStore.error" class="absolute inset-0 flex items-center justify-center text-red-400 z-10 text-sm">
          {{ mapsStore.error }}
        </div>
        <WorldMapCanvas
          v-else-if="mapConfig"
          ref="worldmapCanvasRef"
          :config="mapConfig"
          :states="statesStore.states"
          :edit-mode="editor.editMode.value"
          :placing="editor.placing.value"
          :selected-object-id="editor.selectedObjectId.value"
          @object-click="onObjectClick"
          @object-contextmenu="onObjectContextMenu"
          @canvas-latlng-click="onCanvasLatLngClick"
          @latlng-drag-end="onLatLngDragEnd"
        />
        <div v-else class="absolute inset-0 flex items-center justify-center text-zinc-600">Map not found</div>
      </div>

      <!-- Automap -->
      <div v-else-if="isAutomap" class="flex-1 relative overflow-hidden">
        <AutomapCanvas
          v-if="mapConfig?.globals.backend_id"
          :backend-id="mapConfig.globals.backend_id"
        />
        <div v-else class="flex items-center justify-center h-full text-zinc-500 text-sm">No backend configured for this map.</div>
      </div>

      <!-- Static map -->
      <div v-else class="flex-1 overflow-auto bg-zinc-950">
        <div v-if="mapsStore.loading" class="flex items-center justify-center h-full text-zinc-500 text-sm">
          Loading map…
        </div>
        <div v-else-if="mapsStore.error" class="flex items-center justify-center h-full text-red-400 text-sm">
          {{ mapsStore.error }}
        </div>
        <MapCanvas
          v-else-if="mapConfig"
          ref="canvasRef"
          :config="mapConfig"
          :states="statesStore.states"
          :edit-mode="editor.editMode.value"
          :placing="editor.placing.value"
          :dragging-id="editor.draggingId.value"
          :drag-positions="editor.dragPositions"
          :line-drag-positions="editor.lineDragPositions"
          :selected-object-id="editor.selectedObjectId.value"
          :checkmk-url="checkmkUrl"
          :is-admin="auth.isAdmin"
          :icon-size-override="showSettings ? settingsForm.icon_size : undefined"
          :snap-grid="editor.snapGrid.value"
          @object-mousedown="onObjectMouseDown"
          @object-click="onObjectClick"
          @object-contextmenu="onObjectContextMenu"
          @object-delete="onObjectDelete"
          @line-drag-start="onLineDragStart"
          @canvas-click="onCanvasClick"
        />
        <div v-else class="flex items-center justify-center h-full text-zinc-600">Map not found</div>
      </div>

      <!-- Edit panel (not for automap) -->
      <EditPanel
        v-if="editor.editMode.value && !isAutomap"
        :draft="editor.draft"
        :placing="editor.placing.value"
        :selected-object="selectedObject"
        :drag-positions="editor.dragPositions"
        :backend-id="mapConfig?.globals.backend_id ?? ''"
        :snap-grid="editor.snapGrid.value"
        :map-type="mapConfig?.globals.map_type"
        @start-placing="editor.startPlacing()"
        @delete-selected="editor.deleteSelected()"
        @preview-properties="onPreviewProperties"
        @save-properties="onSaveProperties"
        @update:dirty="hasUnsavedChanges = $event"
        @update:snap-grid="editor.snapGrid.value = $event"
      />
    </div>

    <!-- Unsaved changes warning when leaving edit mode -->
    <Teleport to="body">
      <div v-if="showExitEditWarning" class="fixed inset-0 z-[60] flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showExitEditWarning = false" />
        <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/60 rounded-2xl p-6 w-80">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-9 h-9 rounded-full bg-amber-500/15 ring-1 ring-amber-500/25 flex items-center justify-center shrink-0">
              <svg class="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
              </svg>
            </div>
            <div>
              <p class="font-semibold text-zinc-100 text-sm">Unsaved changes</p>
              <p class="text-xs text-zinc-500 mt-0.5">Save or discard before leaving edit mode.</p>
            </div>
          </div>
          <div class="flex gap-2 justify-between mt-5">
            <button @click="confirmExitEditMode"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-500/15 hover:bg-red-500/25 ring-1 ring-red-500/25 hover:ring-red-500/40 text-red-400 transition-all">
              Discard
            </button>
            <div class="flex gap-2">
              <button @click="showExitEditWarning = false"
                class="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all">
                Cancel
              </button>
              <button @click="saveAndExitEditMode"
                class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-all">
                Save & exit
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirmation -->
    <ConfirmDialog
      v-if="deleteTargetObject"
      title="Delete object"
      message="This cannot be undone."
      confirm-label="Delete"
      @confirm="confirmObjectDelete"
      @cancel="deleteTargetObject = null"
    />

    <!-- Object Properties Modal -->
    <Teleport to="body">
      <ObjectPropertiesModal
        v-if="propsModalObject"
        :object="propsModalObject"
        :state="statesStore.states[propsModalObject.id]"
        :backend-id="mapConfig?.globals.backend_id ?? ''"
        :map-type="mapConfig?.globals.map_type"
        @close="propsModalObject = null"
        @save="onPropsModalSave"
        @delete="onPropsModalDelete"
      />
    </Teleport>

    <!-- Map Settings Modal -->
    <Teleport to="body">
      <div v-if="showSettings" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showSettings = false" />
        <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 w-[34rem] max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between mb-6">
            <h3 class="text-base font-bold text-zinc-100">Map Settings</h3>
            <button @click="showSettings = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="saveSettings" class="space-y-4">
            <!-- Alias -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Display name</label>
              <input v-model="settingsForm.alias"
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <!-- Backend + Icon size -->
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Backend</label>
                <div class="relative">
                  <select v-model="settingsForm.backend_id"
                    class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
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
                <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Icon size</label>
                <NumberInput v-model="settingsForm.icon_size" min="12" max="96" class="w-full" />
              </div>
            </div>

            <!-- Map type -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Map type</label>
              <div class="relative">
                <select v-model="settingsForm.map_type"
                  class="w-full appearance-none px-3.5 py-2.5 pr-9 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
                  <option value="static">Static map</option>
                  <option value="worldmap">Worldmap (geographic)</option>
                  <option value="automap">Automap (topology)</option>
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
              <div class="grid grid-cols-3 gap-3">
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Latitude</label>
                  <NumberInput v-model="settingsForm.worldmap_lat" step="any" class="w-full" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Longitude</label>
                  <NumberInput v-model="settingsForm.worldmap_lng" step="any" class="w-full" />
                </div>
                <div class="space-y-1.5">
                  <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Zoom</label>
                  <NumberInput v-model="settingsForm.worldmap_zoom" min="1" max="18" class="w-full" />
                </div>
              </div>
              <p class="text-xs text-zinc-600">Pan/zoom the map first, then reopen settings to capture the current view.</p>
            </template>

            <!-- Background image (static only) -->
            <div v-if="settingsForm.map_type === 'static'" class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Background image</label>
              <div class="flex gap-2">
                <input v-model="settingsForm.background_image" placeholder="filename.png"
                  class="flex-1 px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
                <label class="flex items-center px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 hover:ring-zinc-500 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 cursor-pointer transition-all">
                  Upload
                  <input type="file" accept="image/*" class="hidden" @change="uploadBackground" />
                </label>
              </div>
              <p v-if="uploadError" class="text-red-400 text-xs flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                {{ uploadError }}
              </p>
              <p v-if="uploadOk" class="text-green-400 text-xs flex items-center gap-1">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                Uploaded successfully
              </p>
            </div>

            <!-- Actions -->
            <div class="flex gap-3 justify-end pt-2 border-t border-white/5">
              <button type="button" @click="showSettings = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all">Cancel</button>
              <button type="submit" :disabled="settingsSaving"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
                {{ settingsSaving ? 'Saving…' : 'Save changes' }}
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
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMapsStore } from '@/stores/maps'
import { useStatesStore } from '@/stores/states'
import { useBackendsStore } from '@/stores/backends'
import { useMapEditor } from '@/composables/useMapEditor'
import { mapsApi } from '@/api/client'
import MapCanvas from '@/components/map/MapCanvas.vue'
import WorldMapCanvas from '@/components/map/WorldMapCanvas.vue'
import NumberInput from '@/components/NumberInput.vue'
import AutomapCanvas from '@/components/map/AutomapCanvas.vue'
import EditPanel from '@/components/map/EditPanel.vue'
import ObjectPropertiesModal from '@/components/map/ObjectPropertiesModal.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import type { MapObject } from '@/types/api'

type LineDragMode = 'move' | 'start' | 'end'

const route = useRoute()
const auth = useAuthStore()
const mapsStore = useMapsStore()
const statesStore = useStatesStore()
const backendsStore = useBackendsStore()

const mapName = computed(() => route.params.name as string)
const mapConfig = computed(() => mapsStore.currentMap)
const canvasRef = ref<InstanceType<typeof MapCanvas> | null>(null)
const worldmapCanvasRef = ref<InstanceType<typeof WorldMapCanvas> | null>(null)

const isWorldmap = computed(() => mapConfig.value?.globals.map_type === 'worldmap')
const isAutomap  = computed(() => mapConfig.value?.globals.map_type === 'automap')

const checkmkUrl = computed(() => {
  const bid = mapConfig.value?.globals.backend_id
  if (!bid) return null
  return backendsStore.backends.find(b => b.id === bid)?.checkmk_url ?? null
})

async function reloadMap() {
  await mapsStore.fetchMap(mapName.value)
}

const editor = useMapEditor(mapName, reloadMap)

// ---- Object properties modal (right-click in view mode) ----

const propsModalObject = ref<MapObject | null>(null)
const deleteTargetObject = ref<MapObject | null>(null)

function onObjectContextMenu(obj: MapObject) {
  editor.selectObject(obj.id)
  if (!editor.editMode.value) {
    propsModalObject.value = obj
  }
}

async function onPropsModalSave(updates: Record<string, unknown>) {
  if (propsModalObject.value)
    await editor.updateObjectProperties(propsModalObject.value.id, updates)
  propsModalObject.value = null
}

async function onPropsModalDelete() {
  const obj = propsModalObject.value
  propsModalObject.value = null
  if (obj) {
    editor.selectObject(obj.id)
    await editor.deleteSelected()
  }
}

// ---- Edit mode toggle with unsaved-changes guard ----

const hasUnsavedChanges = ref(false)
const showExitEditWarning = ref(false)
const lastPreviewUpdates = ref<Record<string, unknown> | null>(null)

function onToggleEditMode() {
  if (editor.editMode.value && hasUnsavedChanges.value) {
    showExitEditWarning.value = true
  } else {
    editor.toggleEditMode()
  }
}

function confirmExitEditMode() {
  showExitEditWarning.value = false
  // Restore snapshot (discard unsaved preview changes)
  if (editor.selectedObjectId.value && objectSnapshot.value && mapsStore.currentMap) {
    const idx = mapsStore.currentMap.objects.findIndex(o => o.id === editor.selectedObjectId.value)
    if (idx !== -1) mapsStore.currentMap.objects[idx] = objectSnapshot.value
  }
  objectSnapshot.value = null
  hasUnsavedChanges.value = false
  editor.toggleEditMode()
}

async function saveAndExitEditMode() {
  showExitEditWarning.value = false
  if (editor.selectedObjectId.value && lastPreviewUpdates.value) {
    await onSaveProperties(lastPreviewUpdates.value)
  }
  hasUnsavedChanges.value = false
  editor.toggleEditMode()
}

// ---- Live preview: apply sidebar form changes directly to the store ----

const objectSnapshot = ref<MapObject | null>(null)

// After a drag saves successfully: replace store object (new ref triggers EditPanel position sync)
// and update snapshot so deselect doesn't revert the dragged position.
editor.setDragSavedCallback((id) => {
  if (!mapsStore.currentMap) return
  const idx = mapsStore.currentMap.objects.findIndex(o => o.id === id)
  if (idx !== -1) {
    mapsStore.currentMap.objects[idx] = { ...mapsStore.currentMap.objects[idx] }
    if (id === editor.selectedObjectId.value)
      objectSnapshot.value = JSON.parse(JSON.stringify(mapsStore.currentMap.objects[idx]))
  }
})

watch(() => editor.selectedObjectId.value, (newId, oldId) => {
  // Restore snapshot when deselecting without saving
  if (oldId && objectSnapshot.value && mapsStore.currentMap) {
    const idx = mapsStore.currentMap.objects.findIndex(o => o.id === oldId)
    if (idx !== -1) mapsStore.currentMap.objects[idx] = objectSnapshot.value
  }
  objectSnapshot.value = null
  if (newId && mapsStore.currentMap) {
    const obj = mapsStore.currentMap.objects.find(o => o.id === newId)
    if (obj) objectSnapshot.value = JSON.parse(JSON.stringify(obj))
  }
})

function onPreviewProperties(updates: Record<string, unknown>) {
  lastPreviewUpdates.value = updates
  if (!editor.selectedObjectId.value || !mapsStore.currentMap) return
  const idx = mapsStore.currentMap.objects.findIndex(o => o.id === editor.selectedObjectId.value)
  if (idx !== -1) {
    const current = mapsStore.currentMap.objects[idx]
    const extra = updates.extra && typeof updates.extra === 'object'
      ? { ...(typeof current.extra === 'object' && current.extra ? current.extra as object : {}), ...(updates.extra as object) }
      : current.extra
    mapsStore.currentMap.objects[idx] = { ...current, ...updates, extra }
  }
}

function onObjectDelete(obj: MapObject) {
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

const selectedObject = computed<MapObject | null>(() => {
  if (!editor.selectedObjectId.value || !mapConfig.value) return null
  return mapConfig.value.objects.find(o => o.id === editor.selectedObjectId.value) ?? null
})

// ---- Static map event handlers ----

function onObjectMouseDown(event: MouseEvent, obj: MapObject) {
  const canvas = canvasRef.value?.canvasEl
  if (canvas) editor.startDrag(event, obj, canvas)
}

function onObjectClick(obj: MapObject) {
  editor.selectObject(obj.id)
}

function onCanvasClick(event: MouseEvent) {
  if (!editor.editMode.value) return
  if (!editor.placing.value) { editor.selectObject(null); return }
  const canvas = canvasRef.value?.canvasEl
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const parent = canvas.parentElement!
  editor.placeAt(event.clientX - rect.left + parent.scrollLeft, event.clientY - rect.top + parent.scrollTop)
}

function onLineDragStart(event: MouseEvent, obj: MapObject, mode: LineDragMode) {
  const canvas = canvasRef.value?.canvasEl
  if (canvas) editor.startLineDrag(event, obj, mode, canvas)
}

// ---- Worldmap event handlers ----

function onCanvasLatLngClick(lat: number, lng: number) {
  if (!editor.editMode.value || !editor.placing.value) return
  editor.placeAtLatLng(lat, lng)
}

function onLatLngDragEnd(id: string, lat: number, lng: number) {
  editor.moveObjectToLatLng(id, lat, lng)
}

async function onSaveProperties(updates: Record<string, unknown>) {
  if (editor.selectedObjectId.value) {
    await editor.updateObjectProperties(editor.selectedObjectId.value, updates)
    // Update snapshot to new saved state so deselect doesn't revert
    if (mapsStore.currentMap) {
      const obj = mapsStore.currentMap.objects.find(o => o.id === editor.selectedObjectId.value)
      if (obj) objectSnapshot.value = JSON.parse(JSON.stringify(obj))
    }
  }
}

// ---- Map Settings ----

const showSettings = ref(false)
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
})

function openSettings() {
  if (!mapConfig.value) return
  const g = mapConfig.value.globals
  settingsForm.alias = g.alias ?? ''
  settingsForm.backend_id = g.backend_id ?? ''
  settingsForm.icon_size = g.icon_size ?? 22
  settingsForm.background_image = g.background_image ?? ''
  settingsForm.map_type = g.map_type ?? 'static'
  uploadError.value = ''
  uploadOk.value = false

  if (g.map_type === 'worldmap' && worldmapCanvasRef.value) {
    const view = worldmapCanvasRef.value.getView()
    if (view) {
      settingsForm.worldmap_lat = view.lat
      settingsForm.worldmap_lng = view.lng
      settingsForm.worldmap_zoom = view.zoom
    } else {
      settingsForm.worldmap_lat = g.worldmap_lat ?? 51
      settingsForm.worldmap_lng = g.worldmap_lng ?? 10
      settingsForm.worldmap_zoom = g.worldmap_zoom ?? 5
    }
  } else {
    settingsForm.worldmap_lat = g.worldmap_lat ?? 51
    settingsForm.worldmap_lng = g.worldmap_lng ?? 10
    settingsForm.worldmap_zoom = g.worldmap_zoom ?? 5
  }

  showSettings.value = true
}

async function saveSettings() {
  settingsSaving.value = true
  try {
    const updated = await mapsApi.update(mapName.value, {
      alias: settingsForm.alias,
      backend_id: settingsForm.backend_id,
      icon_size: settingsForm.icon_size,
      background_image: settingsForm.background_image || null,
      map_type: settingsForm.map_type,
      worldmap_lat: settingsForm.worldmap_lat,
      worldmap_lng: settingsForm.worldmap_lng,
      worldmap_zoom: settingsForm.worldmap_zoom,
    }, auth.accessToken!)
    if (mapsStore.currentMap) mapsStore.currentMap.globals = updated.globals
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
    const result = await mapsApi.uploadBackground(mapName.value, file, auth.accessToken!)
    settingsForm.background_image = result.filename
    uploadOk.value = true
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
  }
}

// Re-run whenever the map name changes (component is reused by Vue Router between maps).
// Reset all edit state so edit mode, selection, and unsaved changes from Map A
// don't carry over when navigating to Map B.
watchEffect(async () => {
  const name = mapName.value
  editor.resetForNewMap()
  hasUnsavedChanges.value = false
  objectSnapshot.value = null
  await mapsStore.fetchMap(name)
  statesStore.connectToMap(name, auth.accessToken ?? undefined)
})

onMounted(() => {
  if (auth.isAdmin) backendsStore.fetchBackends()
})

onUnmounted(() => {
  statesStore.disconnect()
})
</script>

