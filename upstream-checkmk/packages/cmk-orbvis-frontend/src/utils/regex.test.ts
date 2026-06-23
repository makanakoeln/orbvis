import { describe, expect, it } from 'vitest'

import { compileRegex } from './regex'

describe('compileRegex', () => {
  it('compiles a valid pattern and matches as expected', () => {
    const re = compileRegex('^web-\\d+$')
    expect(re.test('web-01')).toBe(true)
    expect(re.test('db-01')).toBe(false)
  })

  it('honours flags', () => {
    expect(compileRegex('abc', 'i').test('ABC')).toBe(true)
    expect(compileRegex('abc').test('ABC')).toBe(false)
  })

  it('throws SyntaxError for an invalid pattern so callers can render a hint', () => {
    expect(() => compileRegex('[')).toThrow(SyntaxError)
  })
})
