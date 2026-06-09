import { type Ref, computed, reactive, ref } from 'vue'

import { cmkApi } from '@/api/client'
import type { useBoardEditor } from '@/composables/useBoardEditor'
import { useHoverGrace } from '@/composables/useHoverGrace'
import { useToast } from '@/composables/useToast'
import { useStatesStore } from '@/stores/states'
import type { BoardObject, DowntimeEntry } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

type BoardEditor = ReturnType<typeof useBoardEditor>
type AnchorRect = { left: number; top: number; right: number; bottom: number }
type WorldmapView = { lat: number; lng: number; zoom: number }

interface WorldmapMenusOptions {
  editor: BoardEditor
  checkmkUrl: Ref<string | null>
  isReadonly: () => boolean
  openPropsModal: (obj: BoardObject, anchor?: AnchorRect | null) => void
  onSaveViewAsDefault: (view: WorldmapView) => void
}

/**
 * Hover popup, object context menu, canvas context menu and the four command
 * modals (ack / downtime / comment / remove-downtime) for the worldmap board.
 *
 * Cross-cutting dependencies are injected: `openPropsModal` (the shared
 * properties modal lives in the host view) and `onSaveViewAsDefault` (writing
 * the picked view into board settings is the settings cluster's job). Opening
 * the detail drawer should call the returned `closeWorldmapMenus`.
 */
