<template>
  <!-- Graph embed / native chart -->
  <div
    v-if="object.type === 'graph'"
    class="orb-obj__graph"
    :style="graphWrapperStyle"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <!-- No permission: render silent empty box -->
    <div v-if="state?.state === 'NO_PERMISSION'" class="orb-obj__graph-empty" />

    <!-- Native chart mode (host linked) -->
    <template v-else-if="isNativeChart">
      <!-- Waiting for first data point / not found -->
      <div
        v-if="!hasChartData"
        class="orb-obj__graph-waiting"
        :class="editMode ? 'orb-obj__graph-waiting--edit' : ''"
      >
        <svg
          class="orb-obj__graph-glyph"
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
        <span v-if="dataTimedOut" class="orb-obj__graph-hint orb-obj__graph-hint--padded">{{
          _t('No data for "%{service}" on %{host}', {
            service: object.service_description || object.host_name || '',
            host: object.host_name ?? ''
          })
        }}</span>
        <span v-else class="orb-obj__graph-hint">{{ _t('Waiting for data…') }}</span>
      </div>
      <!-- D3 chart -->
      <div v-else class="orb-obj__chart" style="padding: 6px 8px 5px">
        <!-- Header: metric label + current value -->
        <div class="orb-obj__chart-head">
          <span class="orb-obj__chart-title">
            {{
              isSingleMetric ? chartMetricLabels[0] || object.graph_metric?.[0] : chartHeaderName
            }}
          </span>
          <span
            v-if="isSingleMetric"
            class="orb-obj__chart-value"
            :style="{ color: singleMetricColor }"
            >{{ singleMetricValueStr }}</span
          >
          <span v-else class="orb-obj__chart-live">live</span>
        </div>
        <!-- Multi-metric legend -->
        <div v-if="!isSingleMetric" class="orb-obj__chart-legend">
          <div
            v-for="(label, idx) in chartMetricLabels.slice(0, MAX_VISIBLE_SERIES)"
            :key="label"
            class="orb-obj__legend-item"
            style="max-width: 50%"
          >
            <span
              class="orb-obj__legend-swatch"
              :style="{ background: CHART_PALETTE[idx % CHART_PALETTE.length] }"
            />
            <span class="orb-obj__legend-label">{{ label }}</span>
            <span
              class="orb-obj__legend-value"
              :style="{ color: CHART_PALETTE[idx % CHART_PALETTE.length] }"
              >{{ legendValue(idx) }}</span
            >
          </div>
          <span
            v-if="chartMetricLabels.length > MAX_VISIBLE_SERIES"
            class="orb-obj__legend-more"
            :title="hiddenMetricLabels"
            >+{{ chartMetricLabels.length - MAX_VISIBLE_SERIES }}</span
          >
        </div>
        <div class="orb-obj__chart-body">
          <template v-for="group in chartGroups" :key="group.id">
            <MetricChart
              class="orb-obj__chart-canvas"
              :data="group.data"
              :metric-keys="Object.keys(group.data)"
              :mirrored-keys="group.mirrored"
              :unit-map="chartMetricUnits"
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
      <!-- Placeholder: no URL, unembeddable scheme, or load error -->
      <div v-if="!embeddableGraphUrl || graphLoadFailed" class="orb-obj__graph-placeholder">
        <svg
          class="orb-obj__graph-glyph"
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
        <span class="orb-obj__graph-hint">{{
          object.graph_url ? _t('Load failed') : _t('No URL configured')
        }}</span>
      </div>
      <!-- img embed -->
      <img
        v-else-if="object.graph_embed_type !== 'iframe'"
        :src="graphSrc"
        class="orb-obj__graph-img"
        draggable="false"
        @error="graphLoadFailed = true"
        @load="graphLoadFailed = false"
      />
      <!-- iframe embed. No allow-same-origin: combined with allow-scripts it
           would void the sandbox entirely for same-origin content — graphs
           only need to render and run their own scripts, never to reach our
           origin (cookies, sessionStorage tokens, parent DOM). -->
      <iframe
        v-else
        :src="embeddableGraphUrl"
        class="orb-obj__graph-iframe"
        sandbox="allow-scripts"
      />
    </template>
    <!-- Optional caption label -->
    <div
      v-if="object.label?.show && object.label?.text && state?.state !== 'NO_PERMISSION'"
      class="orb-obj__graph-caption"
      :style="labelStyle"
    >
      {{ object.label.text }}
    </div>
    <!-- Resize handle (edit mode only) -->
    <div
      v-if="editMode && resizableTypes.has(object.type)"
      class="orb-obj__resize-handle"
      title="Resize"
      @pointerdown.stop="$emit('graph-resize-start', $event)"
    >
      <svg
        class="orb-obj__resize-icon"
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
    <div v-if="selected" class="orb-obj__graph-selection" />
  </div>

  <!-- Textbox -->
  <div
    v-else-if="object.type === 'textbox'"
    class="orb-obj__textbox"
    :class="[
      isNagvisClassic ? 'orb-obj__textbox--classic' : 'orb-obj__textbox--boxed',
      !isNagvisClassic && !object.textbox_border
        ? selected
          ? 'orb-obj__textbox--ring-selected'
          : 'orb-obj__textbox--ring'
        : ''
    ]"
    :style="textboxStyle"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    {{ textboxText }}
    <div
      v-if="editMode && resizableTypes.has(object.type)"
      class="orb-obj__resize-handle"
      title="Resize"
      @pointerdown.stop="$emit('graph-resize-start', $event)"
    >
      <svg
        class="orb-obj__resize-icon"
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
  </div>

  <!-- Gadget -->
  <div
    v-else-if="object.display?.mode === 'gadget'"
    class="orb-obj__stack"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <div :class="selected ? 'orb-obj__gadget-frame--selected' : ''">
      <GadgetRenderer
        :type="effectiveGadgetType"
        :metric="object.display?.gadget_metric ?? null"
        :state="state"
        :size="iconSize"
        :perfometer="gadgetPerfometer"
        :metric-units="gadgetMetricUnits"
      />
    </div>
    <div
      v-if="object.label?.show && state?.state !== 'NO_PERMISSION'"
      class="orb-obj__gadget-label"
      :style="labelStyle"
    >
      {{ displayName }}
    </div>
  </div>

  <!-- Text-only: object name rendered as state-coloured text, no icon. -->
  <div
    v-else-if="object.display?.mode === 'text'"
    class="orb-obj__stack"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <div
      class="orb-obj__text-pill"
      :class="selected ? 'orb-obj__text-pill--selected' : ''"
      :style="textOnlyStyle"
    >
      {{ displayName }}
    </div>
  </div>

  <!-- All other types: icon circle (or custom image) + label -->
  <div
    v-else
    class="orb-obj__stack"
    :class="isNagvisClassic ? 'orb-obj__stack--classic' : ''"
    :style="iconWrapperStyle"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <!-- Icon with arc ring overlay + badges -->
    <div class="orb-obj__icon-box">
      <!-- Custom icon image — draggable="false" prevents the browser from starting
           an HTML5 drag operation which would swallow all subsequent mousemove events -->
      <img
        v-if="(object.display?.image ?? object.image_src) && !imgLoadFailed"
        :src="`${BASE_URL}images/${object.display?.image ?? object.image_src}`"
        :style="customIconStyle"
        draggable="false"
        class="orb-obj__icon-img"
        @error="imgLoadFailed = true"
      />
      <!-- Asset-missing placeholder: broken-image glyph so importer
                 misses are visually obvious without dragging the user into the
                 filename string. -->
      <div
        v-else-if="object.type === 'image' && imgLoadFailed && isNagvisClassic"
        class="orb-obj__broken"
        :style="{
          width: `${object.display?.image_size ?? iconSize ?? 60}px`,
          height: `${object.display?.image_size ?? iconSize ?? 60}px`,
          border: '1px dashed #b45309',
          background: 'rgba(254, 243, 199, 0.85)',
          color: '#b45309',
          borderRadius: '2px'
        }"
        :title="`Asset missing: ${object.image_src ?? object.display?.image ?? ''}`"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          :style="{
            width: `${Math.min(Math.round((object.display?.image_size ?? iconSize ?? 60) * 0.55), 32)}px`,
            height: `${Math.min(Math.round((object.display?.image_size ?? iconSize ?? 60) * 0.55), 32)}px`
          }"
        >
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M3 17l6-6 4 4 4-4 4 4" />
          <line x1="3" y1="3" x2="21" y2="21" />
        </svg>
      </div>
      <!-- State circle fallback — SVG for crisp sub-pixel text centering -->
      <!-- Not shown for type=image: if the image fails, the object simply becomes invisible -->
      <svg
        v-else-if="object.type !== 'image' || !imgLoadFailed"
        :width="iconSize"
        :height="iconSize"
        :viewBox="`0 0 ${iconSize} ${iconSize}`"
        overflow="visible"
        class="orb-obj__state-svg"
        :class="selected ? 'orb-obj__state-svg--selected' : ''"
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
        class="orb-obj__arc"
        :style="{ top: `-${RING_PAD}px`, left: `-${RING_PAD}px`, pointerEvents: 'none' }"
        :title="_t('Utilization ring (first metric)')"
      />

      <!-- Stale data badge -->
      <span
        v-if="state?.stale && !isNagvisClassic"
        class="orb-obj__badge orb-obj__badge--stale"
        title="Stale data"
      >
        <svg
          class="orb-obj__badge-icon"
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
        v-if="state?.acknowledged && !isNagvisClassic"
        class="orb-obj__badge orb-obj__badge--ack"
        title="Acknowledged"
      >
        <svg
          class="orb-obj__badge-icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="3.5"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </span>
      <!-- Downtime badge -->
      <span
        v-if="state?.in_downtime && !isNagvisClassic"
        class="orb-obj__badge orb-obj__badge--downtime"
        title="In downtime"
      >
        <svg class="orb-obj__badge-icon" fill="currentColor" viewBox="0 0 24 24">
          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
        </svg>
      </span>
      <!-- BI aggregation: expanded subtree (when expand_depth > 0) -->
      <AggregationSubtree
        v-if="object.type === 'aggregation' && (object.expand_depth ?? 0) > 0 && state?.tree"
        :tree="state.tree"
        :max-depth="object.expand_depth ?? 0"
        :icon-size="iconSize"
        :line-color="object.line_color ?? null"
        :line-width="object.line_width ?? null"
        @node-enter="(o, s, e) => $emit('subtree-enter', o, s, e)"
        @node-leave="$emit('subtree-leave')"
      />
    </div>
    <!-- Label -->
    <div
      v-if="object.label?.show && state?.state !== 'NO_PERMISSION'"
      class="orb-obj__label"
      :class="isNagvisClassic ? '' : 'orb-obj__label--boxed'"
      :style="labelStyle"
    >
      {{ displayName }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, watchEffect } from 'vue'

