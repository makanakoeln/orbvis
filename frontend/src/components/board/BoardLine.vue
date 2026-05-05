<template>
    <g>
        <!-- Invisible fat hit-area: always for right-click, move-cursor only in edit mode -->
        <line
            :x1="x1"
            :y1="y1"
            :x2="x2"
            :y2="y2"
            stroke="transparent"
            stroke-width="12"
            :style="editMode ? 'cursor: move' : 'cursor: pointer'"
            @mousedown.prevent.stop="
                editMode ? $emit('line-drag-start', $event, 'move') : undefined
            "
            @contextmenu.prevent.stop="$emit('context-menu', $event)"
            @click.stop="$emit('line-click')"
            @mouseenter="!editMode && $emit('hover', $event)"
            @mouseleave="!editMode && $emit('hover-leave')"
        />

        <!-- Optional gradient stroke when the line carries a weather-color flag. -->
        <defs v-if="useWeatherColor">
            <linearGradient
                :id="gradientId"
                gradientUnits="userSpaceOnUse"
                :x1="x1"
                :y1="y1"
                :x2="x2"
                :y2="y2"
            >
                <stop offset="0%" :stop-color="effectiveLineColor" />
                <stop offset="100%" :stop-color="effectiveLineColor" stop-opacity="0.6" />
            </linearGradient>
        </defs>
        <!-- Border/outline line (rendered behind) — skipped when using a gradient. -->
        <line
            v-if="lineColorBorder && !useWeatherColor"
            :x1="x1"
            :y1="y1"
            :x2="x2"
            :y2="y2"
            :stroke="lineColorBorder"
            :stroke-width="strokeWidthBorder"
            stroke-linecap="round"
            :stroke-dasharray="isDashed ? '6 4' : undefined"
            pointer-events="none"
        />
        <line
            :x1="x1"
            :y1="y1"
            :x2="x2"
            :y2="y2"
            :stroke="useWeatherColor ? `url(#${gradientId})` : effectiveLineColor"
            :stroke-width="strokeWidth"
            stroke-linecap="round"
            :stroke-dasharray="isDashed ? '6 4' : undefined"
            pointer-events="none"
        />
        <!-- Arrow at endpoint -->
        <polygon
            v-if="hasEndArrow"
            :points="arrowPoints(x2, y2, x1, y1)"
            :fill="effectiveLineColor"
            pointer-events="none"
        />
        <!-- Arrow at startpoint -->
        <polygon
            v-if="hasStartArrow"
            :points="arrowPoints(x1, y1, x2, y2)"
            :fill="effectiveLineColor"
            pointer-events="none"
        />
        <!-- Inward arrows: two triangles meeting at the midpoint. -->
        <template v-if="isArrowInward && midArrows">
            <polygon :points="midArrows.left" :fill="effectiveLineColor" pointer-events="none" />
            <polygon :points="midArrows.right" :fill="effectiveLineColor" pointer-events="none" />
        </template>
        <!-- Dot fallback for plain/dashed without arrows. -->
        <circle
            v-if="!hasEndArrow && !hasStartArrow && !isArrowInward"
            :cx="x2"
            :cy="y2"
            r="4"
            :fill="effectiveLineColor"
            pointer-events="none"
        />
        <!-- In/out perfdata labels in boxed badges flanking the midpoint
             at 25% / 75% along the line. -->
        <g v-if="wmLabelAnchors && wmLabelIn" pointer-events="none">
            <rect
                :x="wmLabelAnchors.inX - _labelBoxWidth(wmLabelIn) / 2"
                :y="wmLabelAnchors.inY - 10"
                :width="_labelBoxWidth(wmLabelIn)"
                height="20"
                rx="3"
                fill="white"
                :stroke="effectiveLineColor"
                stroke-width="1.5"
            />
            <text
                :x="wmLabelAnchors.inX"
                :y="wmLabelAnchors.inY"
                text-anchor="middle"
                dominant-baseline="middle"
                font-size="11"
                font-weight="700"
                fill="black"
                >{{ wmLabelIn }}</text
            >
        </g>
        <g v-if="wmLabelAnchors && wmLabelOut" pointer-events="none">
            <rect
                :x="wmLabelAnchors.outX - _labelBoxWidth(wmLabelOut) / 2"
                :y="wmLabelAnchors.outY - 10"
                :width="_labelBoxWidth(wmLabelOut)"
                height="20"
                rx="3"
                fill="white"
                :stroke="effectiveLineColor"
                stroke-width="1.5"
            />
            <text
                :x="wmLabelAnchors.outX"
                :y="wmLabelAnchors.outY"
                text-anchor="middle"
                dominant-baseline="middle"
                font-size="11"
                font-weight="700"
                fill="black"
                >{{ wmLabelOut }}</text
            >
        </g>
        <!-- Single-direction fallback when only one perfdata label fits. -->
        <text
            v-if="wmLabelSingle"
            :x="(x1 + x2) / 2"
            :y="(y1 + y2) / 2 + 16"
            text-anchor="middle"
            font-size="13"
            font-weight="700"
            :fill="effectiveLineColor"
            style="
                paint-order: stroke;
                stroke: var(--bg);
                stroke-width: 4px;
                stroke-linejoin: round;
            "
            pointer-events="none"
            >{{ wmLabelSingle }}</text
        >

        <!-- label text at midpoint -->
        <text
            v-if="props.object.label?.show && props.object.label?.text"
            :x="(x1 + x2) / 2"
            :y="(y1 + y2) / 2 - 10"
            text-anchor="middle"
            :font-size="props.object.label?.size ?? 11"
            font-weight="500"
            :fill="props.object.label?.color ?? '#e4e4e7'"
            pointer-events="none"
            style="
                paint-order: stroke;
                stroke: rgb(0 0 0 / 80%);
                stroke-width: 3px;
                stroke-linejoin: round;
            "
            >{{ props.object.label?.text }}</text
        >

        <!-- Edit handles -->
        <template v-if="editMode">
            <circle
                :cx="x1"
                :cy="y1"
                r="7"
                fill="#3b82f6"
                fill-opacity="0.85"
                stroke="white"
                stroke-width="1.5"
                style="cursor: grab"
                @mousedown.prevent.stop="$emit('line-drag-start', $event, 'start')"
            />
            <circle
                :cx="x2"
                :cy="y2"
                r="7"
                fill="#3b82f6"
                fill-opacity="0.85"
                stroke="white"
                stroke-width="1.5"
                style="cursor: grab"
                @mousedown.prevent.stop="$emit('line-drag-start', $event, 'end')"
            />
        </template>
    </g>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import { metricsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import type { BoardObject, ObjectState } from '@/types/api';
import { getMetric, parsePerfData, utilColor, utilPercent } from '@/utils/perf';
import { STATE_COLORS } from '@/utils/stateColors';

const authStore = useAuthStore();

const props = defineProps<{
    object: BoardObject;
    state: ObjectState | undefined;
    editMode: boolean;
    dragCoords?: { x: number; y: number; x2: number; y2: number };
    connectionId?: string | null;
}>();

defineEmits<{
    'line-drag-start': [event: MouseEvent, mode: 'move' | 'start' | 'end'];
    'context-menu': [event: MouseEvent];
    'line-click': [];
    hover: [event: MouseEvent];
    'hover-leave': [];
}>();

const x1 = computed(() => props.dragCoords?.x ?? props.object.x);
const y1 = computed(() => props.dragCoords?.y ?? props.object.y);
const x2 = computed(() => props.dragCoords?.x2 ?? props.object.x2 ?? props.object.x + 50);
const y2 = computed(() => props.dragCoords?.y2 ?? props.object.y2 ?? props.object.y + 50);

const lineColor = computed(
    () =>
        props.object.line_color ??
        STATE_COLORS[props.state?.state ?? 'PENDING'] ??
        STATE_COLORS['PENDING'],
);
const lineColorBorder = computed(() => props.object.line_color_border ?? null);

const isDashed = computed(() => props.object.line_style === 'dashed');
const isArrowInward = computed(() => props.object.line_style === 'arrow_inward');
// Color the line by inbound/outbound utilization gradient instead of state color.
const useWeatherColor = computed(
    () =>
        props.object.line_weather_color === true &&
        !!(props.object.host_name && props.object.service_description),
);
// Effective stroke / fill color: utilization-based when weather coloring is
// enabled and live, otherwise the configured/state-derived line color.
const effectiveLineColor = computed(() =>
    useWeatherColor.value ? wmColor.value : lineColor.value,
);

// Per-line stroke width. Falls back to a sensible default per style:
// 6 for weather-colored lines (heavier visual weight), 2 otherwise.
const strokeWidth = computed(() => props.object.line_width ?? (useWeatherColor.value ? 6 : 2));
const strokeWidthBorder = computed(() => strokeWidth.value + 2);
const hasEndArrow = computed(
    () => props.object.line_style === 'arrow_end' || props.object.line_style === 'arrow_both',
);
const hasStartArrow = computed(
    () => props.object.line_style === 'arrow_start' || props.object.line_style === 'arrow_both',
);

function arrowPoints(tx: number, ty: number, fx: number, fy: number): string {
    const angle = Math.atan2(ty - fy, tx - fx);
    const len = 12,
        w = 6;
    const p1x = tx - len * Math.cos(angle) + w * Math.sin(angle);
    const p1y = ty - len * Math.sin(angle) - w * Math.cos(angle);
    const p2x = tx - len * Math.cos(angle) - w * Math.sin(angle);
    const p2y = ty - len * Math.sin(angle) + w * Math.cos(angle);
    return `${tx},${ty} ${p1x},${p1y} ${p2x},${p2y}`;
}

// Midpoint inward-facing arrow pair: two triangles nearly touching at the
// line midpoint, each tip pointing toward an endpoint.
function midpointArrows(): { left: string; right: string } | null {
    const dx = x2.value - x1.value;
    const dy = y2.value - y1.value;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 24) return null; // line too short to fit two arrows + gap
    const ux = dx / len;
    const uy = dy / len;
    const midX = (x1.value + x2.value) / 2;
    const midY = (y1.value + y2.value) / 2;
    const gap = 1;
    const arrowLen = 8;
    const arrowW = 5;
    // Tip toward (x2,y2): tip closer to midpoint, base further along the ray.
    const rTipX = midX + ux * gap;
    const rTipY = midY + uy * gap;
    const rBaseX = midX + ux * (gap + arrowLen);
    const rBaseY = midY + uy * (gap + arrowLen);
    // Tip toward (x1,y1): mirror.
    const lTipX = midX - ux * gap;
    const lTipY = midY - uy * gap;
    const lBaseX = midX - ux * (gap + arrowLen);
    const lBaseY = midY - uy * (gap + arrowLen);
    const perpX = -uy * arrowW;
    const perpY = ux * arrowW;
    return {
        right: `${rTipX},${rTipY} ${rBaseX + perpX},${rBaseY + perpY} ${rBaseX - perpX},${rBaseY - perpY}`,
        left: `${lTipX},${lTipY} ${lBaseX + perpX},${lBaseY + perpY} ${lBaseX - perpX},${lBaseY - perpY}`,
    };
}

