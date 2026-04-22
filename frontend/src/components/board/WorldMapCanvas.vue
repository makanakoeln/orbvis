<template>
  <div ref="mapEl" class="absolute inset-0 z-0" />
</template>

<script setup lang="ts">
import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { onMounted, onUnmounted, ref, watch } from 'vue';

import type {
  BoardConfig,
  BoardObject as BoardObjectType,
  LabelConfig,
  ObjectState,
  WorldmapView,
} from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';
import { STATE_COLORS } from '@/utils/stateColors';

const props = defineProps<{
  config: BoardConfig;
  states: Record<string, ObjectState>;
  editMode: boolean;
  placing: boolean;
  selectedObjectId: string | null;
}>();

const emit = defineEmits<{
  'object-click': [obj: BoardObjectType];
  'object-contextmenu': [obj: BoardObjectType];
  'object-contextmenu-view': [obj: BoardObjectType, x: number, y: number];
  'object-hover': [obj: BoardObjectType, event: MouseEvent];
  'object-hover-leave': [];
  'canvas-latlng-click': [lat: number, lng: number];
  'latlng-drag-end': [id: string, lat: number, lng: number];
  'latlng2-drag-end': [id: string, lat: number, lng: number];
}>();

const mapEl = ref<HTMLDivElement | null>(null);
let leafletMap: L.Map | null = null;
let tileLayer: L.TileLayer | null = null;
const markers = new Map<string, L.Marker>();

type LineEntry = {
  polyline: L.Polyline;
  handle1: L.Marker;
  handle2: L.Marker;
  label: L.Marker | null;
};
const lines = new Map<string, LineEntry>();

const DEFAULT_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

function stateColor(id: string): string {
  const s = props.states[id]?.state;
  return STATE_COLORS[s ?? ''] ?? STATE_COLORS['PENDING'];
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function makeDivIcon(obj: BoardObjectType): L.DivIcon {
  const color = stateColor(obj.id);
  const size = obj.display?.image_size ?? props.config.icon_size ?? 30;
  const label = obj.label?.show !== false ? escapeHtml(getBoardObjectName(obj)) : '';
  const selected = props.selectedObjectId === obj.id;

  const TYPE_CHARS: Record<string, string> = {
    host: 'H',
    service: 'S',
    hostgroup: 'HG',
    servicegroup: 'SG',
    map: 'M',
    image: '◆',
  };
  const typeChar = TYPE_CHARS[obj.type] ?? '?';
  const charSize = Math.max(8, Math.round(size * (typeChar.length > 1 ? 0.34 : 0.42)));

  const iconFile = obj.display?.image ?? obj.image_src;
  let iconHtml: string;
  if (iconFile) {
    const outline = selected
      ? 'outline: 3px solid white; outline-offset: 2px; border-radius: 3px;'
      : '';
    iconHtml = `<img src="${import.meta.env.BASE_URL}images/${iconFile}" style="width:${size}px;height:${size}px;object-fit:contain;display:block;${outline}" />`;
  } else {
    iconHtml = `<div style="
        width: ${size}px; height: ${size}px;
        background: ${color};
        border-radius: 50%;
        border: 2px solid rgba(0,0,0,0.35);
        box-shadow: 0 1px 4px rgba(0,0,0,0.5)${selected ? `, 0 0 0 3px white` : ''};
        display: flex; align-items: center; justify-content: center;
        position: relative;
      "><span style="color:white;font-size:${charSize}px;font-weight:700;line-height:1;user-select:none;">${typeChar}</span></div>`;
  }

  return L.divIcon({
    className: '',
    html:
      iconHtml +
      (label
        ? `<div style="
        text-align: center;
        color: white;
        font-size: 11px;
        font-weight: 500;
        text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7);
        white-space: nowrap;
        margin-top: 3px;
      ">${label.replace(/\n/g, '<br>')}</div>`
        : ''),
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -(size / 2 + 4)],
  });
}

