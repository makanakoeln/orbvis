<template>
  <div class="orb-worldmap">
    <div ref="mapEl" class="orb-worldmap__map" />
    <div
      v-if="mqVisible"
      class="orb-worldmap__marquee"
      :style="{
        left: `${mqRect.left}px`,
        top: `${mqRect.top}px`,
        width: `${mqRect.width}px`,
        height: `${mqRect.height}px`
      }"
    />
  </div>
</template>

<script setup lang="ts">
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { authApi } from '@/api/client'
import { useMarquee } from '@/composables/useMarquee'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import type {
  BoardConfig,
  BoardObject as BoardObjectType,
  LabelConfig,
  ObjectState,
  WorldmapView
} from '@/types/api'
import { type GroupMember, applyGroupDelta, collectGroupMembers } from '@/utils/groupDrag'
import { getBoardObjectName } from '@/utils/naming'
import {
  DIMMED_FILTER,
  DIMMED_OPACITY,
  objectMatchesFilter,
  passesProblemFilter
} from '@/utils/objectFilter'
import { stateColor as stateColorFromName } from '@/utils/stateColors'

const props = defineProps<{
  config: BoardConfig
  states: Record<string, ObjectState>
  editMode: boolean
  placing: boolean
  selectedObjectId: string | null
  selectedIds?: string[]
  filterNeedle?: string
  problemsOnly?: boolean
  preview?: boolean
}>()

const settingsStore = useSettingsStore()
const auth = useAuthStore()

const emit = defineEmits<{
  'object-click': [obj: BoardObjectType, event: MouseEvent]
  'object-contextmenu': [obj: BoardObjectType]
  'object-contextmenu-view': [obj: BoardObjectType, x: number, y: number]
  'object-hover': [obj: BoardObjectType, event: MouseEvent]
  'object-hover-leave': []
  'canvas-latlng-click': [lat: number, lng: number]
  'canvas-contextmenu-view': [
    view: { lat: number; lng: number; zoom: number },
    screen: { x: number; y: number }
  ]
  'latlng-drag-end': [id: string, lat: number, lng: number]
  'latlngs-drag-end': [moves: { id: string; lat: number; lng: number }[]]
  'latlng2-drag-end': [id: string, lat: number, lng: number]
  'endpoint-bind': [id: string, endpoint: 1 | 2, lat: number, lng: number, refId: string | null]
  'textbox-resize': [id: string, width: number, height: number]
  'view-changed': []
  'marquee-select': [ids: string[], additive: boolean]
  'canvas-click': []
}>()

const mapEl = ref<HTMLDivElement | null>(null)
let leafletMap: L.Map | null = null
let tileLayer: L.TileLayer | null = null
const markers = new Map<string, L.Marker>()

type LineEntry = {
  polyline: L.Polyline
  border: L.Polyline | null
  handle1: L.Marker
  handle2: L.Marker
  label: L.Marker | null
  arrowEnd: L.Marker | null
  arrowStart: L.Marker | null
}
const lines = new Map<string, LineEntry>()

// Default to OrbVis' own caching tile proxy (backend route /api/v1/maps/tiles).
// First-time fetches still hit OSM through the proxy, but subsequent loads come
// from the local on-disk cache and render near-instantly. Boards may override
// this via WorldmapView.tile_url to point at any other OSM-compatible source.
const DEFAULT_TILE_URL = `${import.meta.env.BASE_URL}api/v1/maps/tiles/{z}/{x}/{y}.png`

function stateColor(id: string): string {
  return stateColorFromName(props.states[id]?.state)
}

function isSelected(id: string): boolean {
  return props.selectedIds && props.selectedIds.length
    ? props.selectedIds.includes(id)
    : props.selectedObjectId === id
}

