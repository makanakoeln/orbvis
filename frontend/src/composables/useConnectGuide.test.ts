import { describe, expect, it } from 'vitest'
import { nextTick, ref } from 'vue'

import type { DataElement, PresentationElement } from '@/types/api'
import { createElement } from '@/utils/presentationElements'

import { useConnectGuide } from './useConnectGuide'

function slot(x: number, y: number): DataElement {
  const el = createElement('data', x, y)
  if (el.kind !== 'data') throw new Error('unreachable')
  return el
}

function setup(initial: PresentationElement[]) {
  const elements = ref<PresentationElement[]>(initial)
  const guide = useConnectGuide(() => elements.value)
  return { elements, guide }
}

describe('useConnectGuide', () => {
  it('orders slots in reading order (rows top→bottom, then left→right)', () => {
    const a = slot(900, 30)
    const b = slot(100, 40)
    const c = slot(100, 500)
    const { guide } = setup([c, a, b])
    expect(guide.slots.value.map((s) => s.id)).toEqual([b.id, a.id, c.id])
  })

  it('enters on the first slot and tracks progress', () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { guide } = setup([a, b])
    guide.enter()
    expect(guide.active.value).toBe(true)
    expect(guide.totalCount.value).toBe(2)
    expect(guide.boundCount.value).toBe(0)
    expect(guide.currentId.value).toBe(a.id)
  })

  it('does not activate without any unbound slot', () => {
    const bound = slot(0, 0)
    bound.host_name = 'web01'
    const { guide } = setup([bound])
    guide.enter()
    expect(guide.active.value).toBe(false)
  })

  it('next/prev cycle through the slots', () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { guide } = setup([a, b])
    guide.enter()
    guide.next()
    expect(guide.currentId.value).toBe(b.id)
    guide.next()
    expect(guide.currentId.value).toBe(a.id)
    guide.prev()
    expect(guide.currentId.value).toBe(b.id)
  })

  it('advances when the current slot becomes bound and exits when all are done', async () => {
    const a = slot(0, 0)
    const b = slot(300, 0)
    const { elements, guide } = setup([a, b])
    guide.enter()

    a.host_name = 'web01'
    elements.value = [...elements.value]
    await nextTick()
    expect(guide.active.value).toBe(true)
    expect(guide.boundCount.value).toBe(1)
    expect(guide.currentId.value).toBe(b.id)

    b.host_name = 'web02'
    elements.value = [...elements.value]
    await nextTick()
    expect(guide.active.value).toBe(false)
  })
})