function syncMarkers() {
  if (!leafletMap) return;
  const objects = props.config.objects.filter((o) => o.type !== 'line');
  const currentIds = new Set(objects.map((o) => o.id));

  for (const obj of objects) {
    const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null;
    const lat = obj.lat ?? wv?.lat ?? 51;
    const lng = obj.lng ?? wv?.lng ?? 10;
    const icon = makeDivIcon(obj);
    const objId = obj.id;

    if (markers.has(objId)) {
      const marker = markers.get(objId)!;
      marker.setLatLng([lat, lng]);
      marker.setIcon(icon);
      if (props.editMode) marker.dragging?.enable();
      else marker.dragging?.disable();
    } else {
      const marker = L.marker([lat, lng], { icon, draggable: props.editMode });
      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        const current = props.config.objects.find((o) => o.id === objId);
        if (current) emit('object-click', current);
      });
      marker.on('contextmenu', (e: L.LeafletMouseEvent) => {
        L.DomEvent.stopPropagation(e);
        const current = props.config.objects.find((o) => o.id === objId);
        if (!current) return;
        if (props.editMode) {
          emit('object-contextmenu', current);
        } else {
          emit(
            'object-contextmenu-view',
            current,
            e.originalEvent.clientX,
            e.originalEvent.clientY,
          );
        }
      });
      marker.on('mouseover', (e: L.LeafletMouseEvent) => {
        const current = props.config.objects.find((o) => o.id === objId);
        if (current) emit('object-hover', current, e.originalEvent);
      });
      marker.on('mouseout', () => {
        emit('object-hover-leave');
      });
      marker.on('dragend', () => {
        const pos = marker.getLatLng();
        emit('latlng-drag-end', objId, pos.lat, pos.lng);
      });
      marker.addTo(leafletMap!);
      markers.set(objId, marker);
    }
  }

  // Remove stale markers
  for (const [id, marker] of markers) {
    if (!currentIds.has(id)) {
      marker.remove();
      markers.delete(id);
    }
  }
}

