import type { DataElement, ObjectState, PresentationElement, ShapeElement } from '@/types/api'

// Design-first placeholders: an unbound data slot previews with plausible
// sample data in the editor so a slide can be fully designed before any
// monitoring object is attached. Everything derives deterministically from the
// element id, so previews are stable across renders and saves.

export type BindableElement = DataElement | ShapeElement

export function isBindable(el: PresentationElement): el is BindableElement {
  return el.kind === 'data' || el.kind === 'shape'
}

// A data element is intrinsically a slot; a shape only when a template (or the
// operator) marked it as one via ``data_slot``.
export function isUnboundSlot(el: PresentationElement): el is BindableElement {
  if (el.kind === 'data') return !el.host_name
  if (el.kind === 'shape') return !!el.data_slot && !el.host_name
  return false
}

export function isBoundElement(el: PresentationElement): boolean {
  return isBindable(el) && !!el.host_name
}

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return h
}

// Mostly healthy with the occasional WARNING — a believable wall, not a crisis.
const SAMPLE_STATES = ['OK', 'OK', 'OK', 'WARNING', 'OK', 'OK'] as const

export function sampleStateFor(el: PresentationElement): ObjectState {
  const h = hash(el.id)
  const state = SAMPLE_STATES[h % SAMPLE_STATES.length] ?? 'OK'
  const value = 25 + (h % 60)
  const metric =
    (isBindable(el) &&
      (el.kind === 'data' ? el.display.gadget_metric : (el.flow_metric ?? null))) ||
    'util'
  return {
    object_id: el.id,
    type: 'service',
    state,
    output: 'Sample data',
    perf_data: `${metric}=${value}%;80;90;0;100`,
    acknowledged: false,
    in_downtime: false,
    stale: false
  }
}
