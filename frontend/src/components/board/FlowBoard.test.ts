import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useStatesStore } from '@/stores/states'
import type { TopologyNode } from '@/types/api'

import FlowBoard from './FlowBoard.vue'

// The flow board pulls its data from the central WS pipeline via
// statesStore.topology; the REST topology endpoint is only a fallback. The
// whole API client is mocked so neither path (nor the auth/settings stores in
// the import graph) ever performs a real fetch.
vi.mock('@/api/client', () => ({
  ACCESS_TOKEN_KEY: 'orbvis_access_token',
  ApiError: class ApiError extends Error {},
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
    sso: vi.fn().mockRejectedValue(new Error('no sso')),
    streamTicket: vi.fn().mockResolvedValue({ ticket: 't', expires_in: 300 })
  },
  boardsApi: { update: vi.fn(), states: vi.fn() },
  cmkApi: { command: vi.fn() },
  connectionsApi: { topology: vi.fn().mockResolvedValue([]) },
  metricsApi: { graph: vi.fn() },
  settingsApi: { get: vi.fn(), update: vi.fn() },
  systemSettingsApi: { get: vi.fn(), update: vi.fn() }
}))

// Hierarchical 3-host topology: core is the root, web-01/db-01 hang off it.
// core carries a services_summary so the donut layout renders ring segments.
const sampleTopology = (): TopologyNode[] => [
  {
    name: 'core',
    parents: [],
    state: 'UP',
    output: 'PING OK',
    services_summary: { ok: 3, warning: 0, critical: 1, unknown: 0, pending: 0 }
  },
  { name: 'web-01', parents: ['core'], state: 'UP', output: 'PING OK' },
  { name: 'db-01', parents: ['core'], state: 'DOWN', output: 'PING CRITICAL' }
]

// Overlay components are not under test here; stubbing them keeps the smoke
// test focused on FlowBoard's own d3 render pipeline.
const stubs = {
  BoardSearch: true,
  BoardZoomResetPill: true,
  ContextMenu: true,
  DetailDrawer: true,
  HoverMenu: true
}

const baseProps = {
  connectionId: 'test',
  serviceLayout: 'donut' as const
}

function mountWithTopology() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const states = useStatesStore()
  states.topology = sampleTopology()
  states.topologyReady = true
  return mount(FlowBoard, { props: baseProps, global: { plugins: [pinia], stubs } })
}

describe('FlowBoard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // jsdom has no layout: getBBox / getBoundingClientRect on SVG elements
    // would throw or return zeros. d3 itself is pure JS and runs as-is.
    Object.defineProperty(SVGElement.prototype, 'getBBox', {
      configurable: true,
      value: () => ({ x: 0, y: 0, width: 10, height: 10 })
    })
    // d3-zoom's defaultExtent reads svg.width/height.baseVal, which jsdom's
    // SVGSVGElement does not implement.
    for (const dim of ['width', 'height'] as const) {
      Object.defineProperty(SVGSVGElement.prototype, dim, {
        configurable: true,
        get: () => ({ baseVal: { value: dim === 'width' ? 900 : 600 } })
      })
    }
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    Reflect.deleteProperty(SVGElement.prototype, 'getBBox')
    Reflect.deleteProperty(SVGSVGElement.prototype, 'width')
    Reflect.deleteProperty(SVGSVGElement.prototype, 'height')
  })

  it('renders one d3 node per host plus the synthetic site root', async () => {
    const wrapper = mountWithTopology()
    await flushPromises()

    const svg = wrapper.find('svg.orb-flow__svg')
    expect(svg.exists()).toBe(true)
    expect(svg.findAll('g.node.node-host')).toHaveLength(3)
    expect(svg.findAll('g.node.node-site')).toHaveLength(1)

    const labels = svg.findAll('g.node text.node-label').map((t) => t.text())
    expect(labels).toEqual(expect.arrayContaining(['core', 'web-01', 'db-01', 'test']))

    wrapper.unmount()
  })

  it('draws parent-child links and site links as lines', async () => {
    const wrapper = mountWithTopology()
    await flushPromises()

    // 2 parent→child links (core→web-01, core→db-01) + 1 site→root link.
    expect(wrapper.findAll('g.links line')).toHaveLength(3)

    wrapper.unmount()
  })

  it('renders donut ring segments from the services_summary in donut layout', async () => {
    const wrapper = mountWithTopology()
    await flushPromises()

    // core: ok=3 + critical=1 → two arcs; the other hosts have no summary.
    expect(wrapper.findAll('g.donut path')).toHaveLength(2)

    wrapper.unmount()
  })

  it('unmounts cleanly while the force simulation is still settling', async () => {
    const wrapper = mountWithTopology()
    await flushPromises()

    wrapper.unmount()
    // Let any stray simulation/zoom rAF or timer callbacks fire — a stopped
    // simulation must not tick (and must not throw) after unmount.
    await new Promise((resolve) => setTimeout(resolve, 60))
    expect(wrapper.exists()).toBe(false)
  })
})