const midArrows = computed(() => midpointArrows());

// Anchor positions for the inbound/outbound bandwidth labels.
// Placed at ~25%/75% along the line so they always sit clear of the midpoint
// arrows regardless of line length. Pure-pixel offset doesn't scale: short
// lines get cramped, long lines have labels overlapping.
const wmLabelAnchors = computed(() => {
    const dx = x2.value - x1.value;
    const dy = y2.value - y1.value;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len < 80) return null;
    const ux = dx / len;
    const uy = dy / len;
    const midX = (x1.value + x2.value) / 2;
    const midY = (y1.value + y2.value) / 2;
    // 25% of total length from midpoint, clamped so labels stay readable on
    // medium lines and don't run off the endpoints on short ones.
    const offset = Math.max(40, Math.min(len * 0.25, len / 2 - 30));
    return {
        // "in" anchor is on the start side (left of midpoint), "out" is past the midpoint.
        inX: midX - ux * offset,
        inY: midY - uy * offset,
        outX: midX + ux * offset,
        outY: midY + uy * offset,
    };
});

// Approximate label-box width from character count. Used to size the
// background rect under each weathermap label without measuring real text.
function _labelBoxWidth(label: string): number {
    return Math.max(40, label.length * 7 + 14);
}

// Per-utilization color gradient state — driven by inbound/outbound metrics
// when weather coloring is on. Even when off, these still feed the perfdata
// labels (which can be enabled independently).
const gradientId = computed(() => `wm-grad-${props.object.id}`);

