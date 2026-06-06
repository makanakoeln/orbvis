import { describe, expect, it } from 'vitest'

import { sanitizeTemplateHtml } from './sanitize'

describe('sanitizeTemplateHtml', () => {
  it('keeps allowed markup', () => {
    const html = '<b>bold</b> <span class="x" style="color:red">red</span><br><ul><li>a</li></ul>'
    expect(sanitizeTemplateHtml(html)).toBe(
      '<b>bold</b> <span class="x" style="color:red">red</span><br /><ul><li>a</li></ul>'
    )
  })

  it('keeps table layouts and images (NagVis template convention)', () => {
    expect(sanitizeTemplateHtml('<table><tbody><tr><td>cell</td></tr></tbody></table>')).toBe(
      '<table><tbody><tr><td>cell</td></tr></tbody></table>'
    )
    expect(sanitizeTemplateHtml('<img src="https://example.com/icon.png" alt="x" />')).toBe(
      '<img src="https://example.com/icon.png" alt="x" />'
    )
  })

  it('keeps links with http/https/mailto/tel schemes', () => {
    expect(sanitizeTemplateHtml('<a href="https://example.com" target="_blank">x</a>')).toBe(
      '<a href="https://example.com" target="_blank">x</a>'
    )
    expect(sanitizeTemplateHtml('<a href="mailto:a@b.c">x</a>')).toBe(
      '<a href="mailto:a@b.c">x</a>'
    )
    expect(sanitizeTemplateHtml('<a href="tel:+4912345">x</a>')).toBe(
      '<a href="tel:+4912345">x</a>'
    )
  })

  it('strips script tags entirely', () => {
    expect(sanitizeTemplateHtml('before<script>alert(1)</script>after')).toBe('beforeafter')
  })

  it('strips event handler attributes', () => {
    expect(sanitizeTemplateHtml('<b onclick="alert(1)">x</b>')).toBe('<b>x</b>')
    expect(sanitizeTemplateHtml('<span onmouseover="alert(1)">x</span>')).toBe('<span>x</span>')
    expect(sanitizeTemplateHtml('<img src="https://a.de/x.png" onerror="alert(1)" />')).toBe(
      '<img src="https://a.de/x.png" />'
    )
  })

  it('strips javascript: URLs', () => {
    expect(sanitizeTemplateHtml('<a href="javascript:alert(1)">x</a>')).toBe('<a>x</a>')
  })

  it('blocks overlay/positioning styles but keeps cosmetic ones', () => {
    expect(
      sanitizeTemplateHtml('<div style="position:fixed;inset:0;z-index:9999;color:red">x</div>')
    ).toBe('<div style="color:red">x</div>')
    expect(sanitizeTemplateHtml('<span style="opacity:0">x</span>')).toBe('<span>x</span>')
  })

  it('blocks url() values in styles (exfiltration ping)', () => {
    expect(
      sanitizeTemplateHtml('<div style="background-color:url(https://evil.example)">x</div>')
    ).toBe('<div>x</div>')
  })

  it('drops disallowed tags but keeps their text content', () => {
    expect(sanitizeTemplateHtml('<button>t</button><form>f</form>')).toBe('tf')
  })
})
