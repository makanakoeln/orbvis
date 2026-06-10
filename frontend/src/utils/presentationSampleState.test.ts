import { describe, expect, it } from 'vitest'

import type { DataElement, ShapeElement } from '@/types/api'

import { createElement } from './presentationElements'
import {
  isBindable,
  isBoundElement,
  isUnboundSlot,
  sampleStateFor
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
