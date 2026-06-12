import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/auth'

import { clearDataBindingCache, useDataBinding } from './useDataBinding'

const { mockConnectionsApi } = vi.hoisted(() => ({
  mockConnectionsApi: {
    objects: vi.fn(),
    perfMetrics: vi.fn(),
    aggregations: vi.fn()
  }
}))

vi.mock('@/api/client', () => ({
  connectionsApi: mockConnectionsApi
}))

describe('useDataBinding', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useAuthStore().accessToken = 'tok'
    clearDataBindingCache()
    mockConnectionsApi.objects.mockReset()
    mockConnectionsApi.perfMetrics.mockReset()
  })

  it('caches host lookups per connection', async () => {
    mockConnectionsApi.objects.mockResolvedValue(['web01', 'web02'])
    const b = useDataBinding(() => 'live_1')
    expect(await b.hosts()).toEqual(['web01', 'web02'])
    expect(await b.hosts()).toEqual(['web01', 'web02'])
    expect(mockConnectionsApi.objects).toHaveBeenCalledTimes(1)

    const other = useDataBinding(() => 'live_2')
    await other.hosts()
    expect(mockConnectionsApi.objects).toHaveBeenCalledTimes(2)
  })

  it('caches services per host and metrics per host/service', async () => {
    mockConnectionsApi.objects.mockResolvedValue(['CPU load'])
    const choices = [
      { name: 'load1', title: 'CPU load average of last minute' },
      { name: 'load5', title: 'CPU load average of last 5 minutes' }
    ]
    mockConnectionsApi.perfMetrics.mockResolvedValue(choices)
    const b = useDataBinding(() => 'live_1')
    await b.services('web01')
    await b.services('web01')
    expect(mockConnectionsApi.objects).toHaveBeenCalledTimes(1)
    expect(await b.metrics('web01', 'CPU load')).toEqual(choices)
    await b.metrics('web01', 'CPU load')
    expect(mockConnectionsApi.perfMetrics).toHaveBeenCalledTimes(1)
    await b.metrics('web01')
    expect(mockConnectionsApi.perfMetrics).toHaveBeenCalledTimes(2)
  })

  it('returns [] on failure and retries on the next call instead of pinning the error', async () => {
    mockConnectionsApi.objects.mockRejectedValueOnce(new Error('boom'))
    mockConnectionsApi.objects.mockResolvedValueOnce(['web01'])
    const b = useDataBinding(() => 'live_1')
    expect(await b.hosts()).toEqual([])
    expect(await b.hosts()).toEqual(['web01'])
  })

  it('serves groups and BI aggregations from their own cached sources', async () => {
    mockConnectionsApi.objects.mockResolvedValue(['linux'])
    mockConnectionsApi.aggregations.mockResolvedValue([
      { id: 'aggr1', title: 'Web shop', pack_id: 'default' }
    ])
    const b = useDataBinding(() => 'live_1')
    expect(await b.hostgroups()).toEqual(['linux'])
    expect(mockConnectionsApi.objects).toHaveBeenCalledWith('live_1', 'hostgroup', 'tok')
    await b.servicegroups()
    expect(mockConnectionsApi.objects).toHaveBeenCalledWith('live_1', 'servicegroup', 'tok')
    const aggs = await b.aggregations()
    expect(aggs[0]!.title).toBe('Web shop')
    await b.aggregations()
    expect(mockConnectionsApi.aggregations).toHaveBeenCalledTimes(1)
  })

  it('short-circuits without a connection or host', async () => {
    const b = useDataBinding(() => '')
    expect(await b.hosts()).toEqual([])
    const c = useDataBinding(() => 'live_1')
    expect(await c.services('')).toEqual([])
    expect(mockConnectionsApi.objects).not.toHaveBeenCalled()
  })
})
