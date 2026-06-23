import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { MapObject, DowntimeEntry, ObjectState } from '@/types/api'

import { useObjectActions } from './useObjectActions'

const { cmkApi, toast, statesStub } = vi.hoisted(() => ({
  cmkApi: {
    forceCheckHost: vi.fn().mockResolvedValue(undefined),
    forceCheckService: vi.fn().mockResolvedValue(undefined),
    removeAcknowledgementHost: vi.fn().mockResolvedValue(undefined),
    removeAcknowledgementService: vi.fn().mockResolvedValue(undefined),
    enableNotificationsHost: vi.fn().mockResolvedValue(undefined),
    disableNotificationsHost: vi.fn().mockResolvedValue(undefined),
    enableNotificationsService: vi.fn().mockResolvedValue(undefined),
    disableNotificationsService: vi.fn().mockResolvedValue(undefined),
    listDowntimesHost: vi.fn().mockResolvedValue([]),
    listDowntimesService: vi.fn().mockResolvedValue([]),
    removeDowntimeById: vi.fn().mockResolvedValue(undefined)
  },
  toast: { success: vi.fn(), error: vi.fn() },
  statesStub: {
    state: undefined as ObjectState | undefined,
    refreshAfterCommand: vi.fn()
  }
}))

vi.mock('@/api/client', () => ({ cmkApi }))
vi.mock('@/composables/useToast', () => ({ useToast: () => toast }))
vi.mock('@/stores/states', () => ({
  useStatesStore: () => ({
    getState: () => statesStub.state,
    refreshAfterCommand: statesStub.refreshAfterCommand
  })
}))
vi.mock('@cmk/lib/i18n', () => ({ default: () => ({ _t: (s: string) => s }) }))

function hostObj(over: Partial<MapObject> = {}): MapObject {
  return { id: 'o1', type: 'host', host_name: 'web01', ...over } as MapObject
}
function serviceObj(over: Partial<MapObject> = {}): MapObject {
  return {
    id: 'o2',
    type: 'service',
    host_name: 'web01',
    service_description: 'CPU',
    ...over
  } as MapObject
}

const URL = 'https://cmk.example/site'

describe('useObjectActions — command dispatch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    statesStub.state = undefined
  })

  it('routes forceCheck on a service to the service endpoint with host+service+site', async () => {
    statesStub.state = { site_id: 'siteA' } as ObjectState
    const { handlers } = useObjectActions(URL)
    await handlers.forceCheck(serviceObj())
    expect(cmkApi.forceCheckService).toHaveBeenCalledWith(URL, 'web01', 'CPU', 'siteA')
    expect(cmkApi.forceCheckHost).not.toHaveBeenCalled()
    expect(toast.success).toHaveBeenCalledWith('Force check scheduled')
    expect(statesStub.refreshAfterCommand).toHaveBeenCalledOnce()
  })

  it('routes forceCheck on a host to the host endpoint', async () => {
    const { handlers } = useObjectActions(URL)
    await handlers.forceCheck(hostObj())
    expect(cmkApi.forceCheckHost).toHaveBeenCalledWith(URL, 'web01', null)
    expect(cmkApi.forceCheckService).not.toHaveBeenCalled()
  })

  it('prefers the live state-map site_id over the object-carried site_id', async () => {
    statesStub.state = { site_id: 'live' } as ObjectState
    const { handlers } = useObjectActions(URL)
    await handlers.forceCheck(hostObj({ site_id: 'stale' }))
    expect(cmkApi.forceCheckHost).toHaveBeenCalledWith(URL, 'web01', 'live')
  })

  it('falls back to the object site_id when no state-map entry exists', async () => {
    const { handlers } = useObjectActions(URL)
    await handlers.forceCheck(hostObj({ site_id: 'objsite' }))
    expect(cmkApi.forceCheckHost).toHaveBeenCalledWith(URL, 'web01', 'objsite')
  })

  it('does nothing for an object without a host name', async () => {
    const { handlers } = useObjectActions(URL)
    await handlers.forceCheck({ id: 'o1', type: 'host' } as MapObject)
    expect(cmkApi.forceCheckHost).not.toHaveBeenCalled()
    expect(cmkApi.forceCheckService).not.toHaveBeenCalled()
  })

  it('does nothing when no Checkmk URL is configured', async () => {
    const { handlers } = useObjectActions(null)
    await handlers.forceCheck(hostObj())
    expect(cmkApi.forceCheckHost).not.toHaveBeenCalled()
  })

  it('surfaces a backend error as an error toast with detail, no refresh', async () => {
    cmkApi.forceCheckHost.mockRejectedValueOnce(new Error('boom'))
    const { handlers } = useObjectActions(URL)
    await handlers.forceCheck(hostObj())
    expect(toast.error).toHaveBeenCalledWith('Force check failed: boom')
    expect(statesStub.refreshAfterCommand).not.toHaveBeenCalled()
  })

  it('toggleNotifications picks enable vs disable endpoints', async () => {
    const { handlers } = useObjectActions(URL)
    await handlers.toggleNotifications(hostObj(), true)
    expect(cmkApi.enableNotificationsHost).toHaveBeenCalled()
    await handlers.toggleNotifications(hostObj(), false)
    expect(cmkApi.disableNotificationsHost).toHaveBeenCalled()
  })

  it('removeAck routes host vs service', async () => {
    const { handlers } = useObjectActions(URL)
    await handlers.removeAck(serviceObj())
    expect(cmkApi.removeAcknowledgementService).toHaveBeenCalledWith(URL, 'web01', 'CPU', null)
  })
})

