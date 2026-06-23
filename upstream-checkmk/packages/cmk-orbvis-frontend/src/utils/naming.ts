import type { MapObject, ObjectType } from '@/types/api'

/** Object types that are purely decorative and carry no monitoring state. */
export const VISUAL_ONLY_TYPES: readonly ObjectType[] = ['image', 'textbox', 'line']

/**
 * Return a human-readable type label for a map object.
 * Graph and line objects are labelled by what they monitor ('service' or 'host')
 * when linked to one, not by their OrbVis object type.
 */
export function getObjectTypeLabel(object: MapObject): string {
  if (object.type === 'graph' || object.type === 'line') {
    if (object.service_description) return 'service'
    if (object.host_name) return 'host'
  }
  return object.type
}

/** Return the display name for a map object (label > host/service > host/group/map/aggregation > id). */
export function getMapObjectName(object: MapObject): string {
  if (object.label?.text) return object.label.text
  return getMapObjectIdentifier(object)
}

/** Monitoring identifier; falls back to the label (then id) for objects with
 * no host/group/map/aggregation binding, such as geo bundles. */
export function getMapObjectIdentifier(object: MapObject): string {
  if (object.host_name && object.service_description)
    return `${object.host_name} / ${object.service_description}`
  return (
    object.host_name ??
    object.group_name ??
    object.map_name ??
    object.aggregation_id ??
    (object.label?.text || object.id)
  )
}

/** Sanitize a raw string into a valid map ID: spaces → hyphens, strip invalid chars. */
export function sanitizeMapName(raw: string): string {
  return raw.replace(/ /g, '-').replace(/[^a-zA-Z0-9_-]/g, '')
}

export function sanitizeStrippedChars(raw: string): boolean {
  const withoutSpaces = raw.replace(/ /g, '-')
  return withoutSpaces.replace(/[^a-zA-Z0-9_-]/g, '') !== withoutSpaces
}

/** Convert a hyphen/underscore-separated slug to Title Case display name. */
export function slugToTitleCase(slug: string): string {
  return slug.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
