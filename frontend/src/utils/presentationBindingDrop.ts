import type { DataElement, PresentationElement } from '@/types/api'

import { createElement } from './presentationElements'

// Drag&drop binding from the data panel: dropping a host/service onto an
// existing element binds it; dropping onto empty slide space creates a new
// data element at the drop point. Pure logic — the canvas applies the result
// through its mutate() pipeline.

export const BINDING_DROP_MIME = 'application/x-orbvis-binding'

export interface BindingDropPayload {
  host: string
  service?: string | null
}

export function parseBindingDropPayload(raw: string): BindingDropPayload | null {
  try {
    const v = JSON.parse(raw) as unknown
    if (typeof v !== 'object' || v === null) return null
    const host = (v as Record<string, unknown>).host
    if (typeof host !== 'string' || !host) return null
    const service = (v as Record<string, unknown>).service
    return { host, service: typeof service === 'string' && service ? service : null }
  } catch {
    return null
  }
}

export type BindingDropResult =
  | { kind: 'bind'; id: string; patch: Record<string, unknown> }
  | { kind: 'create'; element: DataElement }

// Topmost element under the point that can carry a monitoring binding: data
// elements and box shapes. Connectors are excluded (their x/y/w/h box is
// vestigial), as are groups, hidden and locked elements.
export function bindableElementAt(
  elements: PresentationElement[],
  point: { x: number; y: number }
): PresentationElement | null {
  const hit = [...elements]
    .filter((e): e is PresentationElement => {
      if (e.kind !== 'data' && e.kind !== 'shape') return false
      if (e.kind === 'shape' && (e.shape === 'line' || e.shape === 'arrow')) return false
      if (e.hidden || e.locked) return false
      return point.x >= e.x && point.x <= e.x + e.w && point.y >= e.y && point.y <= e.y + e.h
    })
    .sort((a, b) => b.z - a.z)[0]
  return hit ?? null
}

export function applyBindingDrop(
  elements: PresentationElement[],
  point: { x: number; y: number },
  payload: BindingDropPayload,
  nextZ: number
): BindingDropResult {
  const target = bindableElementAt(elements, point)
  if (target) {
    return {
      kind: 'bind',
      id: target.id,
      patch: { host_name: payload.host, service_description: payload.service ?? null }
    }
  }
  const el = createElement('data', Math.round(point.x - 80), Math.round(point.y - 60))
  if (el.kind === 'data') {
    el.host_name = payload.host
    el.service_description = payload.service ?? null
    el.z = nextZ
  }
  return { kind: 'create', element: el as DataElement }
}