describe('useObjectActions — modal openers', () => {
  beforeEach(() => vi.clearAllMocks())

  it('acknowledge/scheduleDowntime/addComment stash the object on their modal refs', () => {
    const onStart = vi.fn()
    const a = useObjectActions(URL, onStart)
    a.handlers.acknowledge(hostObj({ id: 'a' }))
    a.handlers.scheduleDowntime(hostObj({ id: 'b' }))
    a.handlers.addComment(hostObj({ id: 'c' }))
    expect(a.ackModalObject.value?.id).toBe('a')
    expect(a.downtimeModalObject.value?.id).toBe('b')
    expect(a.commentModalObject.value?.id).toBe('c')
    expect(onStart).toHaveBeenCalledTimes(3)
  })
})

describe('useObjectActions — removeDowntime', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    statesStub.state = undefined
  })

  it('removes a sole downtime directly without opening the modal', async () => {
    cmkApi.listDowntimesHost.mockResolvedValueOnce([
      { id: 42, site_id: 'siteA' } as unknown as DowntimeEntry
    ])
    const a = useObjectActions(URL)
    await a.handlers.removeDowntime(hostObj())
    expect(cmkApi.removeDowntimeById).toHaveBeenCalledWith(URL, 42, 'siteA')
    expect(a.removeDowntimeModal.visible).toBe(false)
    expect(toast.success).toHaveBeenCalledWith('Downtime removed')
  })

  it('opens the picker modal when several downtimes exist', async () => {
    cmkApi.listDowntimesHost.mockResolvedValueOnce([
      { id: 1, site_id: 's' },
      { id: 2, site_id: 's' }
    ] as unknown as DowntimeEntry[])
    const a = useObjectActions(URL)
    await a.handlers.removeDowntime(hostObj())
    expect(cmkApi.removeDowntimeById).not.toHaveBeenCalled()
    expect(a.removeDowntimeModal.visible).toBe(true)
    expect(a.removeDowntimeModal.downtimes).toHaveLength(2)
  })

  it('reports when there are no active downtimes', async () => {
    cmkApi.listDowntimesHost.mockResolvedValueOnce([])
    const a = useObjectActions(URL)
    await a.handlers.removeDowntime(hostObj())
    expect(toast.error).toHaveBeenCalledWith('No active downtimes found')
    expect(cmkApi.removeDowntimeById).not.toHaveBeenCalled()
  })
})
