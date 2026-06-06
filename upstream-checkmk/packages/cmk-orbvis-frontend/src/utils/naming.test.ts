import { describe, expect, it } from 'vitest'

import { sanitizeBoardName, slugToTitleCase } from './naming'

describe('sanitizeBoardName', () => {
  it('replaces spaces with hyphens', () => {
    expect(sanitizeBoardName('hello world')).toBe('hello-world')
  })

  it('strips special characters', () => {
    expect(sanitizeBoardName('my-board!')).toBe('my-board')
  })

  it('keeps alphanumeric, hyphens, underscores', () => {
    expect(sanitizeBoardName('my_board-01')).toBe('my_board-01')
  })

  it('strips umlauts', () => {
    expect(sanitizeBoardName('Übersicht')).toBe('bersicht')
  })

  it('handles empty string', () => {
    expect(sanitizeBoardName('')).toBe('')
  })
})

describe('slugToTitleCase', () => {
  it('converts hyphens to spaces and capitalizes', () => {
    expect(slugToTitleCase('my-board')).toBe('My Board')
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