function markerZBase(obj: BoardObjectType): number {
  return (obj.z ?? props.config.default_z ?? 1) * 1000
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

// Live size override while a textbox is being drag-resized; null when idle.
let _tbResize: {
  id: string
  startX: number
  startY: number
  initW: number
  initH: number
  w: number
  h: number
} | null = null

function makeTextboxIcon(obj: BoardObjectType, selected: boolean): L.DivIcon {
  const label = obj.label
  const text = escapeHtml(label?.text || 'Text').replace(/\n/g, '<br>')
  const bg = obj.textbox_background
  const hasCustomBg = !!bg && bg !== 'transparent'
  const border = obj.textbox_border
  const color =
    label?.color && label.color !== '#ffffff' && label.color !== '#FFFFFF' ? label.color : '#f8fafc'
  const resizing = _tbResize?.id === obj.id ? _tbResize : null
  const w = resizing ? resizing.w : obj.textbox_width
  const h = resizing ? resizing.h : obj.textbox_height
  const styles = [
    'position:relative;',
    hasCustomBg ? `background:${bg};` : 'background:rgba(15,23,42,0.72);backdrop-filter:blur(4px);',
    border ? `border:1px solid ${border};` : '',
    `color:${color};`,
    `font-size:${label?.size ?? 13}px;`,
    label?.weight ? `font-weight:${label.weight};` : '',
    `text-align:${label?.align ?? 'left'};`,
    w ? `width:${w}px;` : '',
    h ? `height:${h}px;` : '',
    'padding:3px 8px;border-radius:6px;box-sizing:border-box;white-space:pre-wrap;line-height:1.3;',
    hasCustomBg ? '' : 'text-shadow:0 1px 2px rgba(0,0,0,0.6);',
    selected
      ? 'outline:3px dashed #4ade80;outline-offset:5px;box-shadow:0 0 0 4px #fff,0 0 0 7px rgba(0,0,0,0.8),0 0 14px 5px rgba(0,0,0,0.55);'
      : ''
  ].join('')
  const handle =
    props.editMode && !props.preview
      ? `<div class="orb-wm-resize" data-resize-id="${obj.id}" title="Resize" style="position:absolute;right:0;bottom:0;width:14px;height:14px;cursor:se-resize;background:rgba(34,197,94,0.85);border-top-left-radius:4px;pointer-events:auto;"></div>`
      : ''
  return L.divIcon({
    className: '',
    html: `<div data-object-id="${obj.id}" style="${styles}">${text}${handle}</div>`,
    iconSize: w && h ? [w, h] : undefined,
    iconAnchor: [0, 0]
  })
}

function _refreshTextbox(id: string) {
  const marker = markers.get(id)
  const obj = props.config.objects.find((o) => o.id === id)
  if (marker && obj) marker.setIcon(makeTextboxIcon(obj, isSelected(obj.id)))
}

function onTextboxResizeMove(e: MouseEvent) {
  if (!_tbResize) return
  e.preventDefault()
  _tbResize.w = Math.max(40, Math.round(_tbResize.initW + (e.clientX - _tbResize.startX)))
  _tbResize.h = Math.max(24, Math.round(_tbResize.initH + (e.clientY - _tbResize.startY)))
  _refreshTextbox(_tbResize.id)
}

function onTextboxResizeEnd() {
  document.removeEventListener('mousemove', onTextboxResizeMove, true)
  document.removeEventListener('mouseup', onTextboxResizeEnd, true)
  const r = _tbResize
  _tbResize = null
  if (r) {
    emit('textbox-resize', r.id, r.w, r.h)
    _refreshTextbox(r.id)
  }
}

function onTextboxResizeStart(e: MouseEvent) {
  const handle = (e.target as HTMLElement | null)?.closest?.('.orb-wm-resize') as HTMLElement | null
  if (!handle) return
  const id = handle.dataset.resizeId
  if (!id) return
  const obj = props.config.objects.find((o) => o.id === id)
  if (!obj) return
  e.preventDefault()
  e.stopPropagation()
  const box = handle.parentElement?.getBoundingClientRect()
  _tbResize = {
    id,
    startX: e.clientX,
    startY: e.clientY,
    initW: obj.textbox_width ?? Math.round(box?.width ?? 120),
    initH: obj.textbox_height ?? Math.round(box?.height ?? 32),
    w: obj.textbox_width ?? Math.round(box?.width ?? 120),
    h: obj.textbox_height ?? Math.round(box?.height ?? 32)
  }
  document.addEventListener('mousemove', onTextboxResizeMove, true)
  document.addEventListener('mouseup', onTextboxResizeEnd, true)
}

function makeDivIcon(obj: BoardObjectType): L.DivIcon {
  const selected = isSelected(obj.id)
  if (obj.type === 'textbox') return makeTextboxIcon(obj, selected)

  const color = stateColor(obj.id)
  const size = obj.display?.image_size ?? props.config.icon_size ?? settingsStore.settings.icon_size
  const escapedName = escapeHtml(getBoardObjectName(obj))
  const label = obj.label?.show !== false ? escapedName : ''

  const TYPE_CHARS: Record<string, string> = {
    host: 'H',
    service: 'S',
    hostgroup: 'HG',
    servicegroup: 'SG',
    map: 'M',
    image: '◆'
  }
  const typeChar = TYPE_CHARS[obj.type] ?? '?'
  const charSize = Math.max(8, Math.round(size * (typeChar.length > 1 ? 0.34 : 0.42)))

  const iconFile = obj.display?.image ?? obj.image_src
  const textOnly = obj.display?.mode === 'text'
  let iconHtml: string
  if (textOnly) {
    const txtColor = obj.label?.color || color
    const txtSize = obj.label?.size ?? Math.max(12, Math.round(size * 0.5))
    const selRing = selected ? 'outline:2px solid #4ade80;outline-offset:2px;' : ''
    iconHtml = `<div style="
        color: ${txtColor};
        font-size: ${txtSize}px;
        font-weight: 600;
        white-space: nowrap;
        text-shadow: -1px -1px 0 rgba(0,0,0,0.85), 1px -1px 0 rgba(0,0,0,0.85), -1px 1px 0 rgba(0,0,0,0.85), 1px 1px 0 rgba(0,0,0,0.85);
        padding: 1px 6px;
        border-radius: 4px;
        background: rgba(0,0,0,0.55);
        ${selRing}
      ">${escapedName}</div>`
  } else if (iconFile) {
    const outline = selected ? 'filter: drop-shadow(0 0 6px #4ade80);' : ''
    iconHtml = `<img src="${import.meta.env.BASE_URL}images/${iconFile}" style="width:${size}px;height:${size}px;object-fit:contain;display:block;${outline}" />`
  } else {
    iconHtml = `<div style="
        width: ${size}px; height: ${size}px;
        background: ${color};
        border-radius: 50%;
        border: 2px solid rgba(0,0,0,0.35);
        box-shadow: 0 1px 4px rgba(0,0,0,0.5)${selected ? `, 0 0 0 3px white` : ''};
        display: flex; align-items: center; justify-content: center;
        position: relative;
      "><span style="color:white;font-size:${charSize}px;font-weight:700;line-height:1;user-select:none;">${typeChar}</span></div>`
  }

  const state = props.states[obj.id]
  const badgeStyle =
    'position:absolute;width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,0.5);'
  const ackBadge = state?.acknowledged
    ? `<span style="${badgeStyle}top:-6px;right:-6px;background:#f59e0b;color:#1c1917;" title="Acknowledged">
        <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
       </span>`
    : ''
  const downtimeBadge = state?.in_downtime
    ? `<span style="${badgeStyle}top:-6px;left:-6px;background:#3b82f6;color:white;" title="In downtime">
        <svg width="10" height="10" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
       </span>`
    : ''

  const labelSize = obj.label?.size ?? 11
  const labelColor = obj.label?.color || 'white'
  const labelBg = obj.label?.background
  const labelBgStyle =
    labelBg && labelBg !== 'transparent'
      ? `background:${labelBg};padding:1px 5px;border-radius:3px;`
      : ''
  const labelOffsetX = obj.label?.x ?? 0
  const labelOffsetY = obj.label?.y ?? 0
  // Snap the centered-then-offset translate to whole pixels. Without round(),
  // calc(-50% + Xpx) lands on a fractional pixel whenever the label width is
  // odd, which made small fonts render visibly smeared.
  const labelHtml =
    label && !textOnly
      ? `<div style="
        position:absolute;
        top:100%;
        left:50%;
        transform: translate(round(calc(-50% + ${labelOffsetX}px), 1px), round(${labelOffsetY}px, 1px));
        text-align: center;
        color: ${labelColor};
        font-size: ${labelSize}px;
        font-weight: 500;
        text-shadow: -1px -1px 0 rgba(0,0,0,0.85), 1px -1px 0 rgba(0,0,0,0.85), -1px 1px 0 rgba(0,0,0,0.85), 1px 1px 0 rgba(0,0,0,0.85);
        text-rendering: geometricPrecision;
        white-space: nowrap;
        margin-top: 3px;
        ${labelBgStyle}
      ">${label.replace(/\n/g, '<br>')}</div>`
      : ''

  // Dashed green outline like the static board, but markers are themselves
  // state-coloured (often green) — so sandwich a white ring between the marker
  // and the dashes, plus a dark glow, to stay visible on any marker/background.
  const selWrap = selected
    ? 'outline:3px dashed #4ade80;outline-offset:5px;border-radius:9px;box-shadow:0 0 0 4px #fff,0 0 0 7px rgba(0,0,0,0.8),0 0 14px 5px rgba(0,0,0,0.55);'
    : ''
  const wrappedIcon = `<div data-object-id="${obj.id}" style="position:relative;display:inline-block;${selWrap}">${iconHtml}${ackBadge}${downtimeBadge}${labelHtml}</div>`

  return L.divIcon({
    className: '',
    html: wrappedIcon,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)]
  })
}