import { metricsApi } from '@/api/client'
import { useArcRing } from '@/composables/useArcRing'
import { CHART_PALETTE, MAX_VISIBLE_SERIES } from '@/composables/useMetricChart'
import { useMetricUnits } from '@/composables/useMetricUnits'
import { usePerfometer } from '@/composables/usePerfometer'
import { useIsDark } from '@/composables/useTheme'
import { useAuthStore } from '@/stores/auth'
import type { MetricPoint } from '@/stores/states'
import { useStatesStore } from '@/stores/states'
import type { BoardObject, ObjectState } from '@/types/api'
import { renderMetricValue } from '@/utils/metricFormat'
import { utilColor as _utilColor, getMetric, parsePerfData, utilPercent } from '@/utils/perf'
import usei18n from '@/vendor/cmk/lib/i18n'

import AggregationSubtree from './AggregationSubtree.vue'
import GadgetRenderer from './GadgetRenderer.vue'
import MetricChart from './MetricChart.vue'

const BASE_URL = import.meta.env.BASE_URL
const RING_PAD = 6

const { _t } = usei18n()

const props = defineProps<{
  object: BoardObject
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
  editMode?: boolean
  resizeOverride?: { width: number; height: number } | undefined
  connectionId?: string
  renderMode?: 'default' | 'nagvis_classic'
}>()

