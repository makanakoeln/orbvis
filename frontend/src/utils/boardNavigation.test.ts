import { describe, expect, it } from 'vitest'

import { buildServiceStateViewUrl, hostStateOn, svcStateOn } from './boardNavigation'

describe('svcStateOn / hostStateOn', () => {
  it('maps monitoring states to Checkmk filter checkboxes', () => {
    expect(svcStateOn('OK')).toBe('st0')
    expect(svcStateOn('WARNING')).toBe('st1')
    expect(svcStateOn('CRITICAL')).toBe('st2')
    expect(svcStateOn('UNKNOWN')).toBe('st3')
    expect(hostStateOn('UP')).toBe('hst0')
    expect(hostStateOn('DOWN')).toBe('hst1')
    expect(hostStateOn('UNREACHABLE')).toBe('hst2')
  })
})

describe('buildServiceStateViewUrl', () => {
  const cmk = 'http://h/SITE/check_mk/'

  it('builds the host-scoped allservices view with the state checkbox on', () => {
    const url = buildServiceStateViewUrl(cmk, { host: 'web01' }, 'CRITICAL')
    expect(url).toContain('/SITE/check_mk/view.py?')
    expect(url).toContain('view_name=allservices')
    expect(url).toContain('host=web01')
    expect(url).toContain('st2=on')
    expect(url).toContain('_active=svcstate%3Bhost')
  })

  it('switches to the site filter for site targets', () => {
    const url = buildServiceStateViewUrl(cmk, { site: 'remote1' }, 'WARNING')
    expect(url).toContain('site=remote1')
    expect(url).toContain('st1=on')
    expect(url).toContain('_active=svcstate%3Bsite')
  })

  it('returns null outside a Checkmk deployment or without a target', () => {
    expect(buildServiceStateViewUrl(null, { host: 'web01' }, 'OK')).toBeNull()
    expect(buildServiceStateViewUrl(cmk, {}, 'OK')).toBeNull()
  })

  it('returns null for states the svcstate filter cannot express', () => {
    expect(buildServiceStateViewUrl(cmk, { host: 'web01' }, 'PENDING')).toBeNull()
  })
})
