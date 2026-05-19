<template>
    <!-- Graph embed / native chart -->
    <div
        v-if="object.type === 'graph'"
        class="relative select-none"
        :style="graphWrapperStyle"
        @mouseenter="$emit('hover', $event)"
        @mouseleave="$emit('hover-leave')"
        @contextmenu.prevent="$emit('context-menu', $event)"
    >
        <!-- No permission: render silent empty box -->
        <div
            v-if="state?.state === 'NO_PERMISSION'"
            class="w-full h-full rounded-lg border border-[var(--border)] bg-[var(--bg)]/20"
        />

        <!-- Native chart mode (host linked) -->
        <template v-else-if="isNativeChart">
            <!-- Waiting for first data point / not found -->
            <div
                v-if="!hasChartData"
                class="w-full h-full flex flex-col items-center justify-center gap-1.5 rounded-lg text-[var(--text-muted)]"
                :class="
                    editMode
                        ? 'border-2 border-dashed border-[var(--border)]'
                        : 'border border-[var(--border)]'
                "
            >
                <svg
                    class="w-6 h-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                    />
                </svg>
                <span v-if="dataTimedOut" class="text-xs text-center px-3">{{
                    t('boardSettings.graphNotFound', {
                        service: object.service_description || object.host_name,
                        host: object.host_name,
                    })
                }}</span>
                <span v-else class="text-xs">{{ t('boardSettings.graphWaitingData') }}</span>
            </div>
            <!-- D3 chart -->
            <div
                v-else
                class="w-full h-full flex flex-col overflow-hidden rounded-lg border dark:bg-[var(--bg)]/90 dark:border-white/10 bg-white border-[var(--border)]"
                style="padding: 6px 8px 5px"
            >
                <!-- Header: metric label + current value -->
                <div class="mb-1 flex items-center justify-between shrink-0">
                    <span
                        class="text-[9px] font-semibold tracking-wide text-[var(--text-muted)] truncate"
                    >
                        {{
                            isSingleMetric
                                ? chartMetricLabels[0] || object.graph_metric?.[0]
                                : chartHeaderName
                        }}
                    </span>
                    <span
                        v-if="isSingleMetric"
                        class="text-[10px] font-bold shrink-0 ml-1"
                        :style="{ color: singleMetricColor }"
                        >{{ singleMetricValueStr }}</span
                    >
                    <span
                        v-else
                        class="text-[9px] text-[var(--text-muted)] shrink-0 ml-1 uppercase tracking-wide"
                        >live</span
                    >
                </div>
                <!-- Multi-metric legend -->
                <div
                    v-if="!isSingleMetric"
                    class="flex flex-wrap gap-x-2.5 gap-y-0.5 mb-1 shrink-0"
                >
                    <div
                        v-for="(label, idx) in chartMetricLabels.slice(0, MAX_VISIBLE_SERIES)"
                        :key="label"
                        class="flex items-center gap-1 min-w-0"
                        style="max-width: 50%"
                    >
                        <span
                            class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                            :style="{ background: CHART_PALETTE[idx % CHART_PALETTE.length] }"
                        />
                        <span
                            class="text-[9px] dark:text-[var(--text-muted)] text-[var(--text-muted)] truncate"
                            >{{ label }}</span
                        >
                        <span
                            class="text-[9px] font-mono font-semibold shrink-0 whitespace-nowrap"
                            :style="{ color: CHART_PALETTE[idx % CHART_PALETTE.length] }"
                            >{{
                                fmtValueWithUnit(
                                    normalizeMetricValue(
                                        chartLatestValues[label]?.value ?? 0,
                                        chartLatestValues[label]?.unit,
                                    ),
                                    chartLatestValues[label]?.unit,
                                )
                            }}</span
                        >
                    </div>
                    <span
                        v-if="chartMetricLabels.length > MAX_VISIBLE_SERIES"
                        class="text-[9px] text-[var(--text-muted)] self-center cursor-default"
                        :title="hiddenMetricLabels"
                        >+{{ chartMetricLabels.length - MAX_VISIBLE_SERIES }}</span
                    >
                </div>
                <div class="flex flex-col w-full flex-1 min-h-0">
                    <template v-for="group in chartGroups" :key="group.id">
                        <MetricChart
                            class="w-full flex-1 min-h-0"
                            :data="group.data"
                            :metric-keys="Object.keys(group.data)"
                            :window-secs="(object.graph_time_window ?? 60) * 60"
                            :thresholds="chartThresholds"
                            :unit="Object.values(group.data)[0]?.at(-1)?.unit"
                            :dark="isDark"
                        />
                    </template>
                </div>
            </div>
        </template>
        <!-- URL embed mode -->
        <template v-else>
            <!-- Placeholder: no URL or load error -->
            <div
                v-if="!object.graph_url || graphLoadFailed"
                class="w-full h-full flex flex-col items-center justify-center gap-1.5 border-2 border-dashed border-[var(--border)] rounded-lg text-[var(--text-muted)]"
            >
                <svg
                    class="w-6 h-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="1.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
                    />
                </svg>
                <span class="text-xs">{{
                    object.graph_url
                        ? t('boardSettings.graphLoadFailed')
                        : t('boardSettings.graphNoUrl')
                }}</span>
            </div>
            <!-- img embed -->
            <img
                v-else-if="object.graph_embed_type !== 'iframe'"
                :src="graphSrc"
                class="block w-full h-full object-fill rounded-lg"
                draggable="false"
                @error="graphLoadFailed = true"
                @load="graphLoadFailed = false"
            />
            <!-- iframe embed -->
            <iframe
                v-else
                :src="object.graph_url"
                class="block w-full h-full border-0 rounded-lg"
                sandbox="allow-scripts allow-same-origin"
            />
        </template>
        <!-- Optional caption label -->
        <div
            v-if="object.label?.show && object.label?.text && state?.state !== 'NO_PERMISSION'"
            class="absolute -bottom-5 left-0 right-0 text-center text-xs pointer-events-none px-1.5 py-0.5 rounded"
            :style="labelStyle"
        >
            {{ object.label.text }}
        </div>
        <!-- Resize handle (edit mode only) -->
        <div
            v-if="editMode && resizableTypes.has(object.type)"
            class="absolute bottom-0 right-0 w-5 h-5 cursor-se-resize bg-[var(--color-corporate-green-50)]/70 hover:bg-[var(--color-corporate-green-50)] rounded-tl flex items-center justify-center transition-colors"
            title="Resize"
            @pointerdown.stop="$emit('graph-resize-start', $event)"
        >
            <svg
                class="w-3 h-3 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M4.5 19.5l15-15M19.5 4.5v6m0-6h-6"
                />
            </svg>
        </div>
        <!-- Selection ring -->
        <div
            v-if="selected"
            class="absolute inset-0 rounded-lg ring-2 ring-[var(--color-corporate-green-50)] ring-offset-1 ring-offset-[var(--bg)] pointer-events-none"
        />
    </div>

    <!-- Textbox -->
    <div
        v-else-if="object.type === 'textbox'"
        class="px-2.5 py-1.5 rounded-lg text-sm font-medium whitespace-pre-wrap pointer-events-none ring-1 transition-all overflow-auto"
        :class="selected ? 'ring-[var(--color-corporate-green-50)]' : 'ring-[var(--border)]'"
        :style="textboxStyle"
        @mouseenter="$emit('hover', $event)"
        @mouseleave="$emit('hover-leave')"
        @contextmenu.prevent="$emit('context-menu', $event)"
    >
        {{ object.label?.text || 'Text' }}
    </div>

    <!-- Gadget -->
    <div
        v-else-if="object.display?.mode === 'gadget'"
        class="flex flex-col items-center"
        @mouseenter="$emit('hover', $event)"
        @mouseleave="$emit('hover-leave')"
        @contextmenu.prevent="$emit('context-menu', $event)"
    >
        <div
            :class="
                selected
                    ? 'ring-2 ring-[var(--color-corporate-green-50)] ring-offset-2 ring-offset-[var(--bg)] rounded-xl'
                    : ''
            "
        >
            <GadgetRenderer
                :type="object.display?.gadget_type || 'gauge'"
                :metric="object.display?.gadget_metric"
                :state="state"
                :size="iconSize"
            />
        </div>
        <div
            v-if="object.label?.show && state?.state !== 'NO_PERMISSION'"
            class="mt-1 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
            :style="labelStyle"
        >
            {{ displayName }}
        </div>
    </div>

    <!-- Text-only: object name rendered as state-coloured text, no icon. -->
    <div
        v-else-if="object.display?.mode === 'text'"
        class="flex flex-col items-center"
        @mouseenter="$emit('hover', $event)"
        @mouseleave="$emit('hover-leave')"
        @contextmenu.prevent="$emit('context-menu', $event)"
    >
        <div
            class="font-semibold whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
            :class="
                selected
                    ? 'ring-2 ring-[var(--color-corporate-green-50)] ring-offset-2 ring-offset-[var(--bg)]'
                    : ''
            "
            :style="textOnlyStyle"
        >
            {{ displayName }}
        </div>
    </div>

    <!-- All other types: icon circle (or custom image) + label -->
    <div
        v-else
        class="flex flex-col items-center"
        @mouseenter="$emit('hover', $event)"
        @mouseleave="$emit('hover-leave')"
        @contextmenu.prevent="$emit('context-menu', $event)"
    >
        <!-- Icon with arc ring overlay + badges -->
        <div class="relative">
            <!-- Custom icon image — draggable="false" prevents the browser from starting
           an HTML5 drag operation which would swallow all subsequent mousemove events -->
            <img
                v-if="(object.display?.image ?? object.image_src) && !imgLoadFailed"
                :src="`${BASE_URL}images/${object.display?.image ?? object.image_src}`"
                :style="customIconStyle"
                draggable="false"
                class="object-contain transition-all duration-300 select-none"
                :class="isSvgIcon ? 'svg-icon' : ''"
                @error="imgLoadFailed = true"
            />
            <!-- State circle fallback — SVG for crisp sub-pixel text centering -->
            <!-- Not shown for type=image: if the image fails, the object simply becomes invisible -->
            <svg
                v-else-if="object.type !== 'image' || !imgLoadFailed"
                :width="iconSize"
                :height="iconSize"
                :viewBox="`0 0 ${iconSize} ${iconSize}`"
                overflow="visible"
                class="block select-none transition-all duration-300 rounded-full"
                :class="
                    selected
                        ? 'ring-2 ring-[var(--color-corporate-green-50)] ring-offset-2 ring-offset-[var(--bg)]'
                        : ''
                "
                :style="{ filter: stateGlow }"
            >
                <!-- NOT_FOUND: dimmed dashed outline + transparent fill so the
                     object reads as "missing" rather than as a real state. -->
                <circle
                    v-if="state?.state === 'NOT_FOUND'"
                    :cx="iconSize / 2"
                    :cy="iconSize / 2"
                    :r="iconSize / 2 - 1"
                    fill="rgb(63 63 70 / 40%)"
                    :stroke="stateColorRgb"
                    stroke-width="1.5"
                    stroke-dasharray="3 2"
                />
                <circle
                    v-else
                    :cx="iconSize / 2"
                    :cy="iconSize / 2"
                    :r="iconSize / 2"
                    :fill="stateColorRgb"
                />
                <!-- BI aggregation: tree glyph (root → two leaves) -->
                <g
                    v-if="object.type === 'aggregation'"
                    fill="white"
                    stroke="white"
                    :stroke-width="Math.max(1, iconSize * 0.06)"
                    stroke-linecap="round"
                    style="filter: drop-shadow(0 1px 2px rgb(0 0 0 / 50%))"
                >
                    <line
                        :x1="iconSize / 2"
                        :y1="iconSize * 0.32"
                        :x2="iconSize * 0.32"
                        :y2="iconSize * 0.68"
                    />
                    <line
                        :x1="iconSize / 2"
                        :y1="iconSize * 0.32"
                        :x2="iconSize * 0.68"
                        :y2="iconSize * 0.68"
                    />
                    <circle :cx="iconSize / 2" :cy="iconSize * 0.32" :r="iconSize * 0.11" />
                    <circle :cx="iconSize * 0.32" :cy="iconSize * 0.7" :r="iconSize * 0.1" />
                    <circle :cx="iconSize * 0.68" :cy="iconSize * 0.7" :r="iconSize * 0.1" />
                </g>
                <text
                    v-else
                    :x="iconSize / 2"
                    :y="iconSize / 2"
                    text-anchor="middle"
                    dominant-baseline="central"
                    :fill="state?.state === 'NOT_FOUND' ? stateColorRgb : 'white'"
                    :font-size="charFontSize"
                    font-weight="700"
                    font-family="system-ui,-apple-system,BlinkMacSystemFont,sans-serif"
                    :letter-spacing="typeChar.length > 1 ? -1 : 0.5"
                    style="filter: drop-shadow(0 1px 2px rgb(0 0 0 / 50%))"
                >
                    {{ state?.state === 'NOT_FOUND' ? '?' : typeChar }}
                </text>
            </svg>

            <!-- D3 arc ring overlay — pointer-events:none set via attribute + style to ensure
           it never intercepts mousedown/drag events in any browser -->
            <svg
                v-if="shouldShowRing"
                ref="arcSvgEl"
                :width="svgSize"
                :height="svgSize"
                pointer-events="none"
                class="absolute pointer-events-none"
                :style="{ top: `-${RING_PAD}px`, left: `-${RING_PAD}px`, pointerEvents: 'none' }"
                :title="t('board.utilizationRing')"
            />

            <!-- Stale data badge -->
            <span
                v-if="state?.stale"
                class="absolute -bottom-1.5 -right-1.5 w-5 h-5 rounded-full bg-[var(--color-pending)] text-[var(--text)] flex items-center justify-center shadow-md ring-2 ring-[var(--bg)]"
                title="Stale data"
            >
                <svg
                    class="w-3 h-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                </svg>
            </span>
            <!-- Acknowledged badge -->
            <span
                v-if="state?.acknowledged"
                class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-[var(--color-warning)] text-zinc-900 flex items-center justify-center shadow-md ring-2 ring-[var(--bg)]"
                title="Acknowledged"
            >
                <svg
                    class="w-3 h-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="3.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M4.5 12.75l6 6 9-13.5"
                    />
                </svg>
            </span>
            <!-- Downtime badge -->
            <span
                v-if="state?.in_downtime"
                class="absolute -top-1.5 -left-1.5 w-5 h-5 rounded-full bg-[var(--color-light-blue-50)] text-white flex items-center justify-center shadow-md ring-2 ring-[var(--bg)]"
                title="In downtime"
            >
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                </svg>
            </span>
            <!-- BI aggregation: expanded subtree (when expand_depth > 0) -->
            <AggregationSubtree
                v-if="
                    object.type === 'aggregation' && (object.expand_depth ?? 0) > 0 && state?.tree
                "
                :tree="state.tree"
                :max-depth="object.expand_depth ?? 0"
                :icon-size="iconSize"
                :line-color="object.line_color"
                :line-width="object.line_width"
                @node-enter="(o, s, e) => $emit('subtree-enter', o, s, e)"
                @node-leave="$emit('subtree-leave')"
            />
        </div>
        <!-- Label -->
        <div
            v-if="object.label?.show && state?.state !== 'NO_PERMISSION'"
            class="mt-1.5 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
            :style="labelStyle"
        >
            {{ displayName }}
        </div>
    </div>