const isNagvisClassic = computed(() => props.renderMode === 'nagvis_classic')

defineEmits<{
  hover: [event: MouseEvent]
  'hover-leave': []
  'context-menu': [event: MouseEvent]
  'graph-resize-start': [evt: PointerEvent]
  'subtree-enter': [obj: BoardObject, state: ObjectState, event: MouseEvent]
  'subtree-leave': []
}>()

const statesStore = useStatesStore()
const authStore = useAuthStore()

// Group/BI objects have a state but no perf metrics — a gauge or bar would
// permanently render "—", so they fall back to the state light.
const effectiveGadgetType = computed(() => {
  const gt = props.object.display?.gadget_type || 'gauge'
  return ['hostgroup', 'servicegroup', 'dyngroup', 'aggregation'].includes(props.object.type)
    ? 'trafficlight'
    : gt
})

// CMK perfometer behind gauge/bar gadgets — fills the dial when the raw
// perf_data has no max and supplies the CMK-formatted caption.
const gadgetBinding = {
  connectionId: () => props.connectionId,
  hostName: () => props.object.host_name,
  serviceDescription: () => props.object.service_description,
  perfData: () => props.state?.perf_data,
  enabled: () =>
    props.object.display?.mode === 'gadget' &&
    ['gauge', 'bar'].includes(props.object.display?.gadget_type || 'gauge')
}
const gadgetPerfometer = usePerfometer(gadgetBinding)
// Registered display units so the readout matches the Checkmk GUI. The raw
// value gadget needs these too, but no perfometer (it has no fill to scale).
const gadgetMetricUnits = useMetricUnits({
  ...gadgetBinding,
  enabled: () =>
    props.object.display?.mode === 'gadget' &&
    (props.object.display?.gadget_type || 'gauge') !== 'trafficlight'
})

const GRAPH_DATA_TIMEOUT_MS = 15_000
const dataTimedOut = ref(false)
let dataTimeoutTimer: ReturnType<typeof setTimeout> | null = null

function _triggerHistoryPrefill() {
  if (
    props.object.type !== 'graph' ||
    !props.object.host_name ||
    !props.connectionId ||
    !authStore.accessToken
  )
    return
  dataTimedOut.value = false
  if (dataTimeoutTimer) clearTimeout(dataTimeoutTimer)
  dataTimeoutTimer = setTimeout(() => {
    if (!hasChartData.value) dataTimedOut.value = true
  }, GRAPH_DATA_TIMEOUT_MS)
  const windowMins = props.object.graph_time_window ?? 60
  statesStore.prefillMetricHistory(
    props.object.id,
    props.connectionId,
    props.object.host_name,
    props.object.service_description ?? null,
    windowMins,
    authStore.accessToken!
  )
}

onMounted(_triggerHistoryPrefill)
watch(() => props.object.graph_time_window, _triggerHistoryPrefill)
// Clear stale metric data and re-fetch when host or service changes
watch([() => props.object.host_name, () => props.object.service_description], () => {
  statesStore.clearMetricValues(props.object.id)
  _triggerHistoryPrefill()
})
// Re-trigger when token becomes available (e.g. after async SSO login)
watch(
  () => authStore.accessToken,
  (token, prev) => {
    if (token && !prev) _triggerHistoryPrefill()
  }
)

const isDark = useIsDark()

// Single arc ring SVG — always a separate overlay SVG that D3 owns exclusively.
// pointer-events="none" on the SVG element (SVG attribute, not CSS) ensures it
// never intercepts mousedown/click events, preserving drag behaviour in edit mode.
const arcSvgEl = ref<SVGSVGElement | null>(null)
const imgLoadFailed = ref(false)

