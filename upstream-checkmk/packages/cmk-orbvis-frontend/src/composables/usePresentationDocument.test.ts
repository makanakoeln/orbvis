import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import { useAuthStore } from '@/stores/auth'
import type { MapConfig, PresentationView } from '@/types/api'
import { createElement } from '@/utils/presentationElements'

import { usePresentationDocument } from './usePresentationDocument'

// The composable registers onBeforeUnmount, so it must run inside a component
// setup — calling it bare warns. Run it in a throwaway component and hand back
// the returned document API.
function withDoc(): ReturnType<typeof usePresentationDocument> {
  let doc!: ReturnType<typeof usePresentationDocument>
  mount(
    defineComponent({
      setup() {
        doc = usePresentationDocument(makeConfig)
        return () => h('div')
      }
    })
  )
  return doc
}

const { mockMapsApi } = vi.hoisted(() => ({
  mockMapsApi: {
    update: vi.fn(),
    get: vi.fn()
  }
}))

vi.mock('@/api/client', () => ({
  mapsApi: mockMapsApi
}))

function makeConfig(): MapConfig {
  const view: PresentationView = {
    type: 'presentation',
    width: 1920,
    height: 1080,
    theme: 'midnight',
    elements: []
  }
  return { name: 'pres1', alias: 'P', connection_id: 'live_1', version: 3, view } as MapConfig
}

describe('usePresentationDocument', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    useAuthStore().accessToken = 'tok'
    mockMapsApi.update.mockReset()
    mockMapsApi.get.mockReset()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('mutate records a history step; undo restores elements and theme together', () => {
    const doc = withDoc()
    const el = createElement('rect', 10, 10)

    doc.mutate(() => {
      doc.local.value = { ...doc.local.value, theme: 'ops', elements: [el] }
    })
    expect(doc.elements.value).toHaveLength(1)
    expect(doc.local.value.theme).toBe('ops')

    doc.undo()
    expect(doc.elements.value).toHaveLength(0)
    expect(doc.local.value.theme).toBe('midnight')

    doc.redo()
    expect(doc.elements.value).toHaveLength(1)
    expect(doc.local.value.theme).toBe('ops')
  })

  it('debounces saves and adopts the returned version', async () => {
    mockMapsApi.update.mockResolvedValue({ name: 'pres1', version: 4, view: {} })
    const doc = withDoc()

    doc.mutate(() => doc.setElements([createElement('rect', 0, 0)]))
    doc.mutate(() => doc.setElements([...doc.elements.value, createElement('text', 0, 0)]))
    expect(mockMapsApi.update).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(500)
    expect(mockMapsApi.update).toHaveBeenCalledTimes(1)
    expect(mockMapsApi.update).toHaveBeenCalledWith('pres1', expect.anything(), 'tok', 3)
    expect(doc.version.value).toBe(4)
  })

  it('realigns to the canonical version after a conflicting save', async () => {
    mockMapsApi.update.mockRejectedValue(new Error('409'))
    mockMapsApi.get.mockResolvedValue({ name: 'pres1', version: 9, view: {} })
    const doc = withDoc()

    doc.mutate(() => doc.setElements([createElement('rect', 0, 0)]))
    await vi.advanceTimersByTimeAsync(500)

    expect(mockMapsApi.get).toHaveBeenCalledWith('pres1', 'tok')
    expect(doc.version.value).toBe(9)
    // The working copy survives — the conflict realigns the version only.
    expect(doc.elements.value).toHaveLength(1)
  })

  it('exposes shared lookups (byId, topLevelId, nextZ)', () => {
    const doc = withDoc()
    const a = createElement('rect', 0, 0)
    a.z = 5
    const group = createElement('rect', 0, 0)
    doc.setElements([a])
    expect(doc.byId(a.id)?.id).toBe(a.id)
    expect(doc.byId(undefined)).toBeUndefined()
    expect(doc.topLevelId(a.id)).toBe(a.id)
    expect(doc.nextZ.value).toBe(6)
    expect(doc.byId(group.id)).toBeUndefined()
  })
})