</template>

<script setup lang="ts">
import { useMutationObserver } from '@vueuse/core';
import { computed, onMounted, onUnmounted, ref, watch, watchEffect } from 'vue';
import { useI18n } from 'vue-i18n';

import { metricsApi } from '@/api/client';
import { useArcRing } from '@/composables/useArcRing';
import {
    CHART_PALETTE,
    fmtValueWithUnit,
    MAX_VISIBLE_SERIES,
    normalizeMetricValue,
} from '@/composables/useMetricChart';
import { useAuthStore } from '@/stores/auth';
import type { MetricPoint } from '@/stores/states';
import { useStatesStore } from '@/stores/states';
import type { BoardObject, ObjectState } from '@/types/api';
import { getMetric, parsePerfData, utilColor as _utilColor, utilPercent } from '@/utils/perf';

import AggregationSubtree from './AggregationSubtree.vue';
import GadgetRenderer from './GadgetRenderer.vue';
import MetricChart from './MetricChart.vue';

const BASE_URL = import.meta.env.BASE_URL;
const RING_PAD = 6;

const { t } = useI18n();

const props = defineProps<{
    object: BoardObject;
    state: ObjectState | undefined;
    iconSize: number;
    selected?: boolean;
    editMode?: boolean;
    resizeOverride?: { width: number; height: number };
    connectionId?: string;
}>();

