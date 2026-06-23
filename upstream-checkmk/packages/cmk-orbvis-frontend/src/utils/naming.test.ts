import { describe, expect, it } from 'vitest'

import { sanitizeMapName, slugToTitleCase } from './naming'

describe('sanitizeMapName', () => {
  it('replaces spaces with hyphens', () => {
    expect(sanitizeMapName('hello world')).toBe('hello-world')
  })

  it('strips special characters', () => {
    expect(sanitizeMapName('my-map!')).toBe('my-map')
  })

  it('keeps alphanumeric, hyphens, underscores', () => {
    expect(sanitizeMapName('my_map-01')).toBe('my_map-01')
  })

  it('strips umlauts', () => {
    expect(sanitizeMapName('Übersicht')).toBe('bersicht')
  })

  it('handles empty string', () => {
    expect(sanitizeMapName('')).toBe('')
  })
})

describe('slugToTitleCase', () => {
  it('converts hyphens to spaces and capitalizes', () => {
    expect(slugToTitleCase('my-map')).toBe('My Map')
  })

  it('converts underscores to spaces', () => {
    expect(slugToTitleCase('server_group_a')).toBe('Server Group A')
  })

  it('handles single word', () => {
    expect(slugToTitleCase('overview')).toBe('Overview')
  })

  it('handles mixed separators', () => {
    expect(slugToTitleCase('my_server-group')).toBe('My Server Group')
  })
})
