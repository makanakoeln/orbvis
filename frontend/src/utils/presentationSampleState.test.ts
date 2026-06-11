import { describe, expect, it } from 'vitest'

import type { DataElement, ShapeElement } from '@/types/api'

import { createElement } from './presentationElements'
import {
  isBindable,
  isBoundElement,
  isUnboundSlot,
  sampleStateFor,
  slotBounds
} from './presentationSampleState'

function data(over: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', 0, 0)
  if (el.kind !== 'data') throw new Error('unreachable')
  return Object.assign(el, over)
}

function shape(over: Partial<ShapeElement> = {}): ShapeElement {
  const el = createElement('rect', 0, 0)
  if (el.kind !== 'shape') throw new Error('unreachable')
  return Object.assign(el, over)
}

describe('isUnboundSlot', () => {
  it('treats an unbound data element as a slot, a bound one not', () => {
    expect(isUnboundSlot(data())).toBe(true)
    expect(isUnboundSlot(data({ host_name: 'web01' }))).toBe(false)
  })

  it('treats a shape as a slot only when explicitly marked', () => {
    expect(isUnboundSlot(shape())).toBe(false)
    expect(isUnboundSlot(shape({ data_slot: true }))).toBe(true)
    expect(isUnboundSlot(shape({ data_slot: true, host_name: 'web01' }))).toBe(false)
  })

  it('never treats text/image/group as slots', () => {
    expect(isUnboundSlot(createElement('text', 0, 0))).toBe(false)
    expect(isUnboundSlot(createElement('image', 0, 0))).toBe(false)
  })
})

describe('isBindable / isBoundElement', () => {
  it('classifies element kinds', () => {
    expect(isBindable(data())).toBe(true)
    expect(isBindable(shape())).toBe(true)
    expect(isBindable(createElement('text', 0, 0))).toBe(false)
    expect(isBoundElement(data({ host_name: 'web01' }))).toBe(true)
    expect(isBoundElement(data())).toBe(false)
  })
})

describe('slotBounds', () => {
  it('returns the element box for non-connectors', () => {
    const el = data({ x: 10, y: 20, w: 100, h: 50 })
    expect(slotBounds(el, () => undefined)).toEqual({ x: 10, y: 20, w: 100, h: 50 })
  })

  it('spans a docked connector between its endpoint centres', () => {
    const a = data({ x: 0, y: 0, w: 100, h: 100 })
    const b = data({ x: 400, y: 200, w: 100, h: 100 })
    const link = createElement('line', 0, 0)
    if (link.kind !== 'shape') throw new Error('unreachable')
    link.start_ref = a.id
    link.end_ref = b.id
    const byId = (id: string | null | undefined) => [a, b].find((e) => e.id === id)
    // Endpoint centres: (50,50) and (450,250).
    expect(slotBounds(link, byId)).toEqual({ x: 50, y: 50, w: 400, h: 200 })
  })

  it('falls back to the connector corners for free endpoints', () => {
    const link = createElement('line', 30, 40)
    if (link.kind !== 'shape') throw new Error('unreachable')
    link.w = 260
    link.h = 4
    expect(slotBounds(link, () => undefined)).toEqual({ x: 30, y: 40, w: 260, h: 4 })
  })
})

describe('sampleStateFor', () => {
  it('is deterministic per element id', () => {
    const el = data()
    const a = sampleStateFor(el)
    const b = sampleStateFor(el)
    expect(a).toEqual(b)
    expect(a.object_id).toBe(el.id)
  })

  it('carries a parsable perf_data metric matching the configured gadget metric', () => {
    const el = data({ display: { mode: 'gadget', gadget_type: 'gauge', gadget_metric: 'load1' } })
    const s = sampleStateFor(el)
    expect(s.perf_data.startsWith('load1=')).toBe(true)
    expect(s.perf_data).toMatch(/^load1=\d+%;80;90;0;100$/)
  })

  it('falls back to a generic util metric when none is configured', () => {
    expect(sampleStateFor(data()).perf_data).toMatch(/^util=\d+%/)
  })
})
