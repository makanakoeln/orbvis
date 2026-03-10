<template>
  <div ref="mapEl" class="absolute inset-0 z-0" :class="placing ? 'cursor-crosshair' : ''" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { MapConfig, MapObject as MapObjectType, ObjectState } from '@/types/api'

const props = defineProps<{
  config: MapConfig
  states: Record<string, ObjectState>
  editMode: boolean
  placing: boolean
  selectedObjectId: string | null
}>()

const emit = defineEmits<{
  'object-click': [obj: MapObjectType]
  'object-contextmenu': [obj: MapObjectType]
  'object-contextmenu-view': [obj: MapObjectType, x: number, y: number]
  'object-hover': [obj: MapObjectType, event: MouseEvent]
  'object-hover-leave': []
  'canvas-latlng-click': [lat: number, lng: number]
  'latlng-drag-end': [id: string, lat: number, lng: number]
}>()

const mapEl = ref<HTMLDivElement | null>(null)
let leafletMap: L.Map | null = null
const markers = new Map<string, L.Marker>()

function stateColor(id: string): string {
  const s = props.states[id]?.state
  if (!s) return '#6b7280'
  switch (s) {
    case 'UP': case 'OK': return '#22c55e'
    case 'DOWN': case 'CRITICAL': return '#ef4444'
    case 'WARNING': return '#f59e0b'
    case 'UNKNOWN': return '#f97316'
    case 'UNREACHABLE': return '#a855f7'
    default: return '#6b7280'
  }
}

function displayName(obj: MapObjectType): string {
  if (obj.label_text) return obj.label_text
  if (obj.host_name && obj.service_description) return `${obj.host_name}/${obj.service_description}`
  return obj.host_name ?? obj.group_name ?? obj.map_name ?? obj.id
}

function makeDivIcon(obj: MapObjectType): L.DivIcon {
  const color = stateColor(obj.id)
  const size = obj.icon_size ?? props.config.globals.icon_size ?? 22
  const label = obj.label_show !== false ? displayName(obj) : ''
  const selected = props.selectedObjectId === obj.id

  let iconHtml: string
  if (obj.icon) {
    const outline = selected ? 'outline: 3px solid white; outline-offset: 2px; border-radius: 3px;' : ''
    iconHtml = `<img src="/icons/${obj.icon}" style="width:${size}px;height:${size}px;object-fit:contain;display:block;${outline}" />`
  } else {
    iconHtml = `<div style="
        width: ${size}px; height: ${size}px;
        background: ${color};
        border-radius: 50%;
        border: 2px solid rgba(0,0,0,0.35);
        box-shadow: 0 1px 4px rgba(0,0,0,0.5)${selected ? `, 0 0 0 3px white` : ''};
        position: relative;
      "></div>`
  }

  return L.divIcon({
    className: '',
    html: iconHtml + (label ? `<div style="
        text-align: center;
        color: white;
        font-size: 11px;
        font-weight: 500;
        text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7);
        white-space: nowrap;
        margin-top: 3px;
      ">${label}</div>` : ''),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  })
}

function syncMarkers() {
  if (!leafletMap) return
  const objects = props.config.objects.filter(o => o.type !== 'line')
  const currentIds = new Set(objects.map(o => o.id))

  for (const obj of objects) {
    const lat = obj.lat ?? props.config.globals.worldmap_lat ?? 51
    const lng = obj.lng ?? props.config.globals.worldmap_lng ?? 10
    const icon = makeDivIcon(obj)
    const objId = obj.id

    if (markers.has(objId)) {
      const marker = markers.get(objId)!
      marker.setLatLng([lat, lng])
      marker.setIcon(icon)
      if (props.editMode) marker.dragging?.enable()
      else marker.dragging?.disable()
    } else {
      const marker = L.marker([lat, lng], { icon, draggable: props.editMode })
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e)
        const current = props.config.objects.find(o => o.id === objId)
        if (current) emit('object-click', current)
      })
      marker.on('contextmenu', (e: L.LeafletMouseEvent) => {
        L.DomEvent.stopPropagation(e)
        const current = props.config.objects.find(o => o.id === objId)
        if (!current) return
        if (props.editMode) {
          emit('object-contextmenu', current)
        } else {
          emit('object-contextmenu-view', current, e.originalEvent.clientX, e.originalEvent.clientY)
        }
      })
      marker.on('mouseover', (e: L.LeafletMouseEvent) => {
        const current = props.config.objects.find(o => o.id === objId)
        if (current) emit('object-hover', current, e.originalEvent)
      })
      marker.on('mouseout', () => {
        emit('object-hover-leave')
      })
      marker.on('dragend', () => {
        const pos = marker.getLatLng()
        emit('latlng-drag-end', objId, pos.lat, pos.lng)
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

onMounted(() => {
  if (!mapEl.value) return
  const g = props.config.globals
  leafletMap = L.map(mapEl.value, {
    center: [g.worldmap_lat ?? 51, g.worldmap_lng ?? 10],
    zoom: g.worldmap_zoom ?? 5,
  })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(leafletMap)
  leafletMap.on('click', (e) => {
    if (props.placing) {
      emit('canvas-latlng-click', e.latlng.lat, e.latlng.lng)
    }
  })
  syncMarkers()
})

onUnmounted(() => {
  leafletMap?.remove()
  leafletMap = null
  markers.clear()
})

watch(
  () => [props.config.objects, props.states, props.selectedObjectId, props.editMode],
  syncMarkers,
  { deep: true },
)

function getView() {
  if (!leafletMap) return null
  const c = leafletMap.getCenter()
  return { lat: c.lat, lng: c.lng, zoom: leafletMap.getZoom() }
}

defineExpose({ getView })
</script>
