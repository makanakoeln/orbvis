import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import type { BoardConfig, ObjectState } from '@/types/api'

import WorldMapCanvas from './WorldMapCanvas.vue'

// Minimal Leaflet stand-in covering exactly what WorldMapCanvas touches during
// mount (L.map / tileLayer / divIcon / marker + syncMarkers/syncLines) and
// unmount (map.remove). jsdom has no real layout, so nothing renders for real.
const leaflet = vi.hoisted(() => {
  const mapStub = {
    on: vi.fn(),
    remove: vi.fn(),
    getPane: vi.fn(() => undefined),
    fitBounds: vi.fn(),
    getCenter: vi.fn(() => ({ lat: 51, lng: 10 })),
    getZoom: vi.fn(() => 5),
    setView: vi.fn(),
    invalidateSize: vi.fn(),
    boxZoom: { disable: vi.fn() },
    dragging: { enable: vi.fn(), disable: vi.fn() },
    mouseEventToContainerPoint: vi.fn(() => ({ x: 0, y: 0 })),
    latLngToContainerPoint: vi.fn(() => ({ x: 0, y: 0, distanceTo: () => 0 })),
    containerPointToLatLng: vi.fn(() => ({ lat: 0, lng: 0 }))
  }
  const makeMarker = () => ({
    on: vi.fn(),
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
    setLatLng: vi.fn(),
    setIcon: vi.fn(),
    setZIndexOffset: vi.fn(),
    setOpacity: vi.fn(),
    getLatLng: vi.fn(() => ({ lat: 0, lng: 0 })),
    getElement: vi.fn(() => null),
    dragging: { enable: vi.fn(), disable: vi.fn() }
  })
  const makePolyline = () => ({
    on: vi.fn(),
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
    setLatLngs: vi.fn(),
    setStyle: vi.fn(),
    bringToFront: vi.fn(),
    getElement: vi.fn(() => null)
  })
  const makeTileLayer = () => ({
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
    setUrl: vi.fn()
  })
  const L = {
    map: vi.fn(() => mapStub),
    tileLayer: vi.fn(makeTileLayer),
    marker: vi.fn(makeMarker),
    polyline: vi.fn(makePolyline),
    divIcon: vi.fn((opts: { html?: string }) => opts),
    point: vi.fn((x: number, y: number) => ({ x, y, distanceTo: () => 0 })),
    latLngBounds: vi.fn((pts: unknown) => pts),
    DomEvent: { stopPropagation: vi.fn(), preventDefault: vi.fn() }
  }
  return { L, mapStub }
})

vi.mock('leaflet', () => ({ default: leaflet.L }))

vi.mock('@/api/client', () => ({
  ACCESS_TOKEN_KEY: 'orbvis_access_token',
  ApiError: class ApiError extends Error {},
  authApi: {
    streamTicket: vi.fn().mockResolvedValue({ ticket: 'tile-ticket', expires_in: 300 }),
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
    sso: vi.fn().mockRejectedValue(new Error('no sso'))
  },
  settingsApi: { get: vi.fn(), update: vi.fn() },
  systemSettingsApi: { get: vi.fn(), update: vi.fn() }
}))

const sampleConfig = (): BoardConfig => ({
  name: 'geo',
  alias: 'Geo',
  icon_size: 30,
  connection_id: 'test',
  rotation_interval: 0,
  sort_order: 0,
  click_action: 'link',
  view: { type: 'worldmap', lat: 51, lng: 10, zoom: 5 },
  objects: [
    {
      id: 'h1',
      type: 'host',
      x: 0,
      y: 0,
      lat: 52.52,
      lng: 13.405,
      host_name: 'berlin-host',
      url_target: '_blank',
      z: 1
    }
  ]
})

const sampleStates: Record<string, ObjectState> = {
  h1: {
    object_id: 'h1',
    type: 'host',
    state: 'UP',
    output: 'PING OK',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false
  }
}

const baseProps = {
  config: sampleConfig(),
  states: sampleStates,
  editMode: false,
  placing: false,
  selectedObjectId: null
}

describe('WorldMapCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  it('mounts a Leaflet map and creates one marker per geo object', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.accessToken = 'token'

    const wrapper = mount(WorldMapCanvas, {
      props: { ...baseProps, config: sampleConfig() },
      global: { plugins: [pinia] }
    })
    await flushPromises()

    expect(wrapper.find('.orb-worldmap__map').exists()).toBe(true)
    expect(leaflet.L.map).toHaveBeenCalledTimes(1)
    expect(leaflet.L.tileLayer).toHaveBeenCalled()
    expect(leaflet.L.marker).toHaveBeenCalledTimes(1)
    expect(leaflet.L.marker).toHaveBeenCalledWith([52.52, 13.405], expect.anything())
    // The marker's divIcon HTML carries the object id the action bar anchors on.
    const iconHtml = leaflet.L.divIcon.mock.calls.map((c) => c[0]?.html ?? '').join('')
    expect(iconHtml).toContain('data-object-id="h1"')

    wrapper.unmount()
    expect(leaflet.mapStub.remove).toHaveBeenCalledTimes(1)
  })

  it('unmounts cleanly even before the async mount setup resolved', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)

    const wrapper = mount(WorldMapCanvas, {
      props: { ...baseProps, config: sampleConfig() },
      global: { plugins: [pinia] }
    })
    wrapper.unmount()
    await flushPromises()
    expect(wrapper.exists()).toBe(false)
  })
})