function syncMarkers() {
  if (!leafletMap) return
  const objects = props.config.objects.filter((o) => o.type !== 'line')
  const currentIds = new Set(objects.map((o) => o.id))

  for (const obj of objects) {
    const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null
    const lat = obj.lat ?? wv?.lat ?? 51
    const lng = obj.lng ?? wv?.lng ?? 10
    const icon = makeDivIcon(obj)
    const objId = obj.id

    if (markers.has(objId)) {
      const marker = markers.get(objId)!
      marker.setLatLng([lat, lng])
      marker.setIcon(icon)
      marker.setZIndexOffset(markerZBase(obj))
      if (props.editMode && !props.preview) marker.dragging?.enable()
      else marker.dragging?.disable()
    } else {
      const marker = L.marker([lat, lng], {
        icon,
        draggable: props.editMode && !props.preview,
        zIndexOffset: markerZBase(obj)
      })
      marker.on('click', (e: L.LeafletMouseEvent) => {
        if (props.preview) return
        L.DomEvent.stopPropagation(e)
        const current = props.config.objects.find((o) => o.id === objId)
        if (current) emit('object-click', current, e.originalEvent)
      })
      marker.on('contextmenu', (e: L.LeafletMouseEvent) => {
        if (props.preview) return
        L.DomEvent.stopPropagation(e)
        const current = props.config.objects.find((o) => o.id === objId)
        if (!current) return
        if (props.editMode) {
          emit('object-contextmenu', current)
        } else {
          emit('object-contextmenu-view', current, e.originalEvent.clientX, e.originalEvent.clientY)
        }
      })
      marker.on('mouseover', (e: L.LeafletMouseEvent) => {
        if (props.preview || props.editMode) return
        const current = props.config.objects.find((o) => o.id === objId)
        if (current) emit('object-hover', current, e.originalEvent)
      })
      marker.on('mouseout', () => {
        if (props.preview) return
        emit('object-hover-leave')
      })
      marker.on('dragstart', () => {
        _markerDragging = true
        _geoGroup = collectGroupMembers(props.config.objects, props.selectedIds, objId, (o) =>
          o.lat != null && o.lng != null ? [o.lat, o.lng] : null
        )
        _geoDragStart = _geoGroup.length ? marker.getLatLng() : null
      })
      marker.on('drag', () => {
        const pos = marker.getLatLng()
        let dirty = hasBoundLines(objId)
        if (dirty) _liveObjPos.set(objId, [pos.lat, pos.lng])
        if (_geoGroup.length && _geoDragStart) {
          const moves = applyGroupDelta(_geoGroup, [
            pos.lat - _geoDragStart.lat,
            pos.lng - _geoDragStart.lng
          ])
          for (const [mid, [nlat, nlng]] of moves) {
            markers.get(mid)?.setLatLng([nlat, nlng])
            if (hasBoundLines(mid)) {
              _liveObjPos.set(mid, [nlat, nlng])
              dirty = true
            }
          }
        }
        if (dirty) syncLines()
      })
      marker.on('dragend', () => {
        _markerDragging = false
        const pos = marker.getLatLng()
        // Apply optimistically so bound lines / group members don't flash to the
        // old coord before the async store update lands.
        const obj = props.config.objects.find((o) => o.id === objId)
        if (obj) {
          obj.lat = pos.lat
          obj.lng = pos.lng
        }
        _liveObjPos.delete(objId)
        if (_geoGroup.length && _geoDragStart) {
          const delta = applyGroupDelta(_geoGroup, [
            pos.lat - _geoDragStart.lat,
            pos.lng - _geoDragStart.lng
          ])
          const moves = [{ id: objId, lat: pos.lat, lng: pos.lng }]
          for (const [mid, [nlat, nlng]] of delta) {
            const mo = props.config.objects.find((o) => o.id === mid)
            if (mo) {
              mo.lat = nlat
              mo.lng = nlng
            }
            _liveObjPos.delete(mid)
            moves.push({ id: mid, lat: nlat, lng: nlng })
          }
          _geoGroup = []
          _geoDragStart = null
          emit('latlngs-drag-end', moves)
        } else {
          emit('latlng-drag-end', objId, pos.lat, pos.lng)
        }
      })
      marker.addTo(leafletMap!)
      markers.set(objId, marker)
    }
  }

  // Remove stale markers
  for (const [id, marker] of markers) {
    if (!currentIds.has(id)) {
      marker.remove()
      markers.delete(id)
    }
  }
}