export function useWorldmapMenus(options: WorldmapMenusOptions) {
  const { editor, checkmkUrl, isReadonly, openPropsModal, onSaveViewAsDefault } = options
  const statesStore = useStatesStore()
  const toast = useToast()
  const { _t } = usei18n()

  const worldmapHover = reactive({ visible: false, object: null as BoardObject | null, x: 0, y: 0 })
  const worldmapCtxMenu = reactive({
    visible: false,
    object: null as BoardObject | null,
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

  // Close-grace so the operator can move onto the hover card and click a
  // service-state pill (HoverMenu @card-enter/-leave round-trip).
  const worldmapHoverGrace = useHoverGrace(() => {
    worldmapHover.visible = false
  })

  function onWorldmapHover(obj: BoardObject, event: MouseEvent): void {
    worldmapHoverGrace.cancelClose()
    worldmapHover.object = obj
    worldmapHover.x = event.pageX + 12
    worldmapHover.y = event.pageY + 12
    worldmapHover.visible = true
  }

  function onWorldmapHoverLeave(): void {
    worldmapHoverGrace.scheduleClose()
  }

  function onWorldmapContextMenuView(obj: BoardObject, x: number, y: number): void {
    editor.selectObject(obj.id)
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

  const worldmapAckModal = ref<BoardObject | null>(null)
  const worldmapDowntimeModal = ref<BoardObject | null>(null)
  const worldmapCommentModal = ref<BoardObject | null>(null)
  const worldmapRemoveDowntimeModal = reactive<{
    visible: boolean
    downtimes: DowntimeEntry[]
    objectName: string
  }>({
    visible: false,
    downtimes: [],
    objectName: ''
  })

  function onWorldmapCtxDowntime(): void {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (obj) worldmapDowntimeModal.value = obj
  }

  async function onWorldmapCtxRemoveDowntime(): Promise<void> {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (!obj || !checkmkUrl.value) return
    let downtimes: DowntimeEntry[]
    try {
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        downtimes = await cmkApi.listDowntimesService(
          checkmkUrl.value,
          obj.host_name,
          obj.service_description
        )
      } else if (obj.host_name) {
        downtimes = await cmkApi.listDowntimesHost(checkmkUrl.value, obj.host_name)
      } else {
        return
      }
    } catch {
      toast.error(_t('Failed to remove downtime'))
      return
    }
    if (downtimes.length === 0) {
      toast.error(_t('No active downtimes found'))
      return
    }
    if (downtimes.length === 1 && downtimes[0]) {
      await doWorldmapRemoveDowntime(downtimes[0])
      return
    }
    worldmapRemoveDowntimeModal.downtimes = downtimes
    worldmapRemoveDowntimeModal.objectName = obj.host_name ?? ''
    worldmapRemoveDowntimeModal.visible = true
  }

  async function doWorldmapRemoveDowntime(dt: DowntimeEntry): Promise<void> {
    if (!checkmkUrl.value) return
    try {
      await cmkApi.removeDowntimeById(checkmkUrl.value, dt.id, dt.site_id)
      toast.success(_t('Downtime removed'))
      statesStore.refreshAfterCommand()
    } catch {
      toast.error(_t('Failed to remove downtime'))
    }
  }

  function onWorldmapCtxAck(): void {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (obj) worldmapAckModal.value = obj
  }

  function onWorldmapCtxAddComment(): void {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (obj) worldmapCommentModal.value = obj
  }

  async function onWorldmapCtxRemoveAck(): Promise<void> {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (!obj || !checkmkUrl.value) return
    const siteId = statesStore.getState(obj.id)?.site_id ?? null
    try {
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        await cmkApi.removeAcknowledgementService(
          checkmkUrl.value,
          obj.host_name,
          obj.service_description,
          siteId
        )
      } else if (obj.host_name) {
        await cmkApi.removeAcknowledgementHost(checkmkUrl.value, obj.host_name, siteId)
      }
    } catch (err) {
      const detail = err instanceof Error ? err.message : ''
      toast.error(
        detail
          ? `${_t('Failed to remove acknowledgement')}: ${detail}`
          : _t('Failed to remove acknowledgement')
      )
    }
  }

  async function onWorldmapCtxToggleNotifications(enable: boolean): Promise<void> {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (!obj || !checkmkUrl.value) return
    const siteId = statesStore.getState(obj.id)?.site_id ?? null
    try {
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        await (enable ? cmkApi.enableNotificationsService : cmkApi.disableNotificationsService)(
          checkmkUrl.value,
          obj.host_name,
          obj.service_description,
          siteId
        )
      } else if (obj.host_name) {
        await (enable ? cmkApi.enableNotificationsHost : cmkApi.disableNotificationsHost)(
          checkmkUrl.value,
          obj.host_name,
          siteId
        )
      }
    } catch {
      toast.error(_t('Failed to toggle notifications'))
    }
  }

  async function onWorldmapCtxForceCheck(): Promise<void> {
    const obj = worldmapCtxMenu.object
    worldmapCtxMenu.visible = false
    if (!obj || !checkmkUrl.value) return
    const siteId = statesStore.getState(obj.id)?.site_id ?? null
    try {
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        await cmkApi.forceCheckService(
          checkmkUrl.value,
          obj.host_name,
          obj.service_description,
          siteId
        )
      } else if (obj.host_name) {
        await cmkApi.forceCheckHost(checkmkUrl.value, obj.host_name, siteId)
      }
    } catch {
      toast.error(_t('Force check failed'))
    }
  }

  function closeWorldmapMenus(): void {
    worldmapHoverGrace.cancelClose()
    worldmapHover.visible = false
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

  function closeWorldmapAckModal(): void {
    worldmapAckModal.value = null
    statesStore.refreshAfterCommand()
  }

  function closeWorldmapDowntimeModal(): void {
    worldmapDowntimeModal.value = null
    statesStore.refreshAfterCommand()
  }

  function closeWorldmapRemoveDowntimeModal(): void {
    worldmapRemoveDowntimeModal.visible = false
    statesStore.refreshAfterCommand()
  }

  return {
    worldmapHover,
    worldmapCtxMenu,
    worldmapCtxState,
    worldmapCanvasCtxMenu,
    worldmapHoverGrace,
    worldmapAckModal,
    worldmapDowntimeModal,
    worldmapCommentModal,
    worldmapRemoveDowntimeModal,
    onWorldmapHover,
    onWorldmapHoverLeave,
    onWorldmapContextMenuView,
    onWorldmapCtxEdit,
    onWorldmapCtxDelete,
    onWorldmapCtxDuplicate,
    onWorldmapCtxDetach,
    onWorldmapCtxDowntime,
    onWorldmapCtxRemoveDowntime,
    onWorldmapCtxAck,
    onWorldmapCtxAddComment,
    onWorldmapCtxRemoveAck,
    onWorldmapCtxToggleNotifications,
    onWorldmapCtxForceCheck,
    closeWorldmapMenus,
    onWorldmapCanvasContextMenu,
    onWorldmapCanvasCtxSaveAsDefault,
    closeWorldmapAckModal,
    closeWorldmapDowntimeModal,
    closeWorldmapRemoveDowntimeModal
  }
}
