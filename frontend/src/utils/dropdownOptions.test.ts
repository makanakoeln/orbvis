import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import type { TranslateFn } from '@/i18n'

import {
  boardTypeOptions,
  linePerfdataLabelOptions,
  lineStyleOptions,
  placeableObjectTypes
} from './dropdownOptions'

const t: TranslateFn = (msg) => msg

describe('placeableObjectTypes', () => {
  it('lists the graph type by default', () => {
    const names = placeableObjectTypes(t).map((o) => o.name)
    expect(names).toContain('graph')
    expect(names).toContain('host')
    expect(names).toContain('line')
  })

  it('omits the graph type when includeGraph is false', () => {
    const names = placeableObjectTypes(t, false).map((o) => o.name)
    expect(names).not.toContain('graph')
  })
})

describe('boardTypeOptions', () => {
  it('returns the four core board types by default', () => {
    const names = boardTypeOptions(t).map((o) => o.name)
    expect(names).toEqual(['static', 'worldmap', 'flow', 'radar'])
  })

  it('appends foldertree and presentation only when their flags are set', () => {
    const names = boardTypeOptions(t, true, true).map((o) => o.name)
    expect(names).toContain('foldertree')
    expect(names).toContain('presentation')
  })

  it('keeps the flags independent', () => {
    expect(boardTypeOptions(t, true, false).map((o) => o.name)).toContain('foldertree')
    expect(boardTypeOptions(t, true, false).map((o) => o.name)).not.toContain('presentation')
  })
})

describe('linePerfdataLabelOptions', () => {
  it('lists the four perfdata label modes', () => {
    expect(linePerfdataLabelOptions(t).map((o) => o.name)).toEqual([
      'none',
      'percent',
      'bandwidth',
      'both'
    ])
  })
})

describe('lineStyleOptions', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('prepends a null Default option and falls back to the built-in styles', () => {
    const options = lineStyleOptions(t)
    expect(options[0]).toEqual({ name: null, title: 'Default' })
    const names = options.map((o) => o.name)
    expect(names).toContain('plain')
    expect(names).toContain('arrow_inward')
  })
})
