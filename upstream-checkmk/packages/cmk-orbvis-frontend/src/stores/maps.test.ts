import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { MapConfig, MapRead } from '@/types/api'

import { useMapsStore } from './maps'

const { mockMapsApi } = vi.hoisted(() => ({
  mockMapsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    delete: vi.fn()
  }
}))

vi.mock('@/api/client', () => ({
  mapsApi: mockMapsApi,
  authApi: {
    login: vi.fn(),
    sso: vi.fn().mockRejectedValue(new Error('no sso')),
    me: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn()
  },
  settingsApi: { get: vi.fn(), update: vi.fn() },
  connectionsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() }
}))

vi.mock('@/router', () => ({
  default: { push: vi.fn(), currentRoute: { value: { query: {} } } }
}))
vi.mock('@/i18n', () => ({ i18n: { global: { locale: { value: 'en' } } } }))

const sampleMaps: MapRead[] = [
  {
    name: 'map1',
    alias: 'Map 1',
    background_image: null,
    icon_size: 30,
    connection_id: 'live_1',
    view_type: 'static',
    view: { type: 'static' },
    object_count: 0,
    rotation_interval: 0,
    sort_order: 0,
    click_action: 'link',
    readonly: false,
    show_in_lists: true,
    hover_template: null,
    context_template: null
  }
]

const sampleConfig: MapConfig = {
  name: 'map1',
  alias: 'Map 1',
  icon_size: 30,
  connection_id: 'live_1',
  rotation_interval: 0,
  sort_order: 0,
  click_action: 'link',
  view: { type: 'static' },
  objects: []
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('useMapsStore', () => {
  it('starts with empty maps', () => {
    const store = useMapsStore()
    expect(store.maps).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchMaps() populates maps on success', async () => {
    mockMapsApi.list.mockResolvedValue(sampleMaps)
    const store = useMapsStore()
    await store.fetchMaps()
    expect(store.maps).toEqual(sampleMaps)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchMaps() sets error on failure', async () => {
    mockMapsApi.list.mockRejectedValue(new Error('Network error'))
    const store = useMapsStore()
    await store.fetchMaps()
    expect(store.error).toBe('Network error')
    expect(store.loading).toBe(false)
    expect(store.maps).toEqual([])
  })

  it('fetchMap() clears currentMap immediately', async () => {
    const store = useMapsStore()
    store.currentMap = sampleConfig
    mockMapsApi.get.mockResolvedValue(sampleConfig)

    const fetchPromise = store.fetchMap('map1')
    expect(store.currentMap).toBeNull()
    await fetchPromise
    expect(store.currentMap).toEqual(sampleConfig)
  })

  it('fetchMap() sets error on failure', async () => {
    mockMapsApi.get.mockRejectedValue(new Error('Not found'))
    const store = useMapsStore()
    await store.fetchMap('nonexistent')
    expect(store.error).toBe('Not found')
    expect(store.currentMap).toBeNull()
  })

  it('createMap() appends the new map in place without re-fetching', async () => {
    mockMapsApi.create.mockResolvedValue(sampleConfig)
    const store = useMapsStore()
    const result = await store.createMap('map1', 'Map 1')
    expect(mockMapsApi.create).toHaveBeenCalled()
    // In-place append: no extra list() round-trip.
    expect(mockMapsApi.list).not.toHaveBeenCalled()
    expect(store.maps).toHaveLength(1)
    expect(store.maps[0]!.name).toBe('map1')
    expect(result).toEqual(sampleConfig)
  })

  it('deleteMap() removes the map in place without re-fetching', async () => {
    mockMapsApi.list.mockResolvedValue(sampleMaps)
    mockMapsApi.delete.mockResolvedValue(undefined)
    const store = useMapsStore()
    await store.fetchMaps()
    mockMapsApi.list.mockClear()

    await store.deleteMap('map1')
    expect(mockMapsApi.delete).toHaveBeenCalledWith('map1', expect.any(String))
    // No extra list() round-trip — map is removed in place.
    expect(mockMapsApi.list).not.toHaveBeenCalled()
    expect(store.maps).toEqual([])
  })
})