const wmMetrics = computed(() => parsePerfData(props.state?.perf_data ?? ''));
const wmMetricIn = computed(() =>
    getMetric(wmMetrics.value, props.object.weathermap_metric ?? undefined),
);
const wmMetricOut = computed(() =>
    getMetric(wmMetrics.value, props.object.weathermap_metric_out ?? undefined),
);
const wmPct = computed(() => {
    const m = wmMetricIn.value ?? wmMetricOut.value;
    return m ? utilPercent(m) : 0;
});
const wmColor = computed(() => utilColor(wmPct.value));

const showsPerfdataLabels = computed(
    () => props.object.line_perfdata_label != null && props.object.line_perfdata_label !== 'none',
);

function _fmtSI(value: number, unit: string): string {
    if (unit === '%') return `${value.toFixed(0)}%`;
    const av = Math.abs(value);
    let v = value;
    let p = '';
    if (av >= 1e12) {
        v = value / 1e12;
        p = 'T';
    } else if (av >= 1e9) {
        v = value / 1e9;
        p = 'G';
    } else if (av >= 1e6) {
        v = value / 1e6;
        p = 'M';
    } else if (av >= 1e3) {
        v = value / 1e3;
        p = 'k';
    }
    const fixed = (Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2)).replace(/\.?0+$/, '');
    return unit ? `${fixed} ${p}${unit}` : p ? `${fixed}${p}` : fixed;
}