const _handleIconCache = new Map<string, L.DivIcon>()
function makeHandleIcon(color: string): L.DivIcon {
  const cached = _handleIconCache.get(color)
  if (cached) return cached
  const icon = L.divIcon({
    className: '',
    html: `<div style="width:10px;height:10px;background:${color};border:2px solid white;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.5)"></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5]
  })
  _handleIconCache.set(color, icon)
  return icon
}

function resolveLineColor(obj: BoardObjectType): string {
  return obj.line_color ?? stateColor(obj.id)
}

function geoBearing(p1: [number, number], p2: [number, number]): number {
  const lat1 = (p1[0] * Math.PI) / 180
  const lat2 = (p2[0] * Math.PI) / 180
  const dLng = ((p2[1] - p1[1]) * Math.PI) / 180
  const y = Math.sin(dLng) * Math.cos(lat2)
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng)
  return (Math.atan2(y, x) * 180) / Math.PI
}

function makeArrowIcon(color: string, deg: number): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<svg width="12" height="12" viewBox="-6 -6 12 12" style="transform:rotate(${deg}deg);overflow:visible"><polygon points="0,-7 5,5 -5,5" fill="${escapeHtml(color)}"/></svg>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6]
  })
}

function makeLineLabelIcon(text: string, label: LabelConfig): L.DivIcon {
  const color = label.color || 'white'
  const size = label.size || 11
  const bg =
    label.background && label.background !== 'transparent' ? label.background : 'transparent'
  const shadow =
    bg === 'transparent'
      ? 'text-shadow: -1px -1px 0 rgba(0,0,0,0.85), 1px -1px 0 rgba(0,0,0,0.85), -1px 1px 0 rgba(0,0,0,0.85), 1px 1px 0 rgba(0,0,0,0.85);'
      : ''
  return L.divIcon({
    className: '',
    html: `<div style="
      color: ${color};
      font-size: ${size}px;
      font-weight: 500;
      background: ${bg};
      ${shadow}
      white-space: nowrap;
      pointer-events: none;
      padding: ${bg === 'transparent' ? '0' : '1px 4px'};
      border-radius: 2px;
    ">${escapeHtml(text)}</div>`,
    iconAnchor: [-label.x, -label.y]
  })
}

function midpoint(p1: [number, number], p2: [number, number]): [number, number] {
  return [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2]
}

// Live marker positions during an in-flight drag, so bound lines follow live.
const _liveObjPos = new Map<string, [number, number]>()

// Group drag (multi-selection): the other selected markers move with the grabbed
// one by the same lat/lng delta.
let _geoDragStart: L.LatLng | null = null
let _geoGroup: GroupMember[] = []
let _markerDragging = false