defineEmits<{
    hover: [event: MouseEvent];
    'hover-leave': [];
    'context-menu': [event: MouseEvent];
    'graph-resize-start': [evt: PointerEvent];
    'subtree-enter': [obj: BoardObject, state: ObjectState, event: MouseEvent];
    'subtree-leave': [];
}>();

const statesStore = useStatesStore();
const authStore = useAuthStore();

const GRAPH_DATA_TIMEOUT_MS = 15_000;
const dataTimedOut = ref(false);
let dataTimeoutTimer: ReturnType<typeof setTimeout> | null = null;

function _triggerHistoryPrefill() {
    if (
        props.object.type !== 'graph' ||
        !props.object.host_name ||
        !props.connectionId ||
        !authStore.accessToken
    )
        return;
    dataTimedOut.value = false;
    if (dataTimeoutTimer) clearTimeout(dataTimeoutTimer);
    dataTimeoutTimer = setTimeout(() => {
        if (!hasChartData.value) dataTimedOut.value = true;
    }, GRAPH_DATA_TIMEOUT_MS);
    const windowMins = props.object.graph_time_window ?? 60;
    statesStore.prefillMetricHistory(
        props.object.id,
        props.connectionId,
        props.object.host_name,
        props.object.service_description ?? null,
        windowMins,
        authStore.accessToken!,
    );
}

