import { type MaybeRefOrGetter, reactive, ref, toValue } from 'vue'

import { cmkApi } from '@/api/client'
import { useToast } from '@/composables/useToast'
import { useStatesStore } from '@/stores/states'
import type { BoardObject, DowntimeEntry } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

interface DispatchOptions {
  hostFn: (baseUrl: string, hostname: string, siteId?: string | null) => Promise<void>
  serviceFn: (
    baseUrl: string,
    hostname: string,
    service: string,
    siteId?: string | null
  ) => Promise<void>
  errorText: string
  successText?: string
}

export interface UseObjectActions {
  ackModalObject: ReturnType<typeof ref<BoardObject | null>>
  downtimeModalObject: ReturnType<typeof ref<BoardObject | null>>
  commentModalObject: ReturnType<typeof ref<BoardObject | null>>
  removeDowntimeModal: { visible: boolean; downtimes: DowntimeEntry[]; objectName: string }
  closeAckModal(): void
  closeDowntimeModal(): void
  closeRemoveDowntimeModal(): void
  handlers: {
    acknowledge(obj: BoardObject | null): void
    removeAck(obj: BoardObject | null): Promise<void>
    scheduleDowntime(obj: BoardObject | null): void
    removeDowntime(obj: BoardObject | null): Promise<void>
    addComment(obj: BoardObject | null): void
    forceCheck(obj: BoardObject | null): Promise<void>
    toggleNotifications(obj: BoardObject | null, enable: boolean): Promise<void>
  }
}

/**
 * Shared cmkApi-action plumbing for board context menus. Holds modal-state and
 * the host/service dispatch boilerplate so BoardCanvas and FlowBoard don't each
 * re-implement the same seven handlers.
 */
export function useObjectActions(
  checkmkUrl: MaybeRefOrGetter<string | null | undefined>,
  onActionStart?: () => void
): UseObjectActions {
  const { _t } = usei18n()
  const toast = useToast()
  const statesStore = useStatesStore()

  const ackModalObject = ref<BoardObject | null>(null)
  const downtimeModalObject = ref<BoardObject | null>(null)
  const commentModalObject = ref<BoardObject | null>(null)
  const removeDowntimeModal = reactive<{
    visible: boolean
    downtimes: DowntimeEntry[]
    objectName: string
  }>({ visible: false, downtimes: [], objectName: '' })

  function start(): string | null {
    onActionStart?.()
    const url = toValue(checkmkUrl)
    return url ?? null
  }

  async function dispatchHostOrService(
    url: string,
    obj: BoardObject,
    { hostFn, serviceFn, errorText, successText }: DispatchOptions
  ): Promise<void> {
    try {
      // Prefer the live state-map site_id; fall back to a site_id carried
      // on the object itself (the Flow Board has no state-map entry but
      // tags its objects with the topology node's site).
      const siteId = statesStore.getState(obj.id)?.site_id ?? obj.site_id ?? null
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        await serviceFn(url, obj.host_name, obj.service_description, siteId)
      } else if (obj.host_name) {
        await hostFn(url, obj.host_name, siteId)
      } else {
        return
      }
      if (successText) toast.success(successText)
      statesStore.refreshAfterCommand()
    } catch (err) {
      const detail = err instanceof Error ? err.message : ''
      toast.error(detail ? `${errorText}: ${detail}` : errorText)
    }
  }

  function acknowledge(obj: BoardObject | null): void {
    start()
    if (obj) ackModalObject.value = obj
  }

  async function removeAck(obj: BoardObject | null): Promise<void> {
    const url = start()
    if (!obj || !url) return
    await dispatchHostOrService(url, obj, {
      hostFn: cmkApi.removeAcknowledgementHost,
      serviceFn: cmkApi.removeAcknowledgementService,
      errorText: _t('Failed to remove acknowledgement')
    })
  }

  function scheduleDowntime(obj: BoardObject | null): void {
    start()
    if (obj) downtimeModalObject.value = obj
  }

  async function removeDowntime(obj: BoardObject | null): Promise<void> {
    const url = start()
    if (!obj || !url) return
    let downtimes: DowntimeEntry[]
    try {
      if (obj.type === 'service' && obj.host_name && obj.service_description) {
        downtimes = await cmkApi.listDowntimesService(url, obj.host_name, obj.service_description)
      } else if (obj.host_name) {
        downtimes = await cmkApi.listDowntimesHost(url, obj.host_name)
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
    const single = downtimes.length === 1 ? downtimes[0] : undefined
    if (single !== undefined) {
      try {
        await cmkApi.removeDowntimeById(url, single.id, single.site_id)
        toast.success(_t('Downtime removed'))
        statesStore.refreshAfterCommand()
      } catch {
        toast.error(_t('Failed to remove downtime'))
      }
      return
    }
    removeDowntimeModal.downtimes = downtimes
    removeDowntimeModal.objectName = obj.host_name ?? ''
    removeDowntimeModal.visible = true
  }

  function addComment(obj: BoardObject | null): void {
    start()
    if (obj) commentModalObject.value = obj
  }

  async function forceCheck(obj: BoardObject | null): Promise<void> {
    const url = start()
    if (!obj || !url) return
    await dispatchHostOrService(url, obj, {
      hostFn: cmkApi.forceCheckHost,
      serviceFn: cmkApi.forceCheckService,
      errorText: _t('Force check failed'),
      successText: _t('Force check scheduled')
    })
  }

  async function toggleNotifications(obj: BoardObject | null, enable: boolean): Promise<void> {
    const url = start()
    if (!obj || !url) return
    await dispatchHostOrService(url, obj, {
      hostFn: enable ? cmkApi.enableNotificationsHost : cmkApi.disableNotificationsHost,
      serviceFn: enable ? cmkApi.enableNotificationsService : cmkApi.disableNotificationsService,
      errorText: _t('Failed to toggle notifications'),
      successText: _t('Notifications updated')
    })
  }

  // Modal close = command finished (or aborted) — refresh so the board
  // reflects the acknowledged/downtimed state without waiting a full tick.
  function closeAckModal(): void {
    ackModalObject.value = null
    statesStore.refreshAfterCommand()
  }

  function closeDowntimeModal(): void {
    downtimeModalObject.value = null
    statesStore.refreshAfterCommand()
  }

  function closeRemoveDowntimeModal(): void {
    removeDowntimeModal.visible = false
    statesStore.refreshAfterCommand()
  }

  return {
    ackModalObject,
    downtimeModalObject,
    commentModalObject,
    removeDowntimeModal,
    closeAckModal,
    closeDowntimeModal,
    closeRemoveDowntimeModal,
    handlers: {
      acknowledge,
      removeAck,
      scheduleDowntime,
      removeDowntime,
      addComment,
      forceCheck,
      toggleNotifications
    }
  }
}