// Shift+drag marquee selection (plain drag stays map-pan). Coords are leaflet
// container points.
const {
  rect: mqRect,
  visible: mqVisible,
  active: mqActive,
  moved: mqMoved,
  additive: mqAdditive,
  begin: mqBegin,
  update: mqUpdate,
  reset: mqReset
} = useMarquee()

function onMarqueeMove(e: MouseEvent) {
  if (!mqActive.value || !leafletMap) return
  e.preventDefault()
  const p = leafletMap.mouseEventToContainerPoint(e)
  mqUpdate(p.x, p.y)
}

function onMarqueeUp() {
  document.removeEventListener('mousemove', onMarqueeMove, true)
  document.removeEventListener('mouseup', onMarqueeUp, true)
  if (!mqActive.value || !leafletMap) return
  const r = mqRect.value
  const wasMoved = mqMoved.value
  const additive = mqAdditive.value
  mqReset()
  leafletMap.dragging.enable()
  if (!wasMoved) return
  const ids = props.config.objects
    .filter((o) => o.type !== 'line' && o.lat != null && o.lng != null)
    .filter((o) => {
      const p = leafletMap!.latLngToContainerPoint([o.lat!, o.lng!])
      return p.x >= r.left && p.x <= r.left + r.width && p.y >= r.top && p.y <= r.top + r.height
    })
    .map((o) => o.id)
  emit('marquee-select', ids, additive)
}

function onMarqueeStart(e: L.LeafletMouseEvent) {
  if (!props.editMode || props.preview || !leafletMap) return
  if (!e.originalEvent.shiftKey) return
  L.DomEvent.preventDefault(e.originalEvent)
  leafletMap.dragging.disable()
  mqBegin(
    e.containerPoint.x,
    e.containerPoint.y,
    e.originalEvent.ctrlKey || e.originalEvent.metaKey
  )
  document.addEventListener('mousemove', onMarqueeMove, true)
  document.addEventListener('mouseup', onMarqueeUp, true)
}

function boundEndpoint(refId: string | null | undefined): [number, number] | null {
  if (!refId) return null
  const live = _liveObjPos.get(refId)
  if (live) return live
  const o = props.config.objects.find((obj) => obj.id === refId)
  return o && o.lat != null && o.lng != null ? [o.lat, o.lng] : null
}

function hasBoundLines(objId: string): boolean {
  return props.config.objects.some(
    (o) => o.type === 'line' && (o.start_ref === objId || o.end_ref === objId)
  )
}

const BOUND_COLOR = '#22c55e'

// Offset a bound endpoint's handle ~16 screen px toward the other end so it
// clears the connected marker and leaves the marker grabbable.
function nudgedHandle(
  pt: [number, number],
  toward: [number, number],
  bound: boolean
): [number, number] {
  if (!bound || !leafletMap) return pt
  const p = leafletMap.latLngToContainerPoint(pt)
  const t = leafletMap.latLngToContainerPoint(toward)
  const dx = t.x - p.x
  const dy = t.y - p.y
  const len = Math.sqrt(dx * dx + dy * dy)
  if (len < 1) return pt
  const d = Math.min(16, len / 2)
  const ll = leafletMap.containerPointToLatLng(L.point(p.x + (dx / len) * d, p.y + (dy / len) * d))
  return [ll.lat, ll.lng]
}

// Nearest non-line marker within ~24 screen px of a dropped handle, for binding.
function markerNear(latlng: L.LatLng, lineId: string): string | null {
  if (!leafletMap) return null
  const p = leafletMap.latLngToContainerPoint(latlng)
  let best: string | null = null
  let bestDist = 24
  for (const obj of props.config.objects) {
    if (obj.id === lineId || obj.type === 'line' || obj.lat == null || obj.lng == null) continue
    const d = p.distanceTo(leafletMap.latLngToContainerPoint([obj.lat, obj.lng]))
    if (d <= bestDist) {
      bestDist = d
      best = obj.id
    }
  }
  return best
}

