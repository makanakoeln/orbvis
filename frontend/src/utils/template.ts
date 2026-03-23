import type { BoardObject as MapObject, ObjectState } from '@/types/api'
import { parsePerfData } from '@/utils/perf'

function _fmtTs(ts: number | null | undefined): string {
  if (!ts) return ''
  return new Date(ts * 1000).toLocaleString()
}

function _fmtDuration(ts: number | null | undefined): string {
  if (!ts) return ''
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ${m % 60}m`
  const d = Math.floor(h / 24)
  return `${d}d ${h % 24}h`
}

/**
 * Interpolate a template string with object and state data.
 *
 * Placeholders:
 *   {{name}}             – display name (label_text or host/service/group)
 *   {{type}}             – object type (host, service, …)
 *   {{state}}            – monitoring state (UP, DOWN, OK, WARNING, …)
 *   {{output}}           – plugin output (first line)
 *   {{long_output}}      – full plugin output including additional lines
 *   {{host}}             – hostname
 *   {{service}}          – service description
 *   {{group}}            – group name (hostgroup / servicegroup)
 *   {{address}}          – host IP address
 *   {{acknowledged}}     – 'true' / 'false'
 *   {{in_downtime}}      – 'true' / 'false'
 *   {{stale}}            – 'true' / 'false'
 *   {{state_type}}       – 'HARD' / 'SOFT'
 *   {{attempts}}         – 'current/max' check attempts (e.g. '2/3')
 *   {{last_check}}       – formatted timestamp of last check
 *   {{last_state_change}}– formatted timestamp of last state change
 *   {{state_duration}}   – time since last state change (e.g. '3h 12m')
 *   {{perf_data}}        – raw performance data string
 *   {{metric}}           – value of first perf metric (or named one via {{metric:label}})
 *   {{metric_unit}}      – unit of first perf metric
 *   {{metric:LABEL}}     – value of the perf metric named LABEL
 */
export function interpolateTemplate(
  template: string,
  object: MapObject,
  state: ObjectState | undefined,
): string {
  const displayName =
    object.label?.text ||
    (object.host_name && object.service_description
      ? `${object.host_name} / ${object.service_description}`
      : object.host_name ?? object.group_name ?? object.id)

  const perfRaw = state?.perf_data ?? ''
  const metrics = parsePerfData(perfRaw)
  const firstMetric = metrics[0]

  const vars: Record<string, string> = {
    name: displayName,
    type: object.type,
    state: state?.state ?? '',
    output: state?.output?.split('\n')[0] ?? '',
    long_output: state?.output ?? '',
    host: object.host_name ?? '',
    service: object.service_description ?? '',
    group: object.group_name ?? '',
    address: state?.address ?? '',
    acknowledged: state?.acknowledged ? 'true' : 'false',
    in_downtime: state?.in_downtime ? 'true' : 'false',
    stale: state?.stale ? 'true' : 'false',
    state_type: state?.state_type ?? '',
    attempts: (state?.current_attempt && state?.max_attempts)
      ? `${state.current_attempt}/${state.max_attempts}` : '',
    last_check: _fmtTs(state?.last_check),
    last_state_change: _fmtTs(state?.last_state_change),
    state_duration: _fmtDuration(state?.last_state_change),
    perf_data: perfRaw,
    metric: firstMetric ? String(firstMetric.value) + firstMetric.unit : '',
    metric_unit: firstMetric?.unit ?? '',
  }

  return template.replace(/\{\{(\w+(?::\w+)?)\}\}/g, (_, key: string) => {
    // {{metric:LABEL}} – look up a named perf metric
    if (key.startsWith('metric:')) {
      const label = key.slice(7)
      const m = metrics.find(x => x.label === label)
      return m ? String(m.value) + m.unit : ''
    }
    return vars[key] ?? ''
  })
}

/** Resolve template priority: object → map globals → global settings */
export function resolveTemplate(
  objectTpl: string | null | undefined,
  mapTpl: string | null | undefined,
  globalTpl: string | null | undefined,
): string | null {
  return objectTpl || mapTpl || globalTpl || null
}