const _handleIconCache = new Map<string, L.DivIcon>();
function makeHandleIcon(color: string): L.DivIcon {
  const cached = _handleIconCache.get(color);
  if (cached) return cached;
  const icon = L.divIcon({
    className: '',
    html: `<div style="width:10px;height:10px;background:${color};border:2px solid white;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.5)"></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  });
  _handleIconCache.set(color, icon);
  return icon;
}

function makeLineLabelIcon(text: string, label: LabelConfig): L.DivIcon {
  const color = label.color || 'white';
  const size = label.size || 11;
  const bg =
    label.background && label.background !== 'transparent' ? label.background : 'transparent';
  const shadow =
    bg === 'transparent' ? 'text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7);' : '';
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
    iconAnchor: [-label.x, -label.y],
  });
}

function midpoint(p1: [number, number], p2: [number, number]): [number, number] {
  return [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2];
}

function syncLines() {
  if (!leafletMap) return;
  const lineObjs = props.config.objects.filter(
    (o) => o.type === 'line' && o.lat != null && o.lng != null && o.lat2 != null && o.lng2 != null,
  );
  const currentIds = new Set(lineObjs.map((o) => o.id));

  for (const obj of lineObjs) {
    const color = stateColor(obj.id);
    const p1: [number, number] = [obj.lat!, obj.lng!];
    const p2: [number, number] = [obj.lat2!, obj.lng2!];

    const labelCfg = obj.label;
    const labelText = labelCfg?.show !== false ? (labelCfg?.text ?? '') : '';
    const mid = midpoint(p1, p2);

    if (lines.has(obj.id)) {
      const entry = lines.get(obj.id)!;
      entry.polyline.setLatLngs([p1, p2]);
      entry.polyline.setStyle({ color });
      entry.handle1.setLatLng(p1);
      entry.handle2.setLatLng(p2);
      entry.handle1.setIcon(makeHandleIcon(color));
      entry.handle2.setIcon(makeHandleIcon(color));
      if (props.editMode) {
        entry.handle1.dragging?.enable();
        entry.handle2.dragging?.enable();
      } else {
        entry.handle1.dragging?.disable();
        entry.handle2.dragging?.disable();
      }
      if (labelText && labelCfg) {
        if (entry.label) {
          entry.label.setLatLng(mid);
          entry.label.setIcon(makeLineLabelIcon(labelText, labelCfg));
        } else {
          entry.label = L.marker(mid, {
            icon: makeLineLabelIcon(labelText, labelCfg),
            interactive: false,
          }).addTo(leafletMap!);
        }
      } else if (entry.label) {
        entry.label.remove();
        entry.label = null;
      }
    } else {
      const polyline = L.polyline([p1, p2], { color, weight: 3 }).addTo(leafletMap!);
      const handle1 = L.marker(p1, {
        icon: makeHandleIcon(color),
        draggable: props.editMode,
      }).addTo(leafletMap!);
      const handle2 = L.marker(p2, {
        icon: makeHandleIcon(color),
        draggable: props.editMode,
      }).addTo(leafletMap!);
      const label =
        labelText && labelCfg
          ? L.marker(mid, {
              icon: makeLineLabelIcon(labelText, labelCfg),
              interactive: false,
            }).addTo(leafletMap!)
          : null;

      const objId = obj.id;
      polyline.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        const cur = props.config.objects.find((o) => o.id === objId);
        if (cur) emit('object-click', cur);
      });
      polyline.on('contextmenu', (e: L.LeafletMouseEvent) => {
        L.DomEvent.stopPropagation(e);
        const cur = props.config.objects.find((o) => o.id === objId);
        if (!cur) return;
        if (props.editMode) emit('object-contextmenu', cur);
        else emit('object-contextmenu-view', cur, e.originalEvent.clientX, e.originalEvent.clientY);
      });
      handle1.on('dragend', () => {
        const pos = handle1.getLatLng();
        emit('latlng-drag-end', objId, pos.lat, pos.lng);
      });
      handle2.on('dragend', () => {
        const pos = handle2.getLatLng();
        emit('latlng2-drag-end', objId, pos.lat, pos.lng);
      });
      lines.set(objId, { polyline, handle1, handle2, label });
    }
  }

  for (const [id, entry] of lines) {
    if (!currentIds.has(id)) {
      entry.polyline.remove();
      entry.handle1.remove();
      entry.handle2.remove();
      entry.label?.remove();
      lines.delete(id);
    }
  }
}

function applyTileSettings() {
  if (!leafletMap) return;
  const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null;
  const url = wv?.tile_url || DEFAULT_TILE_URL;
  if (tileLayer) tileLayer.remove();
  tileLayer = L.tileLayer(url, {
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(leafletMap);
  const pane = leafletMap.getPane('tilePane') as HTMLElement | undefined;
  if (pane) pane.style.filter = wv?.tile_saturate != null ? `saturate(${wv.tile_saturate}%)` : '';
}

function fitAll() {
  if (!leafletMap) return;
  const objects = props.config.objects.filter(
    (o) => o.type !== 'line' && o.lat != null && o.lng != null,
  );
  if (!objects.length) return;
  leafletMap.fitBounds(L.latLngBounds(objects.map((o) => [o.lat!, o.lng!] as [number, number])), {
    padding: [40, 40],
  });
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (!mapEl.value) return;
  const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null;
  leafletMap = L.map(mapEl.value, {
    center: [wv?.lat ?? 51, wv?.lng ?? 10],
    zoom: wv?.zoom ?? 5,
  });
  leafletMap.on('click', (e) => {
    if (props.placing) {
      emit('canvas-latlng-click', e.latlng.lat, e.latlng.lng);
    }
  });
  applyTileSettings();
  syncMarkers();
  syncLines();
  resizeObserver = new ResizeObserver(() => leafletMap?.invalidateSize());
  resizeObserver.observe(mapEl.value);
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  leafletMap?.remove();
  leafletMap = null;
  tileLayer = null;
  markers.clear();
  lines.clear();
});

watch(
  () => [props.config.objects, props.states, props.selectedObjectId, props.editMode],
  () => {
    syncMarkers();
    syncLines();
  },
  { deep: true },
);

watch(
  () => props.placing,
  (v) => {
    if (mapEl.value) mapEl.value.style.cursor = v ? 'crosshair' : '';
  },
);

watch(() => {
  const wv = props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null;
  return [wv?.tile_url, wv?.tile_saturate];
}, applyTileSettings);

function getView() {
  if (!leafletMap) return null;
  const c = leafletMap.getCenter();
  return { lat: c.lat, lng: c.lng, zoom: leafletMap.getZoom() };
}

defineExpose({ getView, fitAll });
</script>