// ---- Graph: native chart mode ----
const isNativeChart = computed(() => props.object.type === 'graph' && !!props.object.host_name)

const chartMetricUnits = useMetricUnits({ ...gadgetBinding, enabled: () => isNativeChart.value })

const chartData = computed((): Record<string, MetricPoint[]> => {
  if (!isNativeChart.value) return {}
  const mv = statesStore.metricValues[props.object.id]
  if (!mv) return {}

  const windowMins = props.object.graph_time_window ?? 60
  const windowSecs = windowMins * 60
  const now = Date.now() / 1000
  const cutoff = now - windowSecs

  const applyWindow = (pts: MetricPoint[]): MetricPoint[] => {
    const filtered = pts.filter((p) => p.ts >= cutoff)
    if (filtered.length) return [...filtered]
    // If nothing falls in the window yet, show last point as baseline
    const last = pts.at(-1)
    return last ? [last] : []
  }

  const pick = (keys: string[]): Record<string, MetricPoint[]> => {
    const out: Record<string, MetricPoint[]> = {}
    for (const k of keys) {
      const pts = mv[k]
      if (pts) out[k] = applyWindow(pts)
    }
    return out
  }

  if (props.object.graph_metric?.length) {
    return pick(props.object.graph_metric)
  }
  const graphId = props.object.graph_id
  if (graphId) {
    const group = (statesStore.metricGraphs[props.object.id] ?? []).find((g) => g.id === graphId)
    if (group) {
      return pick(group.metrics)
    }
  }
  return Object.fromEntries(Object.entries(mv).map(([k, v]) => [k, applyWindow(v)]))
})

// Raw metric IDs as they appear in chartData (used for data access)
const chartMetricKeys = computed(() => Object.keys(chartData.value))
// Display labels: human-readable titles when available, raw ID as fallback
const chartMetricLabels = computed(() =>
  chartMetricKeys.value.map((key) => statesStore.metricTitles[props.object.id]?.[key] ?? key)
)
const chartHeaderName = computed(() => {
  const o = props.object
  // Prefer the graph template group title (e.g. "RAM (Total, cached, buffers)") over host/service
  // when exactly one group is shown — mirrors how CMK labels its graphs.
  const g = chartGroups.value
  const only = g.length === 1 ? g[0] : undefined
  if (only?.title) return only.title
  if (o.host_name && o.service_description) return `${o.host_name} / ${o.service_description}`
  return o.service_description ?? o.host_name ?? ''
})
const hiddenMetricLabels = computed(() =>
  chartMetricLabels.value.slice(MAX_VISIBLE_SERIES).join(', ')
)
const hasChartData = computed(() => Object.values(chartData.value).some((pts) => pts.length > 0))

const graphW = computed(() => props.resizeOverride?.width ?? props.object.graph_width ?? 400)
const graphH = computed(() => props.resizeOverride?.height ?? props.object.graph_height ?? 200)

const chartThresholds = computed(() => {
  if (!isNativeChart.value) return null
  const ms = parsePerfData(props.state?.perf_data ?? '')
  const m = getMetric(ms, props.object.graph_metric?.[0])
  return m ? { warn: m.warn, crit: m.crit } : null
})

const isSingleMetric = computed(() => chartMetricLabels.value.length === 1)

// Latest reading for the legend, formatted through Checkmk's unit registry.
function legendValue(idx: number): string {
  const key = chartMetricKeys.value[idx]
  const pt = key ? chartData.value[key]?.at(-1) : undefined
  if (!key || !pt) return ''
  return renderMetricValue(pt.value, chartMetricUnits.value[key], pt.unit)
}

const singleMetricValueStr = computed(() => {
  if (!isSingleMetric.value) return ''
  return legendValue(0)
})

const singleMetricColor = computed(() => {
  const ms = parsePerfData(props.state?.perf_data ?? '')
  const label = props.object.graph_metric?.[0] || chartMetricKeys.value[0]
  const m = getMetric(ms, label)
  if (!m) return CHART_PALETTE[0]
  return _utilColor(utilPercent(m))
})

const chartGroups = computed(() => {
  const groups = statesStore.metricGraphs[props.object.id] ?? []
  // graph_metric and graph_id filtering is already applied in chartData.
  // If no template groups, render chartData as a single ungrouped chart.
  if (!groups.length || props.object.graph_id || props.object.graph_metric?.length) {
    const pinned = props.object.graph_id ? groups.find((g) => g.id === props.object.graph_id) : null
    return [{ id: '_all', title: '', data: chartData.value, mirrored: pinned?.mirrored ?? [] }]
  }
  // When multiple graph template groups exist but no specific group is pinned via
  // graph_id, show only the first group that has data. Showing all groups at once
  // squishes them into unreadably small sub-charts. Users can pin a group via graph_id.
  for (const g of groups) {
    const data: Record<string, MetricPoint[]> = {}
    for (const m of g.metrics) {
      const pts = chartData.value[m]
      if (pts) data[m] = pts
    }
    if (Object.keys(data).length > 0) {
      return [{ id: g.id, title: g.title, data, mirrored: g.mirrored ?? [] }]
    }
  }
  return [{ id: '_all', title: '', data: chartData.value, mirrored: [] }]
})

