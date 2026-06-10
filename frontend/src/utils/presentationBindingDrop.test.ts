import { describe, expect, it } from 'vitest'

import type { DataElement, PresentationElement, ShapeElement } from '@/types/api'

import {
  applyBindingDrop,
  bindableElementAt,
  parseBindingDropPayload
} from './presentationBindingDrop'
import { createElement } from './presentationElements'

function data(x: number, y: number, over: Partial<DataElement> = {}): DataElement {
  const el = createElement('data', x, y)
  if (el.kind !== 'data') throw new Error('unreachable')
  return Object.assign(el, over)
}

function rect(x: number, y: number, over: Partial<ShapeElement> = {}): ShapeElement {
  const el = createElement('rect', x, y)
  if (el.kind !== 'shape') throw new Error('unreachable')
  return Object.assign(el, over)
}

describe('parseBindingDropPayload', () => {
  it('accepts a host with optional service', () => {
    expect(parseBindingDropPayload('{"host":"web01"}')).toEqual({ host: 'web01', service: null })
    expect(parseBindingDropPayload('{"host":"web01","service":"CPU"}')).toEqual({
      host: 'web01',
      service: 'CPU'
    })
  })

  it('rejects garbage', () => {
    expect(parseBindingDropPayload('not json')).toBeNull()
    expect(parseBindingDropPayload('{"service":"CPU"}')).toBeNull()
    expect(parseBindingDropPayload('null')).toBeNull()
  })
})

describe('bindableElementAt', () => {
  it('hits the topmost bindable element by z-order', () => {
    const low = data(0, 0, { z: 1 })
    const high = data(50, 50, { z: 5 })
    const els: PresentationElement[] = [low, high]
    expect(bindableElementAt(els, { x: 80, y: 80 })?.id).toBe(high.id)
  })

  it('ignores connectors, locked, hidden and non-bindable elements', () => {
    const line = createElement('line', 0, 0)
    const locked = data(0, 0, { locked: true })
    const hidden = data(0, 0, { hidden: true })
    const text = createElement('text', 0, 0)
    expect(bindableElementAt([line, locked, hidden, text], { x: 10, y: 10 })).toBeNull()
  })
})

describe('applyBindingDrop', () => {
  it('binds the hit element and clears a stale service when none is dropped', () => {
    const target = rect(0, 0)
    const result = applyBindingDrop([target], { x: 10, y: 10 }, { host: 'web01' }, 7)
    expect(result.kind).toBe('bind')
    if (result.kind !== 'bind') return
    expect(result.id).toBe(target.id)
    expect(result.patch).toEqual({ host_name: 'web01', service_description: null })
  })

  it('creates a bound data element on empty slide space', () => {
    const result = applyBindingDrop([], { x: 500, y: 400 }, { host: 'web01', service: 'CPU' }, 7)
    expect(result.kind).toBe('create')
    if (result.kind !== 'create') return
    expect(result.element.kind).toBe('data')
    expect(result.element.host_name).toBe('web01')
    expect(result.element.service_description).toBe('CPU')
    expect(result.element.z).toBe(7)
    expect(result.element.x).toBe(420)
    expect(result.element.y).toBe(340)
  })
})
