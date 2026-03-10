import type { MapObject, ObjectState } from '@/types/api'

/**
 * Interpolate a template string with object and state data.
 * Placeholders: {{name}}, {{type}}, {{state}}, {{output}},
 *               {{host}}, {{service}}, {{acknowledged}}, {{in_downtime}}
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

  const vars: Record<string, string> = {
    name: displayName,
    type: object.type,
    state: state?.state ?? '',
    output: state?.output ?? '',
    host: object.host_name ?? '',
    service: object.service_description ?? '',
    acknowledged: state?.acknowledged ? 'true' : 'false',
    in_downtime: state?.in_downtime ? 'true' : 'false',
  }

  return template.replace(/\{\{(\w+)\}\}/g, (_, key: string) => vars[key] ?? '')
}

/** Resolve template priority: object → map globals → global settings */
export function resolveTemplate(
  objectTpl: string | null | undefined,
  mapTpl: string | null | undefined,
  globalTpl: string | null | undefined,
): string | null {
  return objectTpl || mapTpl || globalTpl || null
}