// ---- Graph: URL embed ----
const graphLoadFailed = ref(false)
const refreshTick = ref(0)

watch(
  () => props.object.graph_url,
  () => {
    graphLoadFailed.value = false
  }
)
let _refreshTimer: ReturnType<typeof setInterval> | null = null

watchEffect(() => {
  if (_refreshTimer) {
    clearInterval(_refreshTimer)
    _refreshTimer = null
  }
  const interval = props.object.graph_refresh_interval ?? 0
  if (props.object.type === 'graph' && interval > 0) {
    _refreshTimer = setInterval(() => {
      refreshTick.value++
    }, interval * 1000)
  }
})
onUnmounted(() => {
  if (_refreshTimer) clearInterval(_refreshTimer)
  if (dataTimeoutTimer) clearTimeout(dataTimeoutTimer)
})

// Render-sink guard: board JSON predating the server-side scheme allowlist
// may still carry hostile URLs — only ever embed http(s) content (relative
// URLs resolve to the page origin and pass).
const embeddableGraphUrl = computed(() => {
  const url = props.object.graph_url
  if (!url) return ''
  try {
    const protocol = new URL(url, window.location.href).protocol
    return protocol === 'http:' || protocol === 'https:' ? url : ''
  } catch {
    return ''
  }
})

const graphSrc = computed(() => {
  const url = embeddableGraphUrl.value
  if (!url) return ''
  if ((props.object.graph_refresh_interval ?? 0) > 0) {
    const sep = url.includes('?') ? '&' : '?'
    return `${url}${sep}_t=${refreshTick.value}`
  }
  return url
})

const graphWrapperStyle = computed(() => ({
  width: `${graphW.value}px`,
  height: `${graphH.value}px`
}))

const svgSize = computed(() => props.iconSize + RING_PAD * 2)

const PENDING_RGB = 'rgb(113,113,122)'
const STATE_RGB: Record<string, string> = {
  UP: 'rgb(34,197,94)',
  OK: 'rgb(34,197,94)',
  DOWN: 'rgb(239,68,68)',
  CRITICAL: 'rgb(239,68,68)',
  UNREACHABLE: 'rgb(249,115,22)',
  UNKNOWN: 'rgb(249,115,22)',
  WARNING: 'rgb(255,208,0)',
  PENDING: PENDING_RGB,
  NOT_FOUND: PENDING_RGB
}
const stateColorRgb = computed(() => STATE_RGB[props.state?.state ?? 'PENDING'] ?? PENDING_RGB)

// Pct from blindly-picked metrics[0]. Used only as a last-resort fallback when
// the perfometer endpoint isn't available — picking the first perfdata field
// is unreliable (e.g. Memory's `mem_lnx_total_used` skews red even at 50% RAM).
const firstMetricPct = computed(() => {
  const first = parsePerfData(props.state?.perf_data ?? '')[0]
  return first ? utilPercent(first) : null
})

// Perfometer-derived ring data: the backend's perfometer logic already picks
// the right metric per check (mem_used_percent for Memory, fs_used_percent for
// Filesystem, …) and applies the proper unit/threshold colouring. We mirror
// that into the icon's utilization ring so state-color and ring-color stay
// semantically aligned.
const cmkPerfPct = ref<number | null>(null)
const cmkPerfColor = ref<string | null>(null)

async function _fetchPerfometerForRing(): Promise<void> {
  if (
    !props.object.host_name ||
    !props.object.service_description ||
    !props.connectionId ||
    !authStore.accessToken ||
    props.state?.state === 'NOT_FOUND' ||
    props.state?.state === 'NO_PERMISSION'
  ) {
    return
  }
  try {
    const r = await metricsApi.getPerfometer(
      props.connectionId,
      props.object.host_name,
      props.object.service_description,
      authStore.accessToken
    )
    const row = r?.rows[0]
    if (!row) {
      cmkPerfPct.value = null
      cmkPerfColor.value = null
      return
    }
    // The backend emits a "remainder" segment in zinc-600 (#52525b). The
    // ring should show the *non-remainder* total fill and pick its colour
    // from the dominant non-remainder segment.
    const REMAINDER = '#52525b'
    const segs = row.filter((s) => s.color !== REMAINDER)
    const fillPct = segs.reduce((acc, s) => acc + s.pct, 0)
    const dominant = segs.reduce((best, s) => (s.pct > (best?.pct ?? -1) ? s : best), segs[0])
    cmkPerfPct.value = Math.min(100, Math.max(0, fillPct))
    cmkPerfColor.value = dominant?.color ?? null
  } catch {
    cmkPerfPct.value = null
    cmkPerfColor.value = null
  }
}

onMounted(_fetchPerfometerForRing)
watch(() => props.state?.perf_data, _fetchPerfometerForRing)
watch([() => props.object.host_name, () => props.object.service_description], () => {
  cmkPerfPct.value = null
  cmkPerfColor.value = null
  void _fetchPerfometerForRing()
})

const ringPct = computed(() => cmkPerfPct.value ?? firstMetricPct.value)
const ringUtilColor = computed(() => {
  if (cmkPerfColor.value) return cmkPerfColor.value
  if (firstMetricPct.value !== null) return _utilColor(firstMetricPct.value)
  return stateColorRgb.value
})

