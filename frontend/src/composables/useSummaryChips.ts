import { computed } from 'vue'

import type { BoardObject, ObjectState } from '@/types/api'
import { buildServiceStateViewUrl, hostStateOn, stripCheckmkBase } from '@/utils/boardNavigation'

export interface SummaryChip {
  state: string
  count: number
  label: string
  tone: 'crit' | 'warn' | 'unknown' | 'ok'
  url: string | null
}

interface SummaryChipsOptions {
  object: () => BoardObject | null
  state: () => ObjectState | undefined
  checkmkUrl: () => string | null | undefined
  isSite: () => boolean
}

/**
 * State-count chip rows shown in the drawer header: per-service-state chips for
 * hosts/sites and per-host-state chips for sites. Each chip links into the
 * matching Checkmk view. Host counts for a site are parsed out of the site's
 * status output ("504 hosts (504 up, 0 down, 0 unreachable)").
 */
export function useSummaryChips(options: SummaryChipsOptions) {
  const { object, state, checkmkUrl, isSite } = options

  function buildServiceChipUrl(stateName: string, count: number): string | null {
    const obj = object()
    if (count <= 0 || !obj) return null
    const isSiteObj = obj.type === 'site'
    return buildServiceStateViewUrl(
      checkmkUrl() ?? null,
      isSiteObj ? { site: obj.host_name } : { host: obj.host_name },
      stateName
    )
  }

  function buildHostChipUrl(stateName: string, count: number): string | null {
    const obj = object()
    const url = checkmkUrl()
    if (count <= 0 || !url || !obj) return null
    if (obj.type !== 'site' || !obj.host_name) return null
    const base = stripCheckmkBase(url)
    const params: Record<string, string> = {
      view_name: 'allhosts',
      filled_in: 'filter',
      _active: 'hoststate;site',
      site: obj.host_name,
      [hostStateOn(stateName)]: 'on'
    }
    return `${base}/check_mk/view.py?${new URLSearchParams(params)}`
  }

  const serviceChips = computed<SummaryChip[]>(() => {
    const s = state()?.services_summary
    if (!s) return []
    const make = (
      stateName: string,
      count: number,
      label: string,
      tone: SummaryChip['tone']
    ): SummaryChip => ({
      state: stateName,
      count,
      label,
      tone,
      url: buildServiceChipUrl(stateName, count)
    })
    // Hide problem chips at zero (visual noise); always keep the OK anchor so
    // the operator sees an "all green" cue when nothing is wrong.
    return [
      make('CRITICAL', s.critical ?? 0, 'CRIT', 'crit'),
      make('WARNING', s.warning ?? 0, 'WARN', 'warn'),
      make('UNKNOWN', s.unknown ?? 0, 'UNKN', 'unknown'),
      make('OK', s.ok ?? 0, 'OK', 'ok')
    ].filter((chip) => chip.state === 'OK' || chip.count > 0)
  })

  // Site state output looks like "504 hosts (504 up, 0 down, 0 unreachable)";
  // extract the host counts so we can render the same kind of chip row as services.
  const hostsSummary = computed<{ up: number; down: number; unreachable: number } | null>(() => {
    if (!isSite()) return null
    const out = state()?.output
    if (!out) return null
    const m = out.match(/(\d+)\s+up,\s*(\d+)\s+down,\s*(\d+)\s+unreachable/)
    if (!m?.[1] || !m[2] || !m[3]) return null
    return { up: parseInt(m[1], 10), down: parseInt(m[2], 10), unreachable: parseInt(m[3], 10) }
  })

  const hostChips = computed<SummaryChip[]>(() => {
    const h = hostsSummary.value
    if (!h) return []
    const make = (
      stateName: string,
      count: number,
      label: string,
      tone: SummaryChip['tone']
    ): SummaryChip => ({
      state: stateName,
      count,
      label,
      tone,
      url: buildHostChipUrl(stateName, count)
    })
    return [
      make('DOWN', h.down, 'DOWN', 'crit'),
      make('UNREACHABLE', h.unreachable, 'UNRCH', 'warn'),
      make('UP', h.up, 'UP', 'ok')
    ].filter((chip) => chip.state === 'UP' || chip.count > 0)
  })

  return { serviceChips, hostChips }
}
