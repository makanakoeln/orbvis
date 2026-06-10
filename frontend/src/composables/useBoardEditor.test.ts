// @vitest-environment jsdom
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, ref } from 'vue'

import { useBoardsStore } from '@/stores/boards'
import type { BoardConfig, BoardObject } from '@/types/api'

import { useBoardEditor } from './useBoardEditor'

const { mockBoardsApi } = vi.hoisted(() => ({
  mockBoardsApi: {
    updateObject: vi.fn().mockResolvedValue({}),
    deleteObject: vi.fn().mockResolvedValue({})
  }
}))

vi.mock('@/api/client', () => ({
  boardsApi: mockBoardsApi,
  authApi: { login: vi.fn(), sso: vi.fn(), me: vi.fn(), refresh: vi.fn(), logout: vi.fn() },
  settingsApi: { get: vi.fn(), update: vi.fn() },
  connectionsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() }
}))
vi.mock('@/router', () => ({
  default: { push: vi.fn(), currentRoute: { value: { query: {} } } }
}))
vi.mock('@/i18n', () => ({ i18n: { global: { locale: { value: 'en' } } } }))

function makeObject(o: Partial<BoardObject> & { id: string; type: string }): BoardObject {
  return o as BoardObject
}

// A canvas element whose mouse→board mapping is the identity (rect at origin,
// no native-image dims so the scroll-based branch in _mouseToCanvas applies).
function makeCanvas(): HTMLElement {
  const el = document.createElement('div')
  document.body.appendChild(el)
  el.getBoundingClientRect = () =>
    ({ left: 0, top: 0, width: 1000, height: 1000, right: 1000, bottom: 1000 }) as DOMRect
  return el
}

function mouse(clientX: number, clientY: number): MouseEvent {
  return new MouseEvent('mousedown', { clientX, clientY })
}

describe('useBoardEditor line drag — bound endpoints', () => {
  let mapName: Ref<string>

  beforeEach(() => {
    setActivePinia(createPinia())
    mapName = ref('board1')
    mockBoardsApi.updateObject.mockClear()
  })

  afterEach(() => {
    // End any in-flight drag so the composable tears down its document
    // listeners before the canvas element is removed (avoids a cross-test leak).
    document.dispatchEvent(new MouseEvent('mouseup'))
    document.body.innerHTML = ''
  })

  // Regression: a line bound to an object renders at the object's *live*
  // position (BoardCanvas.boundCoordsFor), but the line's stored x/y is only a
  // bind-time fallback. After the object moves, that stored coordinate is stale.
  // Grabbing the line must seed the drag from the live object, not the stale
  // coordinate, or the endpoint snaps wildly across the canvas.
  function boardWithStaleBoundLine(): BoardConfig {
    const host = makeObject({ id: 'host1', type: 'host', x: 500, y: 400 })
    const line = makeObject({
      id: 'line1',
      type: 'line',
      // Stale bind-time coordinate — the host has since moved to (500, 400).
      x: 200,
      y: 100,
      x2: 700,
      y2: 600,
      start_ref: 'host1',
      end_ref: null
    })
    return { objects: [host, line] } as unknown as BoardConfig
  }

  it('seeds a move drag of a bound line from the live object, not the stale stored coord', () => {
    const store = useBoardsStore()
    store.currentBoard = boardWithStaleBoundLine()
    const editor = useBoardEditor(mapName, async () => {})
    const line = store.currentBoard.objects.find((o) => o.id === 'line1')!

    editor.startLineDrag(mouse(300, 300), line, 'move', makeCanvas())

    const seeded = editor.lineDragPositions['line1']!
    expect(seeded.x).toBe(500) // live host x, not stale 200
    expect(seeded.y).toBe(400) // live host y, not stale 100
  })

  it('keeps the bound endpoint glued to the live object while the line is moved', () => {
    const store = useBoardsStore()
    store.currentBoard = boardWithStaleBoundLine()
    const editor = useBoardEditor(mapName, async () => {})
    const line = store.currentBoard.objects.find((o) => o.id === 'line1')!

    editor.startLineDrag(mouse(300, 300), line, 'move', makeCanvas())
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 360, clientY: 320 }))

    const dragged = editor.lineDragPositions['line1']!
    // Bound start stays on the host; the free end follows the cursor delta.
    expect(dragged.x).toBe(500)
    expect(dragged.y).toBe(400)
    expect(dragged.x2).toBe(760) // 700 + 60
    expect(dragged.y2).toBe(620) // 600 + 20
  })

  it('seeds a start-handle drag of a bound endpoint from the live object', () => {
    const store = useBoardsStore()
    store.currentBoard = boardWithStaleBoundLine()
    const editor = useBoardEditor(mapName, async () => {})
    const line = store.currentBoard.objects.find((o) => o.id === 'line1')!

    editor.startLineDrag(mouse(300, 300), line, 'start', makeCanvas())

    const seeded = editor.lineDragPositions['line1']!
    expect(seeded.x).toBe(500)
    expect(seeded.y).toBe(400)
  })
})