const customIconStyle = computed(() => {
  // For type=image the iconSize is the *bound*, not a forced square — let
  // the image render at its natural aspect and just cap the largest side.
  // Otherwise (host/service with custom icon) keep the square slot the
  // state ring expects.
  const base: Record<string, string> =
    props.object.type === 'image'
      ? {
          maxWidth: `${props.iconSize}px`,
          maxHeight: `${props.iconSize}px`,
          display: 'block'
        }
      : { width: `${props.iconSize}px`, height: `${props.iconSize}px` }
  const sel = props.selected ? ' drop-shadow(0 0 6px var(--color-corporate-green-50))' : ''
  const style: Record<string, string> = { ...base, filter: `var(--icon-halo)${sel}` }
  // A custom icon on a host/service conveys its state with a solid coloured ring
  // + soft glow + faint tint, so the status reads clearly on any board background
  // (a bare drop-shadow glow was too easy to miss). A raster <img> can't itself be
  // recoloured, and pure image objects carry no status.
  if (props.object.type !== 'image' && stateGlow.value !== 'none') {
    const c = stateColorRgb.value
    style.boxShadow = `0 0 0 2.5px ${c}, 0 0 7px 1px ${c}`
    style.background = c.replace('rgb(', 'rgba(').replace(')', ', 0.18)')
    style.borderRadius = '5px'
  }
  return style
})

const shouldShowRing = computed(
  () =>
    !isNagvisClassic.value &&
    !['textbox', 'line', 'host', 'image'].includes(props.object.type) &&
    props.object.display?.mode !== 'gadget' &&
    props.state?.state !== 'NOT_FOUND' &&
    props.state?.state !== 'NO_PERMISSION'
)

useArcRing({
  svgRef: arcSvgEl,
  iconSize: computed(() => props.iconSize),
  pct: ringPct,
  stateColor: stateColorRgb,
  utilColor: ringUtilColor,
  enabled: shouldShowRing
})

const STATE_GLOWS: Record<string, string> = {
  UP: 'drop-shadow(0 0 5px rgba(34,197,94,0.55))',
  OK: 'drop-shadow(0 0 5px rgba(34,197,94,0.55))',
  DOWN: 'drop-shadow(0 0 6px rgba(239,68,68,0.65))',
  CRITICAL: 'drop-shadow(0 0 6px rgba(239,68,68,0.65))',
  UNREACHABLE: 'drop-shadow(0 0 5px rgba(249,115,22,0.55))',
  UNKNOWN: 'drop-shadow(0 0 5px rgba(249,115,22,0.55))',
  WARNING: 'drop-shadow(0 0 5px rgba(255,208,0,0.55))',
  PENDING: 'none'
}
const stateGlow = computed(() => STATE_GLOWS[props.state?.state ?? 'PENDING'] ?? 'none')

const charFontSize = computed(() => {
  const n = typeChar.value.length
  const factor = n === 1 ? 0.44 : n === 2 ? 0.31 : 0.26
  return Math.max(9, Math.round(props.iconSize * factor))
})

const resizableTypes = new Set(['graph', 'textbox'])

const TYPE_CHARS: Record<string, string> = {
  host: 'H',
  service: 'S',
  hostgroup: 'HG',
  servicegroup: 'SG',
  dyngroup: 'DG',
  map: 'M',
  image: '◆',
  line: '—',
  aggregation: 'BI'
}
const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?')

// [worker_last_run] is a legacy NagVis macro for the timestamp of the last
// monitoring fetch; resolve it from the live state-update time.
const textboxText = computed(() => {
  const raw = props.object.label?.text || 'Text'
  if (!raw.includes('[worker_last_run]')) return raw
  const ts = statesStore.lastUpdate
  const stamp = ts ? new Date(ts * 1000).toLocaleString('sv-SE').replace('T', ' ') : '—'
  return raw.replaceAll('[worker_last_run]', stamp)
})

const textboxStyle = computed(() => {
  const override = props.resizeOverride
  const w = override?.width ?? props.object.textbox_width
  const h = override?.height ?? props.object.textbox_height
  const border = props.object.textbox_border
  const bg = props.object.textbox_background
  const label = props.object.label
  const hasCustomBg = bg && bg !== 'transparent'
  const classic = isNagvisClassic.value
  // Default LabelConfig.color is "#ffffff" — only honour the imported color
  // when the user picked something else, so OrbVis-native boxes stay on the
  // themed text-color over the glass background.
  const customColor =
    label?.color && label.color !== '#ffffff' && label.color !== '#FFFFFF' ? label.color : null
  return {
    // Blur turns an opaque imported background into a frosted smear.
    backdropFilter: classic ? 'none' : hasCustomBg ? undefined : 'blur(4px)',
    background: bg ?? (classic ? 'transparent' : 'var(--bg-glass)'),
    // borderColor alone won't paint without width+style.
    border: border ? `1px solid ${border}` : undefined,
    borderRadius: classic ? '0' : undefined,
    // Classic mirrors NagVis' .box: content-box sizing + 2px side padding +
    // natural line-height, so the text fills the box and sits as centered
    // as it does in NagVis instead of being pushed down by a tall leading.
    boxSizing: classic ? ('content-box' as const) : undefined,
    padding: classic ? '0 2px' : undefined,
    lineHeight: classic ? 'normal' : undefined,
    color: customColor ?? (classic ? '#000000' : 'var(--text)'),
    fontSize: label?.size ? `${label.size}px` : undefined,
    fontWeight: label?.weight ?? undefined,
    textAlign: label?.align ?? undefined,
    width: w ? `${w}px` : undefined,
    height: h ? `${h}px` : undefined
  }
})

