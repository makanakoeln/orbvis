import type {
  DataElement,
  ImageElement,
  PresentationElement,
  ShapeElement,
  TextElement
} from '@/types/api'

export type InsertKind = 'rect' | 'ellipse' | 'line' | 'arrow' | 'text' | 'image' | 'data'

// An image reference is stored as a bare image-store filename (portable across
// sites) — anything with a URL scheme or an absolute path is an external URL
// kept verbatim. Both the element ``src`` and the slide ``background_image``
// follow this convention and resolve through the helpers below.
const IMAGE_URL_RE = /^(https?:|data:|blob:|\/)/

export function resolveImageRef(ref: string | null | undefined): string {
  if (!ref) return ''
  if (IMAGE_URL_RE.test(ref)) return ref
  return `${import.meta.env.BASE_URL}images/${ref}`
}

// Given a stored ``src``/``background_image``, return the image-store filename it
// refers to, or '' when it's an external URL. Also unwraps a legacy fully
// resolved ``…/images/<name>`` URL so older maps still map back to the picker.
export function imageRefName(ref: string | null | undefined): string {
  if (!ref) return ''
  const prefix = `${import.meta.env.BASE_URL}images/`
  if (ref.startsWith(prefix)) return ref.slice(prefix.length)
  return IMAGE_URL_RE.test(ref) ? '' : ref
}

export function newElementId(kind: string): string {
  const rnd = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)
  return `el_${kind}_${rnd}`
}

function base(kind: string, x: number, y: number, w: number, h: number) {
  return {
    id: newElementId(kind),
    x,
    y,
    w,
    h,
    rotation: 0,
    z: 0,
    opacity: 1,
    locked: false,
    hidden: false,
    name: null
  }
}

// Insert-defaults pull their look from the active theme's CSS variables so a
// freshly placed element already fits the slide without manual restyling.
export function createElement(kind: InsertKind, x: number, y: number): PresentationElement {
  if (kind === 'text') {
    const el: TextElement = {
      ...base('text', x, y, 240, 64),
      kind: 'text',
      text: 'Text',
      font_family: null,
      font_size: 32,
      font_weight: 'bold',
      font_style: 'normal',
      text_align: 'left',
      line_height: 1.25,
      color: null,
      background: null,
      letter_spacing: 0
    }
    return el
  }
  if (kind === 'image') {
    const el: ImageElement = {
      ...base('image', x, y, 240, 160),
      kind: 'image',
      src: null,
      fit: 'contain',
      alt: null
    }
    return el
  }
  if (kind === 'data') {
    const el: DataElement = {
      ...base('data', x, y, 160, 120),
      kind: 'data',
      connection_id: null,
      object_type: null,
      host_name: null,
      service_description: null,
      group_name: null,
      aggregation_id: null,
      only_hard_states: false,
      display: { mode: 'icon' },
      label: {
        show: true,
        text: null,
        size: 14,
        color: null,
        background: null,
        weight: 'bold',
        align: 'center'
      },
      fill: null,
      stroke: null
    }
    return el
  }
  const isLinear = kind === 'line' || kind === 'arrow'
  const el: ShapeElement = {
    ...base('shape', x, y, isLinear ? 260 : 200, isLinear ? 4 : 140),
    kind: 'shape',
    shape: kind,
    fill: null,
    stroke: null,
    stroke_width: isLinear ? 3 : 1.5,
    corner_radius: kind === 'rect' ? 12 : 0,
    dash: 'solid',
    connection_id: null,
    object_type: null,
    host_name: null,
    service_description: null,
    group_name: null,
    aggregation_id: null,
    only_hard_states: false,
    label: null,
    start_ref: null,
    end_ref: null,
    flow: false,
    flow_metric: null
  }
  return el
}
