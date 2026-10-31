import { describe, expect, it } from 'vitest'

import { isValidLqlFilter } from './lqlFilter'

describe('isValidLqlFilter', () => {
  it('accepts Filter / And / Or / Negate lines', () => {
    expect(isValidLqlFilter('Filter: host_name ~ ^fw-')).toBe(true)
    expect(isValidLqlFilter('Filter: a = 1\nFilter: b = 2\nOr: 2\n')).toBe(true)
  })

  it('accepts NagVis-style literal \\n separators', () => {
    expect(isValidLqlFilter('Filter: a = 1\\nFilter: b = 2\\nAnd: 2')).toBe(true)
  })

  it('rejects other Livestatus headers, also when smuggled in via a literal \\n', () => {
    expect(isValidLqlFilter('Columns: name')).toBe(false)
    expect(isValidLqlFilter('Filter: a = 1\\nStats: state = 0')).toBe(false)
    expect(isValidLqlFilter('Filter: a = 1\nAuthUser: admin')).toBe(false)
  })

  it('rejects empty and half-typed input', () => {
    expect(isValidLqlFilter('')).toBe(false)
    expect(isValidLqlFilter('  \n ')).toBe(false)
    expect(isValidLqlFilter('Filter:')).toBe(false)
    expect(isValidLqlFilter('Filter: host_name ~ ^fw-\nFil')).toBe(false)
  })
})