function syncLines() {
  if (!leafletMap) return
  const lineObjs = props.config.objects.filter(
    (o) => o.type === 'line' && o.lat != null && o.lng != null && o.lat2 != null && o.lng2 != null
  )
  const currentIds = new Set(lineObjs.map((o) => o.id))

  for (const obj of lineObjs) {
    const color = resolveLineColor(obj)
    const borderColor = obj.line_color_border ?? null
    const p1 = boundEndpoint(obj.start_ref) ?? ([obj.lat!, obj.lng!] as [number, number])
    const p2 = boundEndpoint(obj.end_ref) ?? ([obj.lat2!, obj.lng2!] as [number, number])
    const style = obj.line_style ?? 'plain'
    const dashArray = style === 'dashed' ? '8 6' : undefined
    const hasEnd = style === 'arrow_end' || style === 'arrow_both'
    const hasStart = style === 'arrow_start' || style === 'arrow_both'

    const labelCfg = obj.label
    const labelText = labelCfg?.show !== false ? (labelCfg?.text ?? '') : ''
    const mid = midpoint(p1, p2)

    if (lines.has(obj.id)) {
      const entry = lines.get(obj.id)!
      if (entry.border) {
        entry.border.setLatLngs([p1, p2])
        entry.border.setStyle({ color: borderColor ?? 'transparent', dashArray })
        if (!borderColor) {
          entry.border.remove()
          entry.border = null
        }
      } else if (borderColor) {
        entry.border = L.polyline([p1, p2], {
          color: borderColor,
          weight: 5,
          dashArray
        }).addTo(leafletMap!)
        entry.polyline.bringToFront()
      }
      entry.polyline.setLatLngs([p1, p2])
      entry.polyline.setStyle({ color, dashArray })
      entry.handle1.setLatLng(nudgedHandle(p1, p2, !!obj.start_ref))
      entry.handle2.setLatLng(nudgedHandle(p2, p1, !!obj.end_ref))
      entry.handle1.setIcon(makeHandleIcon(obj.start_ref ? BOUND_COLOR : color))
      entry.handle2.setIcon(makeHandleIcon(obj.end_ref ? BOUND_COLOR : color))
      if (props.editMode) {
        entry.handle1.dragging?.enable()
        entry.handle2.dragging?.enable()
      } else {
        entry.handle1.dragging?.disable()
        entry.handle2.dragging?.disable()
      }
      if (labelText && labelCfg) {
        if (entry.label) {
          entry.label.setLatLng(mid)
          entry.label.setIcon(makeLineLabelIcon(labelText, labelCfg))
        } else {
          entry.label = L.marker(mid, {
            icon: makeLineLabelIcon(labelText, labelCfg),
            interactive: false
          }).addTo(leafletMap!)
        }
      } else if (entry.label) {
        entry.label.remove()
        entry.label = null
      }
      if (hasEnd) {
        const icon = makeArrowIcon(color, geoBearing(p1, p2))
        if (entry.arrowEnd) {
          entry.arrowEnd.setLatLng(p2)
          entry.arrowEnd.setIcon(icon)
        } else entry.arrowEnd = L.marker(p2, { icon, interactive: false }).addTo(leafletMap!)
      } else if (entry.arrowEnd) {
        entry.arrowEnd.remove()
        entry.arrowEnd = null
      }
      if (hasStart) {
        const icon = makeArrowIcon(color, geoBearing(p2, p1))
        if (entry.arrowStart) {
          entry.arrowStart.setLatLng(p1)
          entry.arrowStart.setIcon(icon)
        } else entry.arrowStart = L.marker(p1, { icon, interactive: false }).addTo(leafletMap!)
      } else if (entry.arrowStart) {
        entry.arrowStart.remove()
        entry.arrowStart = null
      }
    } else {
      const border = borderColor
        ? L.polyline([p1, p2], { color: borderColor, weight: 5, dashArray }).addTo(leafletMap!)
        : null
      const polyline = L.polyline([p1, p2], { color, weight: 3, dashArray }).addTo(leafletMap!)
      const handle1 = L.marker(nudgedHandle(p1, p2, !!obj.start_ref), {
        icon: makeHandleIcon(obj.start_ref ? BOUND_COLOR : color),
        draggable: props.editMode
      }).addTo(leafletMap!)
      const handle2 = L.marker(nudgedHandle(p2, p1, !!obj.end_ref), {
        icon: makeHandleIcon(obj.end_ref ? BOUND_COLOR : color),
        draggable: props.editMode
      }).addTo(leafletMap!)
      const label =
        labelText && labelCfg
          ? L.marker(mid, {
              icon: makeLineLabelIcon(labelText, labelCfg),
              interactive: false
            }).addTo(leafletMap!)
          : null
      const arrowEnd = hasEnd
        ? L.marker(p2, {
            icon: makeArrowIcon(color, geoBearing(p1, p2)),
            interactive: false
          }).addTo(leafletMap!)
        : null
      const arrowStart = hasStart
        ? L.marker(p1, {
            icon: makeArrowIcon(color, geoBearing(p2, p1)),
            interactive: false
          }).addTo(leafletMap!)
        : null

      const objId = obj.id
      polyline.on('click', (e: L.LeafletMouseEvent) => {
        if (props.preview) return
        L.DomEvent.stopPropagation(e)
        const cur = props.config.objects.find((o) => o.id === objId)
        if (cur) emit('object-click', cur, e.originalEvent)
      })
      polyline.on('contextmenu', (e: L.LeafletMouseEvent) => {
        if (props.preview) return
        L.DomEvent.stopPropagation(e)
        const cur = props.config.objects.find((o) => o.id === objId)
        if (!cur) return
        if (props.editMode) emit('object-contextmenu', cur)
        else emit('object-contextmenu-view', cur, e.originalEvent.clientX, e.originalEvent.clientY)
      })
      polyline.on('mouseover', (e: L.LeafletMouseEvent) => {
        if (props.preview || props.editMode) return
        const cur = props.config.objects.find((o) => o.id === objId)
        if (cur) emit('object-hover', cur, e.originalEvent)
      })
      polyline.on('mouseout', () => {
        if (props.preview) return
        emit('object-hover-leave')
      })
      handle1.on('dragend', () => {
        const pos = handle1.getLatLng()
        const ref = markerNear(pos, objId)
        if (ref) {
          const o = props.config.objects.find((x) => x.id === ref)
          emit('endpoint-bind', objId, 1, o?.lat ?? pos.lat, o?.lng ?? pos.lng, ref)
        } else {
          emit('endpoint-bind', objId, 1, pos.lat, pos.lng, null)
        }
      })
      handle2.on('dragend', () => {
        const pos = handle2.getLatLng()
        const ref = markerNear(pos, objId)
        if (ref) {
          const o = props.config.objects.find((x) => x.id === ref)
          emit('endpoint-bind', objId, 2, o?.lat ?? pos.lat, o?.lng ?? pos.lng, ref)
        } else {
          emit('endpoint-bind', objId, 2, pos.lat, pos.lng, null)
        }
      })
      lines.set(objId, { polyline, border, handle1, handle2, label, arrowEnd, arrowStart })
    }

    // Tag the polyline's DOM path with the object id so the parent's action bar
    // (which anchors via [data-object-id]) can attach to a selected line, and
    // give a selected line a glow — markers carry both, lines lacked them.
    const pathEl = lines.get(obj.id)?.polyline.getElement() as SVGElement | null
    if (pathEl) {
      pathEl.setAttribute('data-object-id', obj.id)
      pathEl.style.filter = isSelected(obj.id)
        ? 'drop-shadow(0 0 4px #4ade80) drop-shadow(0 0 2px #4ade80)'
        : ''
    }
  }

  for (const [id, entry] of lines) {
    if (!currentIds.has(id)) {
      entry.border?.remove()
      entry.polyline.remove()
      entry.handle1.remove()
      entry.handle2.remove()
      entry.label?.remove()
      entry.arrowEnd?.remove()
      entry.arrowStart?.remove()
      lines.delete(id)
    }
  }
}

