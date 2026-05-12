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
import { objectMatchesFilter } from '@/utils/objectFilter';
import { STATE_COLORS } from '@/utils/stateColors';

const props = defineProps<{
    config: BoardConfig;
    states: Record<string, ObjectState>;
    editMode: boolean;
    placing: boolean;
    selectedObjectId: string | null;
    filterNeedle?: string;
}>();

const emit = defineEmits<{
    'object-click': [obj: BoardObjectType, event: MouseEvent];
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
    border: L.Polyline | null;
    handle1: L.Marker;
    handle2: L.Marker;
    label: L.Marker | null;
    arrowEnd: L.Marker | null;
    arrowStart: L.Marker | null;
};
const lines = new Map<string, LineEntry>();

// Default to OrbVis' own caching tile proxy (backend route /api/v1/maps/tiles).
// First-time fetches still hit OSM through the proxy, but subsequent loads come
// from the local on-disk cache and render near-instantly. Boards may override
// this via WorldmapView.tile_url to point at any other OSM-compatible source.
const DEFAULT_TILE_URL = `${import.meta.env.BASE_URL}api/v1/maps/tiles/{z}/{x}/{y}.png`;

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
    const escapedName = escapeHtml(getBoardObjectName(obj));
    const label = obj.label?.show !== false ? escapedName : '';
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
    const textOnly = obj.display?.mode === 'text';
    let iconHtml: string;
    if (textOnly) {
        const txtColor = obj.label?.color || color;
        const txtSize = obj.label?.size ?? Math.max(12, Math.round(size * 0.5));
        const selRing = selected ? 'outline:2px solid #4ade80;outline-offset:2px;' : '';
        iconHtml = `<div style="
        color: ${txtColor};
        font-size: ${txtSize}px;
        font-weight: 600;
        white-space: nowrap;
        text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7);
        padding: 1px 6px;
        border-radius: 4px;
        background: rgba(0,0,0,0.55);
        ${selRing}
      ">${escapedName}</div>`;
    } else if (iconFile) {
        const outline = selected ? 'filter: drop-shadow(0 0 6px #4ade80);' : '';
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

    const state = props.states[obj.id];
    const badgeStyle =
        'position:absolute;width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 1px 3px rgba(0,0,0,0.5);';
    const ackBadge = state?.acknowledged
        ? `<span style="${badgeStyle}top:-6px;right:-6px;background:#f59e0b;color:#1c1917;" title="Acknowledged">
        <svg width="10" height="10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
       </span>`
        : '';
    const downtimeBadge = state?.in_downtime
        ? `<span style="${badgeStyle}top:-6px;left:-6px;background:#3b82f6;color:white;" title="In downtime">
        <svg width="10" height="10" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
       </span>`
        : '';

    const labelSize = obj.label?.size ?? 11;
    const labelColor = obj.label?.color || 'white';
    const labelBg = obj.label?.background;
    const labelBgStyle =
        labelBg && labelBg !== 'transparent'
            ? `background:${labelBg};padding:1px 5px;border-radius:3px;`
            : '';
    const labelOffsetX = obj.label?.x ?? 0;
    const labelOffsetY = obj.label?.y ?? 0;
    const labelHtml =
        label && !textOnly
            ? `<div style="
        position:absolute;
        top:100%;
        left:50%;
        transform: translate(calc(-50% + ${labelOffsetX}px), ${labelOffsetY}px);
        text-align: center;
        color: ${labelColor};
        font-size: ${labelSize}px;
        font-weight: 500;
        text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7);
        white-space: nowrap;
        margin-top: 3px;
        ${labelBgStyle}
      ">${label.replace(/\n/g, '<br>')}</div>`
            : '';

    const wrappedIcon = `<div style="position:relative;display:inline-block;">${iconHtml}${ackBadge}${downtimeBadge}${labelHtml}</div>`;

    return L.divIcon({
        className: '',
        html: wrappedIcon,
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
        const wv =
            props.config.view.type === 'worldmap' ? (props.config.view as WorldmapView) : null;
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
            marker.on('click', (e: L.LeafletMouseEvent) => {
                L.DomEvent.stopPropagation(e);
                const current = props.config.objects.find((o) => o.id === objId);
                if (current) emit('object-click', current, e.originalEvent);
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

function resolveLineColor(obj: BoardObjectType): string {
    return obj.line_color ?? stateColor(obj.id);
}

function geoBearing(p1: [number, number], p2: [number, number]): number {
    const lat1 = (p1[0] * Math.PI) / 180;
    const lat2 = (p2[0] * Math.PI) / 180;
    const dLng = ((p2[1] - p1[1]) * Math.PI) / 180;
    const y = Math.sin(dLng) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
    return (Math.atan2(y, x) * 180) / Math.PI;
}

function makeArrowIcon(color: string, deg: number): L.DivIcon {
    return L.divIcon({
        className: '',
        html: `<svg width="12" height="12" viewBox="-6 -6 12 12" style="transform:rotate(${deg}deg);overflow:visible"><polygon points="0,-7 5,5 -5,5" fill="${escapeHtml(color)}"/></svg>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6],
    });
}

function makeLineLabelIcon(text: string, label: LabelConfig): L.DivIcon {
    const color = label.color || 'white';
    const size = label.size || 11;
    const bg =
        label.background && label.background !== 'transparent' ? label.background : 'transparent';
    const shadow =
        bg === 'transparent'
            ? 'text-shadow: 0 1px 3px rgba(0,0,0,0.9), 0 0 6px rgba(0,0,0,0.7);'
            : '';
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
        (o) =>
            o.type === 'line' && o.lat != null && o.lng != null && o.lat2 != null && o.lng2 != null,
    );
    const currentIds = new Set(lineObjs.map((o) => o.id));

    for (const obj of lineObjs) {
        const color = resolveLineColor(obj);
        const borderColor = obj.line_color_border ?? null;
        const p1: [number, number] = [obj.lat!, obj.lng!];
        const p2: [number, number] = [obj.lat2!, obj.lng2!];
        const style = obj.line_style ?? 'plain';
        const dashArray = style === 'dashed' ? '8 6' : undefined;
        const hasEnd = style === 'arrow_end' || style === 'arrow_both';
        const hasStart = style === 'arrow_start' || style === 'arrow_both';

        const labelCfg = obj.label;
        const labelText = labelCfg?.show !== false ? (labelCfg?.text ?? '') : '';
        const mid = midpoint(p1, p2);

        if (lines.has(obj.id)) {
            const entry = lines.get(obj.id)!;
            if (entry.border) {
                entry.border.setLatLngs([p1, p2]);
                entry.border.setStyle({ color: borderColor ?? 'transparent', dashArray });
                if (!borderColor) {
                    entry.border.remove();
                    entry.border = null;
                }
            } else if (borderColor) {
                entry.border = L.polyline([p1, p2], {
                    color: borderColor,
                    weight: 5,
                    dashArray,
                }).addTo(leafletMap!);
                entry.polyline.bringToFront();
            }
            entry.polyline.setLatLngs([p1, p2]);
            entry.polyline.setStyle({ color, dashArray });
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
            if (hasEnd) {
                const icon = makeArrowIcon(color, geoBearing(p1, p2));
                if (entry.arrowEnd) {
                    entry.arrowEnd.setLatLng(p2);
                    entry.arrowEnd.setIcon(icon);
                } else
                    entry.arrowEnd = L.marker(p2, { icon, interactive: false }).addTo(leafletMap!);
            } else if (entry.arrowEnd) {
                entry.arrowEnd.remove();
                entry.arrowEnd = null;
            }
            if (hasStart) {
                const icon = makeArrowIcon(color, geoBearing(p2, p1));
                if (entry.arrowStart) {
                    entry.arrowStart.setLatLng(p1);
                    entry.arrowStart.setIcon(icon);
                } else
                    entry.arrowStart = L.marker(p1, { icon, interactive: false }).addTo(
                        leafletMap!,
                    );
            } else if (entry.arrowStart) {
                entry.arrowStart.remove();
                entry.arrowStart = null;
            }
        } else {
            const border = borderColor
                ? L.polyline([p1, p2], { color: borderColor, weight: 5, dashArray }).addTo(
                      leafletMap!,
                  )
                : null;
            const polyline = L.polyline([p1, p2], { color, weight: 3, dashArray }).addTo(
                leafletMap!,
            );
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
            const arrowEnd = hasEnd
                ? L.marker(p2, {
                      icon: makeArrowIcon(color, geoBearing(p1, p2)),
                      interactive: false,
                  }).addTo(leafletMap!)
                : null;
            const arrowStart = hasStart
                ? L.marker(p1, {
                      icon: makeArrowIcon(color, geoBearing(p2, p1)),
                      interactive: false,
                  }).addTo(leafletMap!)
                : null;

            const objId = obj.id;
            polyline.on('click', (e: L.LeafletMouseEvent) => {
                L.DomEvent.stopPropagation(e);
                const cur = props.config.objects.find((o) => o.id === objId);
                if (cur) emit('object-click', cur, e.originalEvent);
            });
            polyline.on('contextmenu', (e: L.LeafletMouseEvent) => {
                L.DomEvent.stopPropagation(e);
                const cur = props.config.objects.find((o) => o.id === objId);
                if (!cur) return;
                if (props.editMode) emit('object-contextmenu', cur);
                else
                    emit(
                        'object-contextmenu-view',
                        cur,
                        e.originalEvent.clientX,
                        e.originalEvent.clientY,
                    );
            });
            polyline.on('mouseover', (e: L.LeafletMouseEvent) => {
                const cur = props.config.objects.find((o) => o.id === objId);
                if (cur) emit('object-hover', cur, e.originalEvent);
            });
            polyline.on('mouseout', () => {
                emit('object-hover-leave');
            });
            handle1.on('dragend', () => {
                const pos = handle1.getLatLng();
                emit('latlng-drag-end', objId, pos.lat, pos.lng);
            });
            handle2.on('dragend', () => {
                const pos = handle2.getLatLng();
                emit('latlng2-drag-end', objId, pos.lat, pos.lng);
            });
            lines.set(objId, { polyline, border, handle1, handle2, label, arrowEnd, arrowStart });
        }
    }

    for (const [id, entry] of lines) {
        if (!currentIds.has(id)) {
            entry.border?.remove();
            entry.polyline.remove();
            entry.handle1.remove();
            entry.handle2.remove();
            entry.label?.remove();
            entry.arrowEnd?.remove();
            entry.arrowStart?.remove();
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
    () => props.filterNeedle ?? '',
    () => applyFilterDimming(),
);

function applyFilterDimming(): void {
    const needle = props.filterNeedle ?? '';
    for (const obj of props.config.objects) {
        const opacity = objectMatchesFilter(obj, needle) ? 1 : 0.25;
        const m = markers.get(obj.id);
        if (m) m.setOpacity(opacity);
        const line = lines.get(obj.id);
        if (line) {
            line.polyline.setStyle({ opacity });
            line.border?.setStyle({ opacity });
            line.label?.setOpacity(opacity);
            line.arrowEnd?.setOpacity(opacity);
            line.arrowStart?.setOpacity(opacity);
        }
    }
}

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
