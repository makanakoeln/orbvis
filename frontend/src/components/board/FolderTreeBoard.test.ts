import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { markRaw } from 'vue'

import { useStatesStore } from '@/stores/states'
import type { FolderTreeNode, FolderTreeView } from '@/types/api'

import FolderTreeBoard from './FolderTreeBoard.vue'

// The folder tree arrives via the central WS pipeline (statesStore.folderTree);
// boardsApi is only touched for view-preference persistence and lazy service
// fetches, both gated on a boardName prop we don't pass. Mock the API client so
// no store in the import graph can fetch for real.
vi.mock('@/api/client', () => ({
  ACCESS_TOKEN_KEY: 'orbvis_access_token',
  ApiError: class ApiError extends Error {},
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
    sso: vi.fn().mockRejectedValue(new Error('no sso'))
  },
  boardsApi: {
    update: vi.fn(),
    folderHostServices: vi.fn().mockResolvedValue([]),
    folderSearch: vi.fn().mockResolvedValue({ matches: [], truncated: false })
  },
  cmkApi: { command: vi.fn() },
  connectionsApi: { topology: vi.fn().mockResolvedValue([]) },
  metricsApi: { graph: vi.fn() },
  settingsApi: { get: vi.fn(), update: vi.fn() },
  systemSettingsApi: { get: vi.fn(), update: vi.fn() }
}))

function makeNode(overrides: Partial<FolderTreeNode> & { path: string }): FolderTreeNode {
  return {
    title: '',
    kind: 'folder',
    state: 'OK',
    is_empty: false,
    folder_id: '',
    host_count: 0,
    problem_count: 0,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    site_id: null,
    children: [],
    ...overrides
  }
}

// Root folder with one healthy and one problem host.
const sampleTree = (): FolderTreeNode =>
  makeNode({
    path: '/main',
    title: 'Main',
    kind: 'folder',
    host_count: 2,
    problem_count: 1,
    severity_counts: { DOWN: 1 },
    state: 'DOWN',
    children: [
      makeNode({ path: '/main/web-01', title: 'web-01', kind: 'host', state: 'UP' }),
      makeNode({
        path: '/main/db-01',
        title: 'db-01',
        kind: 'host',
        state: 'DOWN',
        output: 'PING CRITICAL'
      })
    ]
  })

const listView: FolderTreeView = { type: 'foldertree', default_view: 'list' }

function mountList() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const states = useStatesStore()
  states.folderTree = markRaw(sampleTree())
  states.connected = true
  return mount(FolderTreeBoard, {
    props: { view: listView },
    global: { plugins: [pinia], stubs: { BoardSearch: true } }
  })
}

describe('FolderTreeBoard (list mode)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal(
      'ResizeObserver',
      class {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
    // jsdom has no layout, so the virtualized list would measure a 0px
    // viewport. A fixed clientHeight gives the windowing a real viewport.
    Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
      configurable: true,
      get: () => 800
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    Reflect.deleteProperty(HTMLElement.prototype, 'clientHeight')
  })

  it('renders the root folder and both host rows in the virtual window', async () => {
    const wrapper = mountList()
    await flushPromises()

    const rows = wrapper.findAllComponents({ name: 'FolderTreeRow' })
    expect(rows).toHaveLength(3)
    const titles = rows.map((r) => r.find('.ft-title').text())
    expect(titles).toEqual(['Main', 'web-01', 'db-01'])
    // The full-height spacer drives the scrollbar: 3 rows × 28px.
    expect(wrapper.find('.ft-vlist').attributes('style')).toContain('height: 84px')
  })

  it('marks the problem host and shows the severity pill on the folder', async () => {
    const wrapper = mountList()
    await flushPromises()

    const rows = wrapper.findAllComponents({ name: 'FolderTreeRow' })
    const down = rows.find((r) => r.find('.ft-title').text() === 'db-01')
    expect(down).toBeDefined()
    expect(down!.find('.ft-dot').attributes('title')).toBe('DOWN')

    const folder = rows[0]!
    const pills = folder.findAll('.ft-pill')
    expect(pills).toHaveLength(1)
    expect(pills[0]!.attributes('title')).toBe('1 DOWN')
  })

  it('shows the host summary in the toolbar and the List mode as active', async () => {
    const wrapper = mountList()
    await flushPromises()

    expect(wrapper.find('.ft-summary').text()).toContain('2 hosts')
    expect(wrapper.find('.ft-summary-pill').text()).toBe('1 DOWN')
    expect(wrapper.find('.ft-seg--active').text()).toBe('List')
  })

  it('renders the waiting placeholder when no folder tree arrived yet', () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(FolderTreeBoard, {
      props: { view: listView },
      global: { plugins: [pinia], stubs: { BoardSearch: true } }
    })

    expect(wrapper.find('.ft-placeholder').text()).toContain('Waiting for folder data')
    expect(wrapper.findAllComponents({ name: 'FolderTreeRow' })).toHaveLength(0)
  })
})
