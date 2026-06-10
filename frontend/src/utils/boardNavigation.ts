import type { BoardObject } from '@/types/api'

import { SAFE_URL_SCHEMES } from './sanitize'

function _baseAndSite(
  checkmkUrl: string | null,
  siteOverride?: string | null
): { base: string; p: Record<string, string> } | null {
  const base = checkmkUrl?.replace(/\/check_mk\/?$/, '').replace(/\/$/, '')
  if (!base) return null
  // Don't fall back to the URL's path segment — on a central that would pin
  // the link to the central site id even for hosts on remotes.
  const p: Record<string, string> = {}
  if (siteOverride) p.site = siteOverride
  return { base, p }
}

// Wrap a relative Checkmk path in `index.py?start_url=…` so the landing page
// keeps Checkmk's chrome (sidebar, top-bar, breadcrumbs) instead of dropping
// the operator into a bare view. Bare view URLs are still useful inside an
// embedded iframe (no double chrome), but at the OrbVis layer "open in
// Checkmk" always means "open the real Checkmk page".
function _wrapInChrome(base: string, viewPath: string, viewParams: URLSearchParams): string {
  const inner = `${viewPath}?${viewParams}`
  const outer = new URLSearchParams({ start_url: inner })
  return `${base}/check_mk/index.py?${outer}`
}

export function buildCheckmkUrl(
  obj: BoardObject,
  checkmkUrl: string | null,
  siteOverride?: string | null
): string | null {
  const r = _baseAndSite(checkmkUrl, siteOverride)
  if (!r) return null
  const { base, p } = r

  if ((obj.type === 'host' || obj.type === 'line') && obj.host_name && !obj.service_description) {
    p.view_name = 'hoststatus'
    p.host = obj.host_name
    return _wrapInChrome(base, 'view.py', new URLSearchParams(p))
  }
  if ((obj.type === 'service' || obj.type === 'line') && obj.host_name && obj.service_description) {
    p.view_name = 'service'
    p.host = obj.host_name
    p.service = obj.service_description
    return _wrapInChrome(base, 'view.py', new URLSearchParams(p))
  }
  if (obj.type === 'hostgroup' && obj.group_name) {
    p.view_name = 'hostgroup'
    p.hostgroup = obj.group_name
    return _wrapInChrome(base, 'view.py', new URLSearchParams(p))
  }
  if (obj.type === 'servicegroup' && obj.group_name) {
    p.view_name = 'servicegroup'
    p.servicegroup = obj.group_name
    return _wrapInChrome(base, 'view.py', new URLSearchParams(p))
  }
  if (obj.type === 'aggregation' && obj.aggregation_id) {
    p.view_name = 'aggr_single'
    p.aggr_name = obj.aggregation_id
    p.po_aggr_expand = '1'
    return _wrapInChrome(base, 'view.py', new URLSearchParams(p))
  }
  if (obj.type === 'site' && obj.host_name) {
    // Site root drills into the per-site host overview.
    p.view_name = 'allhosts'
    p.site = obj.host_name
    return _wrapInChrome(base, 'view.py', new URLSearchParams(p))
  }
  return null
}

/**
 * For object types where the live monitoring view (``buildCheckmkUrl``)
 * isn't where the operator's "edit this thing" intent leads, return the
 * configuration/setup URL.
 *
 * BI aggregations: when ``packId`` is supplied (resolved from the
 * AggregationInfo cache the EditPanel + Drawer already keep), deep-link
 * straight into the rules editor of that pack (``mode=bi_rules&pack=…``)
 * so the operator can immediately find + edit the aggregation. Falls
 * back to the BI packs overview (``mode=bi_packs``) when no pack id is
 * available — better than nothing, just one extra click.
 */
export function buildCheckmkSetupUrl(
  obj: BoardObject,
  checkmkUrl: string | null,
  packId?: string | null,
  siteOverride?: string | null
): string | null {
  const r = _baseAndSite(checkmkUrl, siteOverride)
  if (!r) return null
  const { base, p } = r
  if (obj.type === 'aggregation') {
    if (packId) {
      p.mode = 'bi_rules'
      p.pack = packId
    } else {
      p.mode = 'bi_packs'
    }
    return _wrapInChrome(base, 'wato.py', new URLSearchParams(p))
  }
  return null
}

// Defense-in-depth mirror of the backend allowlist (schemas/_validators.py):
// board JSON predating the server-side check may still carry hostile URLs.
const SAFE_PROTOCOLS = SAFE_URL_SCHEMES.map((s) => `${s}:`)

// Uses a real <a> click so the browser doesn't treat it as a popup (important
// when OrbVis runs inside a Checkmk iframe — window.open gets popup-blocked).
export function openUrl(url: string, target: string): void {
  let protocol: string
  try {
    protocol = new URL(url, window.location.href).protocol
  } catch {
    console.warn(`openUrl: unparseable URL blocked: ${url}`)
    return
  }
  if (!SAFE_PROTOCOLS.includes(protocol)) {
    console.warn(`openUrl: blocked unsafe URL scheme: ${protocol}`)
    return
  }
  const a = document.createElement('a')
  a.href = url
  a.target = target
  a.rel = 'noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// Checkmk's filter machinery takes a single "svc_state" / "host_state" filter
// whose individual st*/hst* checkboxes are interpreted as a bitmask. A box
// only counts as ON when its parameter is present and equals "on" — sending
// "off" or omitting it both mean "exclude this state". The whole filter is
// only honored when "_active" lists svcstate/hoststate alongside the host /
// site filter; without it the Setup-defined view defaults win.
export function svcStateOn(state: string): string {
  if (state === 'CRITICAL') return 'st2'
  if (state === 'WARNING') return 'st1'
  if (state === 'UNKNOWN') return 'st3'
  return 'st0' // OK
}

export function hostStateOn(state: string): string {
  if (state === 'DOWN') return 'hst1'
  if (state === 'UNREACHABLE') return 'hst2'
  return 'hst0' // UP
}

/**
 * Checkmk view listing a host's (or site's) services filtered to one state —
 * the target of the clickable state pills/chips in HoverMenu and DetailDrawer.
 * Returns null outside a Checkmk deployment or for unfilterable states (the
 * svcstate filter has no PENDING checkbox).
 */
export function buildServiceStateViewUrl(
  checkmkUrl: string | null,
  target: { host?: string | null | undefined; site?: string | null | undefined },
  state: string
): string | null {
  if (!checkmkUrl) return null
  if (!['OK', 'WARNING', 'CRITICAL', 'UNKNOWN'].includes(state)) return null
  const base = checkmkUrl.replace(/\/check_mk\/?$/, '').replace(/\/$/, '')
  const params: Record<string, string> = {
    view_name: 'allservices',
    filled_in: 'filter',
    _active: 'svcstate;host',
    [svcStateOn(state)]: 'on'
  }
  if (target.site) {
    params.site = target.site
    params._active = 'svcstate;site'
  } else if (target.host) {
    params.host = target.host
  } else {
    return null
  }
  return `${base}/check_mk/view.py?${new URLSearchParams(params)}`
}