const iconWrapperStyle = computed(() => {
  if (!isNagvisClassic.value) return undefined
  // Clamp width to the icon so a wider label can't shift the icon right via
  // flex items-center expansion — NagVis pins the icon's top-left to (x,y).
  const size = props.object.display?.image_size ?? props.iconSize ?? 60
  return { width: `${size}px` }
})

const labelTransform = computed(() => {
  const x = props.object.label?.x ?? 0
  const y = props.object.label?.y ?? 0
  return x || y ? `translate(${x}px, ${y}px)` : undefined
})

const labelStyle = computed(() => {
  const bg = props.object.label?.background
  const width = props.object.label?.width
  const classic = isNagvisClassic.value
  const hasExplicitBg = bg && bg !== 'transparent'
  const lx = props.object.label?.x ?? 0
  const ly = props.object.label?.y ?? 0
  // Classic anchors the label absolutely at (object_x + label_x,
  // object_y + label_y) — NagVis treats label_y as the absolute Y offset,
  // not as a delta on top of an already-stacked flex layout.
  const position = classic
    ? {
        position: 'absolute' as const,
        left: '50%',
        top: `${ly}px`,
        transform: `translateX(calc(-50% + ${lx}px))`
      }
    : { transform: labelTransform.value }
  // Classic mirrors NagVis' .box border (matches the actual element border,
  // so the rendered line lines up with NagVis pixel-for-pixel); default mode
  // uses outline to avoid bumping the flex layout it lives inside.
  const borderStyles = props.object.label_border
    ? classic
      ? { border: `1px solid ${props.object.label_border}`, padding: '0 2px' }
      : { outline: `1px solid ${props.object.label_border}` }
    : classic
      ? {}
      : { outline: '1px solid rgba(255,255,255,0.12)' }
  return {
    fontSize: `${props.object.label?.size ?? 11}px`,
    // Classic tightens line-height to NagVis' span box so the label keeps
    // the same height and doesn't overhang its container.
    lineHeight: classic ? '1.2' : undefined,
    color: props.object.label?.color ?? (classic ? '#000000' : '#e4e4e7'),
    background: hasExplicitBg ? bg : classic ? 'transparent' : 'rgba(0,0,0,0.65)',
    backdropFilter: classic ? 'none' : 'blur(4px)',
    textShadow: classic ? 'none' : '0 1px 3px rgba(0,0,0,0.9)',
    ...borderStyles,
    ...position,
    // NagVis label_width clamps width but only wraps on whitespace — single
    // tokens like "SW01" overflow rather than splitting mid-word.
    width: width ? `${width}px` : undefined,
    whiteSpace: width ? (classic ? 'nowrap' : 'normal') : undefined,
    wordBreak: width && !classic ? ('break-word' as const) : undefined
  }
})

const textOnlyStyle = computed(() => {
  const bg = props.object.label?.background
  const size = props.object.label?.size ?? Math.max(12, Math.round(props.iconSize * 0.4))
  return {
    fontSize: `${size}px`,
    color: props.object.label?.color ?? stateColorRgb.value,
    background: bg && bg !== 'transparent' ? bg : 'rgba(0,0,0,0.65)',
    backdropFilter: 'blur(4px)',
    textShadow: '0 1px 3px rgba(0,0,0,0.9)',
    outline: props.object.label_border
      ? `1px solid ${props.object.label_border}`
      : '1px solid rgba(255,255,255,0.12)',
    transform: labelTransform.value
  }
})

const displayName = computed(() => {
  let name = props.object.group_name ?? props.object.id
  if (props.object.label?.text) name = props.object.label.text
  else if (props.object.type === 'host') name = props.object.host_name ?? props.object.id
  else if (props.object.type === 'service')
    name = props.object.service_description ?? props.object.id
  else if (props.object.type === 'map') name = props.object.map_name ?? props.object.id
  else if (props.object.type === 'aggregation')
    name = props.object.aggregation_id ?? props.object.id
  else if (props.object.type === 'dyngroup') name = props.object.id
  const maxlen = props.object.label_maxlen
  if (maxlen && maxlen > 0 && name.length > maxlen) return name.slice(0, maxlen) + '…'
  return name
})
</script>

<style scoped>
.orb-obj__graph {
  position: relative;
  user-select: none;
}