function _fmtMetric(m: ReturnType<typeof getMetric>): string {
    if (!m) return '';
    return _fmtSI(m.value, m.unit);
}

// CMK-formatted bandwidth strings via /metrics/perfometer (when host+service set).
// The endpoint applies the proper Metric.unit (kbit/s, MiB/s, …) which the raw
// perfdata doesn't carry. Falls back to client-side _fmtMetric on failure.
const cmkPerfLabel = ref<string | null>(null);

async function _fetchPerfometerLabel(): Promise<void> {
    if (
        !props.object.host_name ||
        !props.object.service_description ||
        !props.connectionId ||
        !authStore.accessToken
    ) {
        return;
    }
    try {
        const r = await metricsApi.getPerfometer(
            props.connectionId,
            props.object.host_name,
            props.object.service_description,
            authStore.accessToken,
        );
        cmkPerfLabel.value = r?.label ?? null;
    } catch {
        cmkPerfLabel.value = null;
    }
}

onMounted(() => {
    if (showsPerfdataLabels.value) void _fetchPerfometerLabel();
});
watch(
    () => props.state?.perf_data,
    () => {
        if (showsPerfdataLabels.value) void _fetchPerfometerLabel();
    },
);

// Split the perfometer label "in / out" into the two halves for separate
// rendering on each side of the midpoint arrows.
const cmkSplit = computed<[string | null, string | null]>(() => {
    if (!cmkPerfLabel.value) return [null, null];
    const parts = cmkPerfLabel.value.split(' / ');
    if (parts.length === 2) return [parts[0]?.trim() || null, parts[1]?.trim() || null];
    return [cmkPerfLabel.value, null];
});

// Format a label for the chosen perfdata mode. 'percent' prefers utilPercent
// of the metric (matches the legacy ---%---><---%--- variant), 'bandwidth'
// shows the raw value with units, 'both' combines them.
function _fmtLabel(m: ReturnType<typeof getMetric>, cmkValue: string | null): string {
    if (!m) return '';
    const mode = props.object.line_perfdata_label ?? 'none';
    if (mode === 'none') return '';
    if (mode === 'percent') return `${utilPercent(m).toFixed(0)}%`;
    const value = cmkValue ?? _fmtMetric(m);
    if (mode === 'both') return `${value} (${utilPercent(m).toFixed(0)}%)`;
    return value; // 'bandwidth'
}

const wmLabelIn = computed(() => _fmtLabel(wmMetricIn.value, cmkSplit.value[0]));
const wmLabelOut = computed(() => _fmtLabel(wmMetricOut.value, cmkSplit.value[1]));
// Fallback: a single value below the midpoint when neither in/out has a real
// metric to render but the mode is non-none — used as a state hint.
const wmLabelSingle = computed(() => {
    if (!showsPerfdataLabels.value) return '';
    if (wmLabelIn.value || wmLabelOut.value) return '';
    return '';
});
</script>
