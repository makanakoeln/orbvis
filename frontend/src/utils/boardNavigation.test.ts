import { describe, expect, it } from 'vitest'

import { buildServiceStateViewUrl, hostStateOn, openUrl, svcStateOn } from './boardNavigation'

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

describe('openUrl', () => {
  function clickedHrefs(run: () => void): string[] {
    const hrefs: string[] = []
    const orig = HTMLAnchorElement.prototype.click
    HTMLAnchorElement.prototype.click = function (this: HTMLAnchorElement) {
      hrefs.push(this.href)
    }
    try {
      run()
    } finally {
      HTMLAnchorElement.prototype.click = orig
    }
    return hrefs
  }

  it('opens http(s)/mailto/tel and relative URLs', () => {
    const hrefs = clickedHrefs(() => {
      openUrl('https://example.com/x', '_blank')
      openUrl('mailto:ops@example.com', '_blank')
      openUrl('/relative/path', '_self')
    })
    expect(hrefs).toHaveLength(3)
  })

  it('refuses javascript: URLs even with embedded control characters', () => {
    const hrefs = clickedHrefs(() => {
      openUrl('javascript:alert(1)', '_blank')
      openUrl('java\tscript:alert(1)', '_blank')
      openUrl('java\nscript:alert(1)', '_blank')
      openUrl('data:text/html,<script>alert(1)</script>', '_blank')
    })
    expect(hrefs).toHaveLength(0)
  })
})
