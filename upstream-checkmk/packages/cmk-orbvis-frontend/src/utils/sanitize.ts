import sanitizeHtml from 'sanitize-html'

// Allowlist for user-defined hover/context templates. Interpolated monitoring
// data (plugin output, host names) must never become a script vector. Beyond
// the former DOMPurify set this covers table layouts and inline icons, which
// imported NagVis templates conventionally use. Inline styles are restricted
// to cosmetic properties — positioning/stacking stays blocked so a malicious
// plugin output cannot paint a full-viewport overlay; url(...) values are
// rejected to prevent exfiltration pings on render.
const SAFE_STYLE_VALUE = [/^(?!.*url\s*\()[^;{}]*$/i]

const TEMPLATE_SANITIZE_OPTIONS: sanitizeHtml.IOptions = {
  allowedTags: [
    'b',
    'i',
    'u',
    'em',
    'strong',
    'span',
    'div',
    'p',
    'br',
    'hr',
    'a',
    'ul',
    'ol',
    'li',
    'code',
    'img',
    'table',
    'thead',
    'tbody',
    'tr',
    'td',
    'th'
  ],
  allowedAttributes: {
    '*': ['href', 'class', 'style', 'target', 'rel'],
    img: ['src', 'alt', 'width', 'height', 'class', 'style']
  },
  allowedStyles: {
    '*': {
      color: SAFE_STYLE_VALUE,
      'background-color': SAFE_STYLE_VALUE,
      'font-size': SAFE_STYLE_VALUE,
      'font-weight': SAFE_STYLE_VALUE,
      'font-style': SAFE_STYLE_VALUE,
      'font-family': SAFE_STYLE_VALUE,
      'text-align': SAFE_STYLE_VALUE,
      'text-decoration': SAFE_STYLE_VALUE,
      'white-space': SAFE_STYLE_VALUE,
      padding: SAFE_STYLE_VALUE,
      'padding-top': SAFE_STYLE_VALUE,
      'padding-right': SAFE_STYLE_VALUE,
      'padding-bottom': SAFE_STYLE_VALUE,
      'padding-left': SAFE_STYLE_VALUE,
      margin: SAFE_STYLE_VALUE,
      'margin-top': SAFE_STYLE_VALUE,
      'margin-right': SAFE_STYLE_VALUE,
      'margin-bottom': SAFE_STYLE_VALUE,
      'margin-left': SAFE_STYLE_VALUE,
      border: SAFE_STYLE_VALUE,
      'border-radius': SAFE_STYLE_VALUE,
      width: SAFE_STYLE_VALUE,
      height: SAFE_STYLE_VALUE,
      'max-width': SAFE_STYLE_VALUE,
      'max-height': SAFE_STYLE_VALUE
    }
  },
  allowedSchemes: ['http', 'https', 'mailto', 'tel']
}

export function sanitizeTemplateHtml(html: string): string {
  return sanitizeHtml(html, TEMPLATE_SANITIZE_OPTIONS)
}