onMounted(_triggerHistoryPrefill);
watch(() => props.object.graph_time_window, _triggerHistoryPrefill);
// Clear stale metric data and re-fetch when host or service changes
watch([() => props.object.host_name, () => props.object.service_description], () => {
    statesStore.clearMetricValues(props.object.id);
    _triggerHistoryPrefill();
});
// Re-trigger when token becomes available (e.g. after async SSO login)
watch(
    () => authStore.accessToken,
    (token, prev) => {
        if (token && !prev) _triggerHistoryPrefill();
    },
);

const isDark = ref(document.documentElement.classList.contains('dark'));
useMutationObserver(
    document.documentElement,
    () => {
        isDark.value = document.documentElement.classList.contains('dark');
    },
    { attributes: true, attributeFilter: ['class'] },
);

// Single arc ring SVG — always a separate overlay SVG that D3 owns exclusively.
// pointer-events="none" on the SVG element (SVG attribute, not CSS) ensures it
// never intercepts mousedown/click events, preserving drag behaviour in edit mode.
const arcSvgEl = ref<SVGSVGElement | null>(null);
const imgLoadFailed = ref(false);

// ---- Graph: native chart mode ----
const isNativeChart = computed(() => props.object.type === 'graph' && !!props.object.host_name);

const chartData = computed((): Record<string, MetricPoint[]> => {
    if (!isNativeChart.value) return {};
    const mv = statesStore.metricValues[props.object.id];
    if (!mv) return {};

    const windowMins = props.object.graph_time_window ?? 60;
    const windowSecs = windowMins * 60;
    const now = Date.now() / 1000;
    const cutoff = now - windowSecs;

    const applyWindow = (pts: MetricPoint[]) => {
        const filtered = pts.filter((p) => p.ts >= cutoff);
        // If nothing falls in the window yet, show last point as baseline
        return filtered.length ? [...filtered] : pts.length ? [pts[pts.length - 1]] : [];
    };

    if (props.object.graph_metric?.length) {
        return Object.fromEntries(
            props.object.graph_metric.filter((m) => mv[m]).map((m) => [m, applyWindow(mv[m])]),
        );
    }
    const graphId = props.object.graph_id;
    if (graphId) {
        const group = (statesStore.metricGraphs[props.object.id] ?? []).find(
            (g) => g.id === graphId,
        );
        if (group) {
            return Object.fromEntries(
                group.metrics.filter((m) => mv[m]).map((m) => [m, applyWindow(mv[m])]),
            );
        }
    }
    return Object.fromEntries(Object.entries(mv).map(([k, v]) => [k, applyWindow(v)]));
});