// The tile proxy requires auth, but Leaflet's <img> tiles cannot carry an
// Authorization header — a short-lived stream ticket travels as a query
// param instead (same pattern as the SSE stream), keeping the long-lived
// access token out of proxy logs. Refreshed before its TTL so panning a
// long-open board doesn't hit 401 tiles.
const tileTicket = ref('')
const TILE_TICKET_REFRESH_MS = 4 * 60_000 // ticket TTL is 5 min
let tileTicketTimer: ReturnType<typeof setInterval> | null = null

async function refreshTileTicket() {
  if (!auth.accessToken) return
  try {
    tileTicket.value = (await authApi.streamTicket(auth.accessToken)).ticket
  } catch {
    // Older backend without the ticket endpoint — the access token works too.
    tileTicket.value = auth.accessToken
  }
}

function applyTileSettings() {
  if (!leafletMap) return
  const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null
  // External tile_url overrides stay untouched; only the proxy needs auth.
  const url = wv?.tile_url || `${DEFAULT_TILE_URL}?token=${encodeURIComponent(tileTicket.value)}`
  if (tileLayer) tileLayer.remove()
  tileLayer = L.tileLayer(url, {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(leafletMap)
  const pane = leafletMap.getPane('tilePane') as HTMLElement | undefined
  if (pane) pane.style.filter = wv?.tile_saturate != null ? `saturate(${wv.tile_saturate}%)` : ''
}

function fitAll() {
  if (!leafletMap) return
  const objects = props.config.objects.filter(
    (o) => o.type !== 'line' && o.lat != null && o.lng != null
  )
  if (!objects.length) return
  leafletMap.fitBounds(L.latLngBounds(objects.map((o) => [o.lat!, o.lng!] as [number, number])), {
    padding: [40, 40]
  })
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  if (!mapEl.value) return
  await refreshTileTicket()
  tileTicketTimer = setInterval(refreshTileTicket, TILE_TICKET_REFRESH_MS)
  if (!mapEl.value) return
  const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null
  leafletMap = L.map(mapEl.value, {
    center: [wv?.lat ?? 51, wv?.lng ?? 10],
    zoom: wv?.zoom ?? 5,
    zoomSnap: 0.25,
    // Preview is non-interactive: hide zoom buttons and disable user input
    // so the Settings preview shows a static view that mirrors the form.
    zoomControl: !props.preview,
    dragging: !props.preview,
    scrollWheelZoom: !props.preview,
    doubleClickZoom: !props.preview,
    boxZoom: !props.preview,
    keyboard: !props.preview,
    touchZoom: !props.preview
  })
  leafletMap.on('click', (e) => {
    if (props.placing) {
      emit('canvas-latlng-click', e.latlng.lat, e.latlng.lng)
    } else if (props.editMode && !e.originalEvent.shiftKey) {
      // Clicking the empty map clears the selection (shift is the marquee gesture).
      emit('canvas-click')
    }
  })
  leafletMap.on('contextmenu', (e: L.LeafletMouseEvent) => {
    if (!props.editMode || props.preview) return
    if (!leafletMap) return
    e.originalEvent.preventDefault()
    const c = leafletMap.getCenter()
    // round zoom: leaflet zoomSnap=0.25 → backend WorldmapView.zoom is int
    emit(
      'canvas-contextmenu-view',
      { lat: c.lat, lng: c.lng, zoom: Math.round(leafletMap.getZoom()) },
      { x: e.originalEvent.clientX, y: e.originalEvent.clientY }
    )
  })
  applyTileSettings()
  syncMarkers()
  syncLines()
  // Lets the selected-object action bar re-anchor as the map pans/zooms.
  leafletMap.on('move zoom', () => emit('view-changed'))
  // Shift+drag is a marquee selection in edit mode, not the default box-zoom.
  leafletMap.boxZoom.disable()
  leafletMap.on('mousedown', onMarqueeStart)
  resizeObserver = new ResizeObserver(() => leafletMap?.invalidateSize())
  resizeObserver.observe(mapEl.value)
  // Capture phase so we start a textbox resize before Leaflet's marker-drag.
  mapEl.value.addEventListener('mousedown', onTextboxResizeStart, true)
  if (props.preview) {
    // Iframe-Container ist beim Init oft noch 0×0; ein RAF später ist er
    // gemessen und die Karte muss sich auf den richtigen Center neu setzen.
    requestAnimationFrame(() => {
      if (!leafletMap) return
      leafletMap.invalidateSize()
      if (wv) leafletMap.setView([wv.lat, wv.lng], wv.zoom)
    })
  }
})

onUnmounted(() => {
  if (tileTicketTimer) {
    clearInterval(tileTicketTimer)
    tileTicketTimer = null
  }
  resizeObserver?.disconnect()
  resizeObserver = null
  mapEl.value?.removeEventListener('mousedown', onTextboxResizeStart, true)
  document.removeEventListener('mousemove', onTextboxResizeMove, true)
  document.removeEventListener('mouseup', onTextboxResizeEnd, true)
  document.removeEventListener('mousemove', onMarqueeMove, true)
  document.removeEventListener('mouseup', onMarqueeUp, true)
  leafletMap?.remove()
  leafletMap = null
  tileLayer = null
  markers.clear()
  lines.clear()
})

watch(
  () => [
    props.config.objects,
    props.config.icon_size,
    props.states,
    props.selectedObjectId,
    props.selectedIds,
    props.editMode
  ],
  () => {
    // Skip the marker rebuild while a drag is in flight — setIcon would replace
    // the dragged element and silently abort Leaflet's drag (no dragend fires).
    if (!_markerDragging) syncMarkers()
    syncLines()
    // syncMarkers recreates markers at full opacity, so re-apply dimming
    // here too — this is also where live state polls land (states mutate
    // in place, so a non-deep watch on props.states wouldn't fire).
    applyFilterDimming()
    // setIcon replaces the selected marker's DOM node; tell the parent to
    // re-resolve the action-bar anchor.
    emit('view-changed')
  },
  { deep: true }
)

watch([() => props.filterNeedle ?? '', () => props.problemsOnly], () => applyFilterDimming())

function applyFilterDimming(): void {
  const needle = props.filterNeedle ?? ''
  const filterActive = needle.trim() !== '' || !!props.problemsOnly
  for (const obj of props.config.objects) {
    const matches =
      objectMatchesFilter(obj, needle) &&
      passesProblemFilter(obj, props.problemsOnly, props.states[obj.id]?.state)
    const opacity = matches ? 1 : DIMMED_OPACITY
    const m = markers.get(obj.id)
    if (m) {
      m.setOpacity(opacity)
      const el = m.getElement()
      if (el) el.style.filter = matches ? '' : DIMMED_FILTER
      // Bring-to-front/back maps the object's z to the marker stacking order;
      // a filter match still boosts above everything.
      m.setZIndexOffset((filterActive && matches ? 10000 : 0) + markerZBase(obj))
    }
    const line = lines.get(obj.id)
    if (line) {
      line.polyline.setStyle({ opacity })
      line.border?.setStyle({ opacity })
      line.label?.setOpacity(opacity)
      line.arrowEnd?.setOpacity(opacity)
      line.arrowStart?.setOpacity(opacity)
    }
  }
}

watch(
  () => props.placing,
  (v) => {
    if (mapEl.value) mapEl.value.style.cursor = v ? 'crosshair' : ''
  }
)

watch(() => {
  const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null
  return [wv?.tile_url, wv?.tile_saturate]
}, applyTileSettings)

// The proxy tile URL embeds the ticket — rebuild the layer whenever it
// rotates so tiles fetched later don't 401 with the expired one.
watch(tileTicket, () => applyTileSettings())
watch(
  () => auth.accessToken,
  () => refreshTileTicket()
)

watch(
  () => {
    const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null
    return wv ? `${wv.lat}|${wv.lng}|${wv.zoom}` : ''
  },
  () => {
    if (!leafletMap) return
    const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null
    if (!wv) return
    leafletMap.setView([wv.lat, wv.lng], wv.zoom)
  }
)

function getView() {
  if (!leafletMap) return null
  const c = leafletMap.getCenter()
  return { lat: c.lat, lng: c.lng, zoom: Math.round(leafletMap.getZoom()) }
}

function getContainerSize(): { width: number; height: number } | null {
  if (!mapEl.value) return null
  const r = mapEl.value.getBoundingClientRect()
  return { width: r.width, height: r.height }
}

function setView(lat: number, lng: number, zoom: number) {
  leafletMap?.setView([lat, lng], zoom)
}

defineExpose({ getView, getContainerSize, setView, fitAll })
</script>

<style scoped>
.orb-worldmap {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.orb-worldmap__map {
  position: absolute;
  inset: 0;
}

.orb-worldmap__marquee {
  position: absolute;
  z-index: 600;
  border: 1px solid var(--color-corporate-green-50, #4ade80);
  background: rgb(74 222 128 / 12%);
  pointer-events: none;
}
</style>
