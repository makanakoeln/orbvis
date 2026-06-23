import { computed, reactive } from 'vue'

import type { useMapEditor } from '@/composables/useMapEditor'
import { useStatesStore } from '@/stores/states'
import type { MapObject } from '@/types/api'

type MapEditor = ReturnType<typeof useMapEditor>
type AnchorRect = { left: number; top: number; right: number; bottom: number }
type WorldmapView = { lat: number; lng: number; zoom: number }

interface WorldmapMenusOptions {
  editor: MapEditor
  isReadonly: () => boolean
  openPropsModal: (obj: MapObject, anchor?: AnchorRect | null) => void
  onSaveViewAsDefault: (view: WorldmapView) => void
  // The hover card lives in the shared useObjectHoverMenu — opening a context
  // menu or closing the menus must close the card as well.
  closeHover: () => void
}

/**
 * Object context menu (navigation + edit actions) and canvas context menu for
 * the worldmap map; the object menu is also fed by presentation maps.
 * Operational commands (ack, downtime, …) live in the detail drawer, so the
 * menu itself stays navigation-only — see the note in ContextMenu.vue.
 *
 * Cross-cutting dependencies are injected: `openPropsModal` (the shared
 * properties modal lives in the host view) and `onSaveViewAsDefault` (writing
 * the picked view into map settings is the settings cluster's job). Opening
 * the detail drawer should call the returned `closeWorldmapMenus`.
 */
export function useWorldmapMenus(options: WorldmapMenusOptions) {
  const { editor, isReadonly, openPropsModal, onSaveViewAsDefault, closeHover } = options
  const statesStore = useStatesStore()

  const worldmapCtxMenu = reactive({
    visible: false,
    object: null as MapObject | null,
    x: 0,
    y: 0
  })
  const worldmapCtxState = computed(() =>
    worldmapCtxMenu.object ? statesStore.states[worldmapCtxMenu.object.id] : undefined
  )
  const worldmapCanvasCtxMenu = reactive({
    visible: false,
    x: 0,
    y: 0,
    view: null as WorldmapView | null
  })

  function onWorldmapContextMenuView(obj: MapObject, x: number, y: number): void {
    closeHover()
    worldmapCtxMenu.object = obj
    worldmapCtxMenu.x = x
    worldmapCtxMenu.y = y
    worldmapCtxMenu.visible = true
  }

  function onWorldmapCtxEdit(): void {
    const obj = worldmapCtxMenu.object
    const x = worldmapCtxMenu.x
    const y = worldmapCtxMenu.y
    worldmapCtxMenu.visible = false
    if (obj) openPropsModal(obj, { left: x, top: y, right: x, bottom: y })
  }

  function onWorldmapCtxDelete(): void {
    if (isReadonly()) return
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (obj) {
      editor.selectObject(obj.id)
      editor.deleteSelected()
    }
  }

  function onWorldmapCtxDuplicate(): void {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (obj) {
      editor.selectObject(obj.id)
      editor.duplicateSelected()
    }
  }

  function onWorldmapCtxDetach(): void {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (obj) void editor.updateObjectProperties(obj.id, { start_ref: null, end_ref: null })
  }

  function closeWorldmapMenus(): void {
    closeHover()
    worldmapCtxMenu.visible = false
    worldmapCanvasCtxMenu.visible = false
  }

  function onWorldmapCanvasContextMenu(view: WorldmapView, screen: { x: number; y: number }): void {
    worldmapCanvasCtxMenu.view = view
    worldmapCanvasCtxMenu.x = screen.x
    worldmapCanvasCtxMenu.y = screen.y
    worldmapCanvasCtxMenu.visible = true
  }

  function onWorldmapCanvasCtxSaveAsDefault(): void {
    if (!worldmapCanvasCtxMenu.view) return
    onSaveViewAsDefault({ ...worldmapCanvasCtxMenu.view })
    worldmapCanvasCtxMenu.visible = false
  }

  return {
    worldmapCtxMenu,
    worldmapCtxState,
    worldmapCanvasCtxMenu,
    onWorldmapContextMenuView,
    onWorldmapCtxEdit,
    onWorldmapCtxDelete,
    onWorldmapCtxDuplicate,
    onWorldmapCtxDetach,
    closeWorldmapMenus,
    onWorldmapCanvasContextMenu,
    onWorldmapCanvasCtxSaveAsDefault
  }
}