// Raw metric IDs as they appear in chartData (used for data access)
const chartMetricKeys = computed(() => Object.keys(chartData.value));
// Display labels: human-readable titles when available, raw ID as fallback
const chartMetricLabels = computed(() =>
    chartMetricKeys.value.map((key) => statesStore.metricTitles[props.object.id]?.[key] ?? key),
);
const chartHeaderName = computed(() => {
    const o = props.object;
    // Prefer the graph template group title (e.g. "RAM (Total, cached, buffers)") over host/service
    // when exactly one group is shown — mirrors how CMK labels its graphs.
    const g = chartGroups.value;
    if (g.length === 1 && g[0].title) return g[0].title;
    if (o.host_name && o.service_description) return `${o.host_name} / ${o.service_description}`;
    return o.service_description ?? o.host_name ?? '';
});
const hiddenMetricLabels = computed(() =>
    chartMetricLabels.value.slice(MAX_VISIBLE_SERIES).join(', '),
);
const hasChartData = computed(() =>
    chartMetricKeys.value.some((k) => chartData.value[k].length > 0),
);

// Keyed by display label (title) so the template can use v-for labels as keys
const chartLatestValues = computed(() =>
    Object.fromEntries(
        chartMetricKeys.value.map((k, i) => [
            chartMetricLabels.value[i],
            chartData.value[k].at(-1) ?? null,
        ]),
    ),
);

