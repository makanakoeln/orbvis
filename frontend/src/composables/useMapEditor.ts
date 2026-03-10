/**
 * Map edit-mode state: drag & drop, line editing, object selection, placing new objects.
 */
import { ref, reactive, computed, type Ref } from 'vue'
import { mapsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useMapsStore } from '@/stores/maps'
import { useSettingsStore } from '@/stores/settings'
import type { MapObject, ObjectType } from '@/types/api'

export interface NewObjectDraft {
  type: ObjectType | ''
  host_name: string
  service_description: string
  group_name: string
  map_name: string
  label_text: string
}

interface LineCoords { x: number; y: number; x2: number; y2: number }

type DragTarget =
  | { kind: 'object'; id: string }
  | { kind: 'line'; id: string; mode: 'move' | 'start' | 'end'; init: LineCoords; mouseStartX: number; mouseStartY: number }

// mapName is a Ref so that this composable stays in sync when Vue Router reuses
// the MapView component for a different map (avoids stale closure over the old name).
export function useMapEditor(mapName: Ref<string>, onMapChange: () => Promise<void>) {
  const auth = useAuthStore()
  const mapsStore = useMapsStore()

  // --- Edit mode ---
  const editMode = ref(false)
  function toggleEditMode() {
    editMode.value = !editMode.value
    if (!editMode.value) {
      selectedObjectId.value = null
      placing.value = false
    }
  }

  // --- Selection ---
  const selectedObjectId = ref<string | null>(null)
  function selectObject(id: string | null) {
    selectedObjectId.value = id
  }

  // --- Post-drag callback (so MapView can sync snapshot + EditPanel) ---
  let _onDragSaved: ((id: string) => void) | null = null
  function setDragSavedCallback(cb: (id: string) => void) { _onDragSaved = cb }

  // --- Grid snapping ---
  const snapGrid = ref(0) // 0 = off, 10 or 20 = snap to grid
  function _snap(v: number): number {
    if (!snapGrid.value) return v
    return Math.round(v / snapGrid.value) * snapGrid.value
  }

  // --- Shared drag state ---
  const dragTarget = ref<DragTarget | null>(null)
  let _canvasEl: HTMLElement | null = null

  const dragPositions = reactive<Record<string, { x: number; y: number }>>({})
  const lineDragPositions = reactive<Record<string, LineCoords>>({})

  let _dragOffsetX = 0
  let _dragOffsetY = 0

  // Reactive derived value: which object is currently being dragged.
  // Using computed() ensures Vue's reactivity system tracks it properly.
  const draggingId = computed(() => dragTarget.value?.id ?? null)

  function _mouseToCanvas(event: MouseEvent, canvasEl: HTMLElement) {
    const rect = canvasEl.getBoundingClientRect()
    const parent = canvasEl.parentElement!
    return {
      x: event.clientX - rect.left + parent.scrollLeft,
      y: event.clientY - rect.top + parent.scrollTop,
    }
  }

  // --- Document-level drag handlers ---

  function _onDocMouseMove(event: MouseEvent) {
    event.preventDefault()
    if (!_canvasEl) return
    const t = dragTarget.value
    if (!t) return
    const pos = _mouseToCanvas(event, _canvasEl)

    if (t.kind === 'object') {
      dragPositions[t.id] = {
        x: Math.max(0, _snap(Math.round(pos.x - _dragOffsetX))),
        y: Math.max(0, _snap(Math.round(pos.y - _dragOffsetY))),
      }
    } else if (t.kind === 'line') {
      const dx = pos.x - t.mouseStartX
      const dy = pos.y - t.mouseStartY
      const { init, mode } = t
      if (mode === 'move') {
        lineDragPositions[t.id] = {
          x: _snap(Math.round(init.x + dx)), y: _snap(Math.round(init.y + dy)),
          x2: _snap(Math.round(init.x2 + dx)), y2: _snap(Math.round(init.y2 + dy)),
        }
      } else if (mode === 'start') {
        lineDragPositions[t.id] = {
          x: _snap(Math.round(init.x + dx)), y: _snap(Math.round(init.y + dy)),
          x2: init.x2, y2: init.y2,
        }
      } else {
        lineDragPositions[t.id] = {
          x: init.x, y: init.y,
          x2: _snap(Math.round(init.x2 + dx)), y2: _snap(Math.round(init.y2 + dy)),
        }
      }
    }
  }

  function _onDocMouseUp() {
    document.removeEventListener('mousemove', _onDocMouseMove)
    document.removeEventListener('mouseup', _onDocMouseUp)
    endDrag()
  }

  function _startDocDrag(canvasEl: HTMLElement) {
    _canvasEl = canvasEl
    document.addEventListener('mousemove', _onDocMouseMove)
    document.addEventListener('mouseup', _onDocMouseUp)
  }

  // --- Object (icon) drag ---
  function startDrag(event: MouseEvent, obj: MapObject, canvasEl: HTMLElement) {
    const pos = _mouseToCanvas(event, canvasEl)
    _dragOffsetX = pos.x - obj.x
    _dragOffsetY = pos.y - obj.y
    dragPositions[obj.id] = { x: obj.x, y: obj.y }
    dragTarget.value = { kind: 'object', id: obj.id }
    _startDocDrag(canvasEl)
    event.preventDefault()
    event.stopPropagation()
  }

  // --- Line drag ---
  function startLineDrag(
    event: MouseEvent,
    obj: MapObject,
    mode: 'move' | 'start' | 'end',
    canvasEl: HTMLElement,
  ) {
    const mouse = _mouseToCanvas(event, canvasEl)
    const x2 = (obj.extra?.x2 as number) ?? obj.x + 100
    const y2 = (obj.extra?.y2 as number) ?? obj.y + 100
    const init: LineCoords = { x: obj.x, y: obj.y, x2, y2 }
    lineDragPositions[obj.id] = { ...init }
    dragTarget.value = { kind: 'line', id: obj.id, mode, init, mouseStartX: mouse.x, mouseStartY: mouse.y }
    selectedObjectId.value = obj.id
    _startDocDrag(canvasEl)
    event.preventDefault()
    event.stopPropagation()
  }

  // --- End drag (save to backend, patch store locally) ---
  async function endDrag() {
    const t = dragTarget.value
    if (!t) return
    dragTarget.value = null

    try {
      if (t.kind === 'object') {
        const pos = dragPositions[t.id]
        await mapsApi.updateObject(mapName.value, t.id, { x: pos.x, y: pos.y }, auth.accessToken!)
        const obj = mapsStore.currentMap?.objects.find(o => o.id === t.id)
        if (obj) { obj.x = pos.x; obj.y = pos.y }
        delete dragPositions[t.id]
        if (_onDragSaved) _onDragSaved(t.id)
      } else if (t.kind === 'line') {
        const lp = lineDragPositions[t.id]
        await mapsApi.updateObject(mapName.value, t.id, {
          x: lp.x, y: lp.y,
          extra: { x2: lp.x2, y2: lp.y2 },
        }, auth.accessToken!)
        const obj = mapsStore.currentMap?.objects.find(o => o.id === t.id)
        if (obj) {
          obj.x = lp.x; obj.y = lp.y
          if (!obj.extra) obj.extra = {}
          obj.extra.x2 = lp.x2; obj.extra.y2 = lp.y2
        }
        delete lineDragPositions[t.id]
        if (_onDragSaved) _onDragSaved(t.id)
      }
    } catch (e) {
      console.error('Failed to save drag', e)
      await onMapChange()
    }
  }

  // --- Update object properties (from EditPanel) ---
  async function updateObjectProperties(id: string, updates: Record<string, unknown>) {
    const updated = await mapsApi.updateObject(mapName.value, id, updates, auth.accessToken!)
    const objects = mapsStore.currentMap?.objects
    if (objects && updated) {
      const idx = objects.findIndex(o => o.id === id)
      if (idx !== -1) objects[idx] = updated
    }
  }

  // --- Place new object ---
  const placing = ref(false)
  const draft = reactive<NewObjectDraft>({
    type: '', host_name: '', service_description: '', group_name: '', map_name: '', label_text: '',
  })

  function startPlacing() {
    if (!draft.type) return
    placing.value = true
    selectedObjectId.value = null
  }

  async function placeAt(x: number, y: number) {
    if (!placing.value || !draft.type) return
    placing.value = false
    const s = useSettingsStore().settings
    // Use crypto.randomUUID() to avoid collisions from rapid or concurrent placements.
    const id = `${draft.type}_${crypto.randomUUID()}`
    const obj: MapObject = {
      id, type: draft.type,
      x: _snap(Math.round(x)), y: _snap(Math.round(y)),
      host_name: draft.host_name || undefined,
      service_description: draft.service_description || undefined,
      group_name: draft.group_name || undefined,
      map_name: draft.map_name || undefined,
      label_text: draft.label_text || undefined,
      label_show: s.label_show,
      label_x: s.label_x, label_y: s.label_y,
      label_size: s.label_size, label_color: s.label_color, label_background: s.label_background,
      view_type: draft.type === 'line' ? 'line' : s.view_type,
      url_target: s.url_target, z: s.z,
      extra: draft.type === 'line' ? { x2: _snap(Math.round(x)) + 150, y2: _snap(Math.round(y)) } : {},
    }
    try {
      const newConfig = await mapsApi.addObject(mapName.value, obj, auth.accessToken!)
      if (mapsStore.currentMap) mapsStore.currentMap.objects = newConfig.objects
      selectedObjectId.value = id
    } catch (e) {
      console.error('Failed to add object', e)
    }
  }

  // --- Place new object at geographic coordinates (worldmap) ---
  async function placeAtLatLng(lat: number, lng: number) {
    if (!placing.value || !draft.type) return
    placing.value = false
    const s = useSettingsStore().settings
    const id = `${draft.type}_${crypto.randomUUID()}`
    const obj: MapObject = {
      id, type: draft.type,
      x: 0, y: 0,
      lat, lng,
      host_name: draft.host_name || undefined,
      service_description: draft.service_description || undefined,
      group_name: draft.group_name || undefined,
      map_name: draft.map_name || undefined,
      label_text: draft.label_text || undefined,
      label_show: s.label_show,
      label_x: s.label_x, label_y: s.label_y,
      label_size: s.label_size, label_color: s.label_color, label_background: s.label_background,
      view_type: s.view_type,
      url_target: s.url_target, z: s.z,
      extra: {},
    }
    try {
      const newConfig = await mapsApi.addObject(mapName.value, obj, auth.accessToken!)
      if (mapsStore.currentMap) mapsStore.currentMap.objects = newConfig.objects
      selectedObjectId.value = id
    } catch (e) {
      console.error('Failed to add object', e)
    }
  }

  async function moveObjectToLatLng(id: string, lat: number, lng: number) {
    try {
      await mapsApi.updateObject(mapName.value, id, { lat, lng }, auth.accessToken!)
      const obj = mapsStore.currentMap?.objects.find(o => o.id === id)
      if (obj) { obj.lat = lat; obj.lng = lng }
    } catch (e) {
      console.error('Failed to save lat/lng', e)
      await onMapChange()
    }
  }

  // --- Reset all edit state when navigating to a different map ---
  function resetForNewMap() {
    editMode.value = false
    selectedObjectId.value = null
    placing.value = false
    dragTarget.value = null
    draft.type = ''
    draft.host_name = ''
    draft.service_description = ''
    draft.group_name = ''
    draft.map_name = ''
    draft.label_text = ''
    Object.keys(dragPositions).forEach(k => delete dragPositions[k])
    Object.keys(lineDragPositions).forEach(k => delete lineDragPositions[k])
  }

  // --- Delete ---
  async function deleteSelected() {
    const id = selectedObjectId.value
    if (!id) return
    selectedObjectId.value = null
    try {
      await mapsApi.deleteObject(mapName.value, id, auth.accessToken!)
      if (mapsStore.currentMap)
        mapsStore.currentMap.objects = mapsStore.currentMap.objects.filter(o => o.id !== id)
    } catch (e) {
      console.error('Failed to delete object', e)
      await onMapChange()
    }
  }

  return {
    editMode, toggleEditMode,
    selectedObjectId, selectObject,
    snapGrid, setDragSavedCallback,
    draggingId, dragPositions,
    lineDragPositions,
    startDrag, startLineDrag,
    updateObjectProperties,
    placing, draft, startPlacing, placeAt, placeAtLatLng, moveObjectToLatLng,
    deleteSelected,
    resetForNewMap,
  }
}