.orb-obj__graph-empty {
  width: 100%;
  height: 100%;
  background: color-mix(in srgb, var(--bg) 20%, transparent);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.orb-obj__graph-waiting {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 100%;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.orb-obj__graph-waiting--edit {
  border: 2px dashed var(--border);
}

.orb-obj__graph-glyph {
  width: var(--dimension-8);
  height: var(--dimension-8);
}

.orb-obj__graph-hint {
  font-size: var(--font-size-normal);
  line-height: 16px;
}

.orb-obj__graph-hint--padded {
  padding: 0 var(--dimension-5);
  text-align: center;
}

.orb-obj__chart {
  display: flex;
  overflow: hidden;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
}

.orb-obj__chart-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  margin-bottom: var(--dimension-3);
}

.orb-obj__chart-title {
  overflow: hidden;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.025em;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-obj__chart-value {
  flex-shrink: 0;
  margin-left: var(--dimension-3);
  font-size: 10px;
  font-weight: 700;
}

.orb-obj__chart-live {
  flex-shrink: 0;
  margin-left: var(--dimension-3);
  font-size: 9px;
  letter-spacing: 0.025em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.orb-obj__chart-legend {
  display: flex;
  flex-wrap: wrap;
  flex-shrink: 0;
  gap: var(--dimension-2) 10px;
  margin-bottom: var(--dimension-3);
}

.orb-obj__legend-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  min-width: 0;
}

.orb-obj__legend-swatch {
  display: inline-block;
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 9999px;
}

.orb-obj__legend-label {
  overflow: hidden;
  font-size: 9px;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-obj__legend-value {
  flex-shrink: 0;
  font-size: 9px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.orb-obj__legend-more {
  align-self: center;
  font-size: 9px;
  color: var(--text-muted);
  cursor: default;
}

.orb-obj__chart-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  width: 100%;
  min-height: 0;
}

.orb-obj__chart-canvas {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.orb-obj__graph-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  height: 100%;
  color: var(--text-muted);
  border: 2px dashed var(--border);
  border-radius: 8px;
}

.orb-obj__graph-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
  border-radius: 8px;
}

.orb-obj__graph-iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 8px;
}

.orb-obj__graph-caption {
  position: absolute;
  right: 0;
  bottom: -20px;
  left: 0;
  padding: var(--dimension-2) 6px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  text-align: center;
  border-radius: 4px;
  pointer-events: none;
}

.orb-obj__resize-handle {
  position: absolute;
  right: 0;
  bottom: 0;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-7);
  height: var(--dimension-7);
  background: color-mix(in srgb, var(--color-corporate-green-50) 70%, transparent);
  border-top-left-radius: 4px;
  cursor: se-resize;
  transition: background-color 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-obj__resize-handle:hover {
  background: var(--color-corporate-green-50);
}

.orb-obj__resize-icon {
  width: var(--dimension-5);
  height: var(--dimension-5);
  color: white;
}

.orb-obj__graph-selection {
  position: absolute;
  inset: 0;
  border-radius: 8px;
  box-shadow:
    0 0 0 1px var(--bg),
    0 0 0 3px var(--color-corporate-green-50);
  pointer-events: none;
}

.orb-obj__textbox {
  position: relative;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  white-space: pre-wrap;
  pointer-events: none;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-obj__textbox--classic {
  overflow: visible;
}

.orb-obj__textbox--boxed {
  overflow: auto;
  padding: 6px 10px;
  border-radius: 8px;
}

.orb-obj__textbox--ring {
  box-shadow: 0 0 0 1px var(--border);
}

.orb-obj__textbox--ring-selected {
  box-shadow: 0 0 0 1px var(--color-corporate-green-50);
}

.orb-obj__stack {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.orb-obj__stack--classic {
  position: relative;
}

.orb-obj__gadget-frame--selected {
  border-radius: 12px;
  box-shadow:
    0 0 0 2px var(--bg),
    0 0 0 4px var(--color-corporate-green-50);
}

.orb-obj__gadget-label {
  margin-top: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-weight: 500;
  white-space: nowrap;
  border-radius: 4px;
  pointer-events: none;
}

.orb-obj__text-pill {
  padding: var(--dimension-2) 6px;
  font-weight: 600;
  white-space: nowrap;
  border-radius: 4px;
  pointer-events: none;
}

.orb-obj__text-pill--selected {
  box-shadow:
    0 0 0 2px var(--bg),
    0 0 0 4px var(--color-corporate-green-50);
}

.orb-obj__icon-box {
  position: relative;
}

.orb-obj__icon-img {
  object-fit: contain;
  user-select: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-obj__broken {
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.orb-obj__state-svg {
  display: block;
  border-radius: 9999px;
  user-select: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-obj__state-svg--selected {
  box-shadow:
    0 0 0 2px var(--bg),
    0 0 0 4px var(--color-corporate-green-50);
}

.orb-obj__arc {
  position: absolute;
  pointer-events: none;
}

.orb-obj__badge {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--dimension-7);
  height: var(--dimension-7);
  border-radius: 9999px;
  box-shadow:
    0 0 0 2px var(--bg),
    0 4px 6px -1px rgb(0 0 0 / 10%),
    0 2px 4px -2px rgb(0 0 0 / 10%);
}

.orb-obj__badge--stale {
  right: -6px;
  bottom: -6px;
  color: var(--text);
  background: var(--color-pending);
}

.orb-obj__badge--ack {
  top: -6px;
  right: -6px;
  color: var(--color-midnight-grey-100);
  background: var(--color-warning);
}

.orb-obj__badge--downtime {
  top: -6px;
  left: -6px;
  color: white;
  background: var(--color-light-blue-50);
}

.orb-obj__badge-icon {
  width: var(--dimension-5);
  height: var(--dimension-5);
}

.orb-obj__label {
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
}

.orb-obj__label--boxed {
  margin-top: 6px;
  padding: var(--dimension-2) 6px;
  border-radius: 4px;
}

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