const graphW = computed(() => props.resizeOverride?.width ?? props.object.graph_width ?? 400);
const graphH = computed(() => props.resizeOverride?.height ?? props.object.graph_height ?? 200);

const chartThresholds = computed(() => {
    if (!isNativeChart.value) return null;
    const ms = parsePerfData(props.state?.perf_data ?? '');
    const m = getMetric(ms, props.object.graph_metric?.[0]);
    return m ? { warn: m.warn, crit: m.crit } : null;
});

const isSingleMetric = computed(() => chartMetricLabels.value.length === 1);

const singleMetricValueStr = computed(() => {
    if (!isSingleMetric.value) return '';
    const label = chartMetricLabels.value[0];
    const pt = chartLatestValues.value[label];
    if (!pt) return '';
    return fmtValueWithUnit(normalizeMetricValue(pt.value, pt.unit), pt.unit);
});

const singleMetricColor = computed(() => {
    const ms = parsePerfData(props.state?.perf_data ?? '');
    const label = props.object.graph_metric?.[0] || chartMetricKeys.value[0];
    const m = getMetric(ms, label);
    if (!m) return CHART_PALETTE[0];
    return _utilColor(utilPercent(m));
});

const chartGroups = computed(() => {
    const groups = statesStore.metricGraphs[props.object.id] ?? [];
    // graph_metric and graph_id filtering is already applied in chartData.
    // If no template groups, render chartData as a single ungrouped chart.
    if (!groups.length || props.object.graph_id || props.object.graph_metric?.length) {
        return [{ id: '_all', title: '', data: chartData.value }];
    }
    // When multiple graph template groups exist but no specific group is pinned via
    // graph_id, show only the first group that has data. Showing all groups at once
    // squishes them into unreadably small sub-charts. Users can pin a group via graph_id.
    for (const g of groups) {
        const data = Object.fromEntries(
            g.metrics.filter((m) => chartData.value[m]).map((m) => [m, chartData.value[m]]),
        );
        if (Object.keys(data).length > 0) {
            return [{ id: g.id, title: g.title, data }];
        }
    }
    return [{ id: '_all', title: '', data: chartData.value }];
});

// ---- Graph: URL embed ----
const graphLoadFailed = ref(false);
const refreshTick = ref(0);

watch(
    () => props.object.graph_url,
    () => {
        graphLoadFailed.value = false;
    },
);
let _refreshTimer: ReturnType<typeof setInterval> | null = null;

watchEffect(() => {
    if (_refreshTimer) {
        clearInterval(_refreshTimer);
        _refreshTimer = null;
    }
    const interval = props.object.graph_refresh_interval ?? 0;
    if (props.object.type === 'graph' && interval > 0) {
        _refreshTimer = setInterval(() => {
            refreshTick.value++;
        }, interval * 1000);
    }
});
onUnmounted(() => {
    if (_refreshTimer) clearInterval(_refreshTimer);
    if (dataTimeoutTimer) clearTimeout(dataTimeoutTimer);
});

const graphSrc = computed(() => {
    const url = props.object.graph_url;
    if (!url) return '';
    if ((props.object.graph_refresh_interval ?? 0) > 0) {
        const sep = url.includes('?') ? '&' : '?';
        return `${url}${sep}_t=${refreshTick.value}`;
    }
    return url;
});

const graphWrapperStyle = computed(() => ({
    width: `${graphW.value}px`,
    height: `${graphH.value}px`,
}));

const svgSize = computed(() => props.iconSize + RING_PAD * 2);

