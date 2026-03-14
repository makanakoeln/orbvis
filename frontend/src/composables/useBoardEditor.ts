/**
 * Map edit-mode state: drag & drop, line editing, object selection, placing new objects.
 */
import { ref, reactive, type Ref } from 'vue'
import { boardsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import { useSettingsStore } from '@/stores/settings'
import type { BoardObject, ObjectType } from '@/types/api'

export interface NewObjectDraft {
  type: ObjectType | ''
  host_name: string
  service_description: string
  group_name: string
  board_name: string
  label_text: string
  image_src: string
}

interface LineCoords { x: number; y: number; x2: number; y2: number }

type DragTarget =
  | { kind: 'line'; id: string; mode: 'move' | 'start' | 'end'; init: LineCoords; mouseStartX: number; mouseStartY: number }

// mapName is a Ref so that this composable stays in sync when Vue Router reuses
// the MapView component for a different map (avoids stale closure over the old name).
export function useBoardEditor(mapName: Ref<string>, onMapChange: () => Promise<void>) {
  const auth = useAuthStore()
  const boardsStore = useBoardsStore()

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

  const lineDragPositions = reactive<Record<string, LineCoords>>({})

  function _mouseToCanvas(event: MouseEvent, canvasEl: HTMLElement) {
    const rect = canvasEl.getBoundingClientRect()
    // When canvas fills its parent (background image mode), positions are percentages
    // of native image size — read native dims from data attributes set by BoardCanvas.
    const nativeW = parseFloat(canvasEl.dataset.nativeWidth ?? '0')
    const nativeH = parseFloat(canvasEl.dataset.nativeHeight ?? '0')
    if (nativeW > 0 && nativeH > 0) {
      return {
        x: ((event.clientX - rect.left) / rect.width) * nativeW,
        y: ((event.clientY - rect.top) / rect.height) * nativeH,
      }
    }
    const parent = canvasEl.parentElement!
    return {
      x: event.clientX - rect.left + parent.scrollLeft,
      y: event.clientY - rect.top + parent.scrollTop,
    }
  }

  // --- Document-level drag handlers (line drag only) ---

  function _onDocMouseMove(event: MouseEvent) {
    event.preventDefault()
    if (!_canvasEl) return
    const t = dragTarget.value
    if (!t) return
    const pos = _mouseToCanvas(event, _canvasEl)

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

  function _onDocMouseUp() {
    document.removeEventListener('mousemove', _onDocMouseMove, { capture: true })
    document.removeEventListener('mouseup', _onDocMouseUp, { capture: true })
    endLineDrag()
  }

  function _startDocDrag(canvasEl: HTMLElement) {
    _canvasEl = canvasEl
    // Use capture phase so we receive events before any child element that may
    // call stopPropagation() (e.g. D3 internal handlers).
    document.addEventListener('mousemove', _onDocMouseMove, { capture: true })
    document.addEventListener('mouseup', _onDocMouseUp, { capture: true })
  }

  // --- Save object position (called from BoardCanvas object-drag-end event) ---
  async function saveObjectPosition(id: string, x: number, y: number) {
    // Optimistic update before the API call so Vue re-renders at the new position
    // immediately when localDragPositions is cleared — no snap-back glitch.
    const obj = boardsStore.currentBoard?.objects.find(o => o.id === id)
    if (obj) { obj.x = x; obj.y = y }
    try {
      await boardsApi.updateObject(mapName.value, id, { x, y }, auth.accessToken!)
      if (_onDragSaved) _onDragSaved(id)
    } catch (e) {
      console.error('Failed to save drag', e)
      await onMapChange()
    }
  }

  // --- Line drag ---
  function startLineDrag(
    event: MouseEvent,
    obj: BoardObject,
    mode: 'move' | 'start' | 'end',
    canvasEl: HTMLElement,
  ) {
    const mouse = _mouseToCanvas(event, canvasEl)
    const x2 = obj.x2 ?? obj.x + 100
    const y2 = obj.y2 ?? obj.y + 100
    const init: LineCoords = { x: obj.x, y: obj.y, x2, y2 }
    lineDragPositions[obj.id] = { ...init }
    dragTarget.value = { kind: 'line', id: obj.id, mode, init, mouseStartX: mouse.x, mouseStartY: mouse.y }
    selectedObjectId.value = obj.id
    _startDocDrag(canvasEl)
    event.preventDefault()
    event.stopPropagation()
  }

  // --- End line drag (save to backend, patch store locally) ---
  async function endLineDrag() {
    const t = dragTarget.value
    if (!t || t.kind !== 'line') return
    dragTarget.value = null
    try {
      const lp = lineDragPositions[t.id]
      await boardsApi.updateObject(mapName.value, t.id, {
        x: lp.x, y: lp.y,
        x2: lp.x2, y2: lp.y2,
      }, auth.accessToken!)
      const obj = boardsStore.currentBoard?.objects.find(o => o.id === t.id)
      if (obj) {
        obj.x = lp.x; obj.y = lp.y
        obj.x2 = lp.x2; obj.y2 = lp.y2
      }
      delete lineDragPositions[t.id]
      if (_onDragSaved) _onDragSaved(t.id)
    } catch (e) {
      console.error('Failed to save line drag', e)
      await onMapChange()
    }
  }

  // --- Update object properties (from EditPanel) ---
  async function updateObjectProperties(id: string, updates: Record<string, unknown>) {
    const updated = await boardsApi.updateObject(mapName.value, id, updates, auth.accessToken!)
    const objects = boardsStore.currentBoard?.objects
    if (objects && updated) {
      const idx = objects.findIndex(o => o.id === id)
      if (idx !== -1) objects[idx] = updated
    }
  }

  // --- Place new object ---
  const placing = ref(false)
  const draft = reactive<NewObjectDraft>({
    type: '', host_name: '', service_description: '', group_name: '', board_name: '', label_text: '', image_src: '',
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
    const obj: BoardObject = {
      id, type: draft.type,
      x: _snap(Math.round(x)), y: _snap(Math.round(y)),
      host_name: draft.host_name || undefined,
      service_description: draft.service_description || undefined,
      group_name: draft.group_name || undefined,
      map_name: draft.board_name || undefined,
      label: {
        show: s.label_show,
        text: draft.label_text || null,
        x: s.label_x, y: s.label_y,
        size: s.label_size, color: s.label_color, background: s.label_background,
      },
      display: draft.type === 'line' ? null : {
        mode: s.view_type as 'icon' | 'text' | 'gadget',
        image: draft.image_src || null,
        image_size: s.icon_size,
      },
      image_src: draft.type === 'image' ? (draft.image_src || null) : undefined,
      url_target: s.url_target, z: s.z,
      ...(draft.type === 'line' ? { x2: _snap(Math.round(x)) + 150, y2: _snap(Math.round(y)), line_style: s.line_style ?? 'plain' } : {}),
    }
    try {
      const newConfig = await boardsApi.addObject(mapName.value, obj, auth.accessToken!)
      if (boardsStore.currentBoard) boardsStore.currentBoard.objects = newConfig.objects
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
    const obj: BoardObject = {
      id, type: draft.type,
      x: 0, y: 0,
      lat, lng,
      host_name: draft.host_name || undefined,
      service_description: draft.service_description || undefined,
      group_name: draft.group_name || undefined,
      map_name: draft.board_name || undefined,
      label: {
        show: s.label_show,
        text: draft.label_text || null,
        x: s.label_x, y: s.label_y,
        size: s.label_size, color: s.label_color, background: s.label_background,
      },
      display: {
        mode: s.view_type as 'icon' | 'text' | 'gadget',
        image: draft.image_src || null,
        image_size: s.icon_size,
      },
      url_target: s.url_target, z: s.z,
    }
    try {
      const newConfig = await boardsApi.addObject(mapName.value, obj, auth.accessToken!)
      if (boardsStore.currentBoard) boardsStore.currentBoard.objects = newConfig.objects
      selectedObjectId.value = id
    } catch (e) {
      console.error('Failed to add object', e)
    }
  }

  async function moveObjectToLatLng(id: string, lat: number, lng: number) {
    try {
      await boardsApi.updateObject(mapName.value, id, { lat, lng }, auth.accessToken!)
      const obj = boardsStore.currentBoard?.objects.find(o => o.id === id)
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
    draft.board_name = ''
    draft.label_text = ''
    draft.image_src = ''
    Object.keys(lineDragPositions).forEach(k => delete lineDragPositions[k])
  }

  // --- Delete ---
  async function deleteSelected() {
    const id = selectedObjectId.value
    if (!id) return
    selectedObjectId.value = null
    try {
      await boardsApi.deleteObject(mapName.value, id, auth.accessToken!)
      if (boardsStore.currentBoard)
        boardsStore.currentBoard.objects = boardsStore.currentBoard.objects.filter(o => o.id !== id)
    } catch (e) {
      console.error('Failed to delete object', e)
      await onMapChange()
    }
  }

  // --- Duplicate selected object ---
  async function duplicateSelected() {
    const id = selectedObjectId.value
    if (!id || !boardsStore.currentBoard) return
    const src = boardsStore.currentBoard.objects.find(o => o.id === id)
    if (!src) return
    const newId = `${src.type}_${crypto.randomUUID()}`
    const clone: BoardObject = {
      ...JSON.parse(JSON.stringify(src)),
      id: newId,
      x: _snap(src.x + 30),
      y: _snap(src.y + 30),
    }
    if (clone.x2 !== undefined && clone.x2 !== null) {
      clone.x2 = (clone.x2 as number) + 30
      clone.y2 = (clone.y2 as number) + 30
    }
    try {
      const newConfig = await boardsApi.addObject(mapName.value, clone, auth.accessToken!)
      if (boardsStore.currentBoard) boardsStore.currentBoard.objects = newConfig.objects
      selectedObjectId.value = newId
    } catch (e) {
      console.error('Failed to duplicate object', e)
    }
  }

  // --- Cancel placing ---
  function cancelPlacing() {
    placing.value = false
  }

  return {
    editMode, toggleEditMode,
    selectedObjectId, selectObject,
    snapGrid, setDragSavedCallback,
    lineDragPositions,
    saveObjectPosition, startLineDrag,
    updateObjectProperties,
    placing, draft, startPlacing, placeAt, placeAtLatLng, moveObjectToLatLng,
    deleteSelected, duplicateSelected, cancelPlacing,
    resetForNewMap,
  }
}
