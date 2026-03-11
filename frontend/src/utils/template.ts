import type { BoardObject as MapObject, ObjectState } from '@/types/api'
import { parsePerfData } from '@/utils/perf'

/**
 * Interpolate a template string with object and state data.
 *
 * Placeholders:
 *   {{name}}           – display name (label_text or host/service/group)
 *   {{type}}           – object type (host, service, …)
 *   {{state}}          – monitoring state (UP, DOWN, OK, WARNING, …)
 *   {{output}}         – plugin output (first line)
 *   {{long_output}}    – full plugin output including additional lines
 *   {{host}}           – hostname
 *   {{service}}        – service description
 *   {{group}}          – group name (hostgroup / servicegroup)
 *   {{acknowledged}}   – 'true' / 'false'
 *   {{in_downtime}}    – 'true' / 'false'
 *   {{stale}}          – 'true' / 'false'
 *   {{perf_data}}      – raw performance data string
 *   {{metric}}         – value of first perf metric (or named one via {{metric:label}})
 *   {{metric_unit}}    – unit of first perf metric
 *   {{metric:LABEL}}   – value of the perf metric named LABEL
 */
export function interpolateTemplate(
  template: string,
  object: MapObject,
  state: ObjectState | undefined,
): string {
  const displayName =
    object.label_text ||
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
    acknowledged: state?.acknowledged ? 'true' : 'false',
    in_downtime: state?.in_downtime ? 'true' : 'false',
    stale: state?.stale ? 'true' : 'false',
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