const STATE_RGB: Record<string, string> = {
    UP: 'rgb(34,197,94)',
    OK: 'rgb(34,197,94)',
    DOWN: 'rgb(239,68,68)',
    CRITICAL: 'rgb(239,68,68)',
    UNREACHABLE: 'rgb(249,115,22)',
    UNKNOWN: 'rgb(249,115,22)',
    WARNING: 'rgb(255,208,0)',
    PENDING: 'rgb(113,113,122)',
    NOT_FOUND: 'rgb(113,113,122)',
};
const stateColorRgb = computed(
    () => STATE_RGB[props.state?.state ?? 'PENDING'] ?? STATE_RGB['PENDING'],
);

// Pct from blindly-picked metrics[0]. Used only as a last-resort fallback when
// the perfometer endpoint isn't available — picking the first perfdata field
// is unreliable (e.g. Memory's `mem_lnx_total_used` skews red even at 50% RAM).
const firstMetricPct = computed(() => {
    const metrics = parsePerfData(props.state?.perf_data ?? '');
    return metrics.length ? utilPercent(metrics[0]) : null;
});

// Perfometer-derived ring data: the backend's perfometer logic already picks
// the right metric per check (mem_used_percent for Memory, fs_used_percent for
// Filesystem, …) and applies the proper unit/threshold colouring. We mirror
// that into the icon's utilization ring so state-color and ring-color stay
// semantically aligned.
const cmkPerfPct = ref<number | null>(null);
const cmkPerfColor = ref<string | null>(null);

async function _fetchPerfometerForRing(): Promise<void> {
    if (
        !props.object.host_name ||
        !props.object.service_description ||
        !props.connectionId ||
        !authStore.accessToken ||
        props.state?.state === 'NOT_FOUND' ||
        props.state?.state === 'NO_PERMISSION'
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
        if (!r || !r.rows.length) {
            cmkPerfPct.value = null;
            cmkPerfColor.value = null;
            return;
        }
        // The backend emits a "remainder" segment in zinc-600 (#52525b). The
        // ring should show the *non-remainder* total fill and pick its colour
        // from the dominant non-remainder segment.
        const REMAINDER = '#52525b';
        const segs = r.rows[0].filter((s) => s.color !== REMAINDER);
        const fillPct = segs.reduce((acc, s) => acc + s.pct, 0);
        const dominant = segs.reduce((best, s) => (s.pct > (best?.pct ?? -1) ? s : best), segs[0]);
        cmkPerfPct.value = Math.min(100, Math.max(0, fillPct));
        cmkPerfColor.value = dominant?.color ?? null;
    } catch {
        cmkPerfPct.value = null;
        cmkPerfColor.value = null;
    }
}

onMounted(_fetchPerfometerForRing);
watch(() => props.state?.perf_data, _fetchPerfometerForRing);
watch([() => props.object.host_name, () => props.object.service_description], () => {
    cmkPerfPct.value = null;
    cmkPerfColor.value = null;
    void _fetchPerfometerForRing();
});

const ringPct = computed(() => cmkPerfPct.value ?? firstMetricPct.value);
const ringUtilColor = computed(() => {
    if (cmkPerfColor.value) return cmkPerfColor.value;
    if (firstMetricPct.value !== null) return _utilColor(firstMetricPct.value);
    return stateColorRgb.value;
});

const isSvgIcon = computed(() => {
    const icon = props.object.display?.image ?? props.object.image_src;
    return icon?.toLowerCase().endsWith('.svg') ?? false;
});

const customIconStyle = computed(() => {
    // For type=image the iconSize is the *bound*, not a forced square — let
    // the image render at its natural aspect and just cap the largest side.
    // Otherwise (host/service with custom icon) keep the square slot the
    // state ring expects.
    const base =
        props.object.type === 'image'
            ? {
                  maxWidth: `${props.iconSize}px`,
                  maxHeight: `${props.iconSize}px`,
                  display: 'block',
              }
            : { width: `${props.iconSize}px`, height: `${props.iconSize}px` };
    if (!props.selected) return base;
    const glow = 'drop-shadow(0 0 6px var(--color-corporate-green-50))';
    const filter = isSvgIcon.value && isDark.value ? `invert(1) ${glow}` : glow;
    return { ...base, filter };
});

const shouldShowRing = computed(
    () =>
        !['textbox', 'line', 'host', 'image'].includes(props.object.type) &&
        props.object.display?.mode !== 'gadget' &&
        props.state?.state !== 'NOT_FOUND' &&
        props.state?.state !== 'NO_PERMISSION',
);

useArcRing({
    svgRef: arcSvgEl,
    iconSize: computed(() => props.iconSize),
    pct: ringPct,
    stateColor: stateColorRgb,
    utilColor: ringUtilColor,
    enabled: shouldShowRing,
});

const STATE_GLOWS: Record<string, string> = {
    UP: 'drop-shadow(0 0 5px rgba(34,197,94,0.55))',
    OK: 'drop-shadow(0 0 5px rgba(34,197,94,0.55))',
    DOWN: 'drop-shadow(0 0 6px rgba(239,68,68,0.65))',
    CRITICAL: 'drop-shadow(0 0 6px rgba(239,68,68,0.65))',
    UNREACHABLE: 'drop-shadow(0 0 5px rgba(249,115,22,0.55))',
    UNKNOWN: 'drop-shadow(0 0 5px rgba(249,115,22,0.55))',
    WARNING: 'drop-shadow(0 0 5px rgba(255,208,0,0.55))',
    PENDING: 'none',
};
const stateGlow = computed(() => STATE_GLOWS[props.state?.state ?? 'PENDING'] ?? 'none');

const charFontSize = computed(() => {
    const n = typeChar.value.length;
    const factor = n === 1 ? 0.44 : n === 2 ? 0.31 : 0.26;
    return Math.max(9, Math.round(props.iconSize * factor));
});

const resizableTypes = new Set(['graph', 'textbox']);

const TYPE_CHARS: Record<string, string> = {
    host: 'H',
    service: 'S',
    hostgroup: 'HG',
    servicegroup: 'SG',
    map: 'M',
    image: '◆',
    line: '—',
    aggregation: 'BI',
};
const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?');

const textboxStyle = computed(() => {
    const override = props.resizeOverride;
    const w = override?.width ?? props.object.textbox_width;
    const h = override?.height ?? props.object.textbox_height;
    return {
        backdropFilter: 'blur(4px)',
        background: props.object.textbox_background ?? 'var(--bg-glass)',
        borderColor: props.object.textbox_border ?? undefined,
        color: 'var(--text)',
        width: w ? `${w}px` : undefined,
        height: h ? `${h}px` : undefined,
    };
});

const labelStyle = computed(() => {
    const bg = props.object.label?.background;
    return {
        fontSize: `${props.object.label?.size ?? 11}px`,
        color: props.object.label?.color ?? '#e4e4e7',
        background: bg && bg !== 'transparent' ? bg : 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
        outline: props.object.label_border
            ? `1px solid ${props.object.label_border}`
            : '1px solid rgba(255,255,255,0.12)',
    };
});

const textOnlyStyle = computed(() => {
    const bg = props.object.label?.background;
    const size = props.object.label?.size ?? Math.max(12, Math.round(props.iconSize * 0.4));
    return {
        fontSize: `${size}px`,
        color: props.object.label?.color ?? stateColorRgb.value,
        background: bg && bg !== 'transparent' ? bg : 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        textShadow: '0 1px 3px rgba(0,0,0,0.9)',
        outline: props.object.label_border
            ? `1px solid ${props.object.label_border}`
            : '1px solid rgba(255,255,255,0.12)',
    };
});

const displayName = computed(() => {
    let name = props.object.group_name ?? props.object.id;
    if (props.object.label?.text) name = props.object.label.text;
    else if (props.object.type === 'host') name = props.object.host_name ?? props.object.id;
    else if (props.object.type === 'service')
        name = props.object.service_description ?? props.object.id;
    else if (props.object.type === 'map') name = props.object.map_name ?? props.object.id;
    else if (props.object.type === 'aggregation')
        name = props.object.aggregation_id ?? props.object.id;
    const maxlen = props.object.label_maxlen;
    if (maxlen && maxlen > 0 && name.length > maxlen) return name.slice(0, maxlen) + '…';
    return name;
});
</script>

<style scoped>
@keyframes state-pulse {
    0%,
    100% {
        box-shadow: 0 0 6px 1px rgb(239 68 68 / 50%);
    }

    50% {
        box-shadow: 0 0 18px 4px rgb(239 68 68 / 85%);
    }
}
</style>
