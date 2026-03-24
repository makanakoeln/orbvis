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
    <!-- Native chart mode (host linked) -->
    <template v-if="isNativeChart">
      <!-- Waiting for first data point -->
      <div v-if="!hasChartData"
        class="w-full h-full flex flex-col items-center justify-center gap-1.5 border-2 border-dashed border-zinc-600 rounded-lg text-zinc-500">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
        </svg>
        <span class="text-xs">{{ t('boardSettings.graphWaitingData') }}</span>
      </div>
      <!-- D3 chart -->
      <div v-else class="w-full h-full flex flex-col bg-zinc-950/90 rounded-lg overflow-hidden border border-white/10" style="box-shadow: 0 0 0 1px rgba(255,255,255,0.04), 0 4px 24px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.06)">
        <!-- Title row: service / host -->
        <div class="flex items-center justify-between px-2.5 pt-2 pb-0 shrink-0">
          <span class="text-[11px] font-medium text-zinc-300 truncate">
            {{ object.service_description || object.host_name }}
          </span>
          <span class="text-[9px] text-zinc-600 shrink-0 ml-2 uppercase tracking-wide">live</span>
        </div>
        <!-- Metric legend -->
        <div class="flex flex-wrap gap-x-3 gap-y-0.5 px-2.5 pt-1 pb-1.5 shrink-0 border-b border-white/5">
          <div v-for="(label, idx) in chartMetricLabels" :key="label" class="flex items-center gap-1.5 min-w-0">
            <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0" :style="{ background: CHART_PALETTE[idx % CHART_PALETTE.length] }" />
            <span class="text-[10px] text-zinc-500 truncate">{{ label }}</span>
            <span class="text-[10px] font-mono font-semibold shrink-0" :style="{ color: CHART_PALETTE[idx % CHART_PALETTE.length] }">
              {{ chartLatestValues[label]?.value }}<span class="text-zinc-600 ml-0.5 font-normal">{{ chartLatestValues[label]?.unit }}</span>
            </span>
          </div>
        </div>
        <svg ref="chartSvgRef" class="w-full flex-1 mb-1.5" style="overflow: visible" />
      </div>
    </template>
    <!-- URL embed mode -->
    <template v-else>
      <!-- Placeholder: no URL or load error -->
      <div v-if="!object.graph_url || graphLoadFailed"
        class="w-full h-full flex flex-col items-center justify-center gap-1.5 border-2 border-dashed border-zinc-600 rounded-lg text-zinc-500">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
        </svg>
        <span class="text-xs">{{ object.graph_url ? t('boardSettings.graphLoadFailed') : t('boardSettings.graphNoUrl') }}</span>
      </div>
      <!-- img embed -->
      <img v-else-if="object.graph_embed_type !== 'iframe'"
        :src="graphSrc"
        class="block w-full h-full object-fill rounded-lg"
        draggable="false"
        @error="graphLoadFailed = true"
        @load="graphLoadFailed = false"
      />
      <!-- iframe embed -->
      <iframe v-else
        :src="object.graph_url"
        class="block w-full h-full border-0 rounded-lg"
        sandbox="allow-scripts allow-same-origin"
      />
    </template>
    <!-- Optional caption label -->
    <div v-if="object.label?.show && object.label?.text"
      class="absolute -bottom-5 left-0 right-0 text-center text-xs pointer-events-none px-1.5 py-0.5 rounded"
      :style="labelStyle">
      {{ object.label.text }}
    </div>
    <!-- Resize handle (edit mode only) -->
    <div v-if="editMode"
      @pointerdown.stop="$emit('graph-resize-start', $event)"
      class="absolute bottom-0 right-0 w-5 h-5 cursor-se-resize bg-indigo-500/70 hover:bg-indigo-400 rounded-tl flex items-center justify-center transition-colors"
      title="Resize">
      <svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 19.5l15-15M19.5 4.5v6m0-6h-6" />
      </svg>
    </div>
    <!-- Selection ring -->
    <div v-if="selected" class="absolute inset-0 rounded-lg ring-2 ring-indigo-400 ring-offset-1 ring-offset-zinc-950 pointer-events-none" />
  </div>

  <!-- Textbox -->
  <div
    v-else-if="object.type === 'textbox'"
    class="px-2.5 py-1.5 rounded-lg text-sm font-medium whitespace-pre-wrap pointer-events-none ring-1 transition-all overflow-auto"
    :class="selected ? 'ring-indigo-400' : 'ring-[var(--border)]'"
    :style="textboxStyle"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
    v-html="object.label?.text || 'Text'"
  />

  <!-- Gadget -->
  <div
    v-else-if="object.display?.mode === 'gadget'"
    class="flex flex-col items-center"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <div :class="selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded-xl' : ''">
      <GadgetRenderer
        :type="object.display?.gadget_type || 'gauge'"
        :metric="object.display?.gadget_metric"
        :state="state"
        :size="iconSize"
      />
    </div>
    <div v-if="object.label?.show"
      class="mt-1 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
      :style="labelStyle">
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
        :style="iconStyle"
        draggable="false"
        class="object-contain transition-all duration-300 select-none"
        :class="[isSvgIcon ? 'svg-icon' : '', selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded' : '']"
        @error="imgLoadFailed = true"
      />
      <!-- State circle fallback — SVG for crisp sub-pixel text centering -->
      <!-- Not shown for type=image: if the image fails, the object simply becomes invisible -->
      <svg
        v-else-if="object.type !== 'image' || !imgLoadFailed"
        :width="iconSize" :height="iconSize"
        :viewBox="`0 0 ${iconSize} ${iconSize}`"
        overflow="visible"
        class="block select-none transition-all duration-300 rounded-full"
        :class="selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950' : ''"
        :style="{ filter: stateGlow }"
      >
        <circle :cx="iconSize / 2" :cy="iconSize / 2" :r="iconSize / 2" :fill="stateColorRgb" />
        <text
          :x="iconSize / 2" :y="iconSize / 2"
          text-anchor="middle"
          dominant-baseline="central"
          fill="white"
          :font-size="charFontSize"
          font-weight="700"
          font-family="system-ui,-apple-system,BlinkMacSystemFont,sans-serif"
          :letter-spacing="typeChar.length > 1 ? -1 : 0.5"
          style="filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5))"
        >{{ typeChar }}</text>
      </svg>

      <!-- D3 arc ring overlay — pointer-events:none set via attribute + style to ensure
           it never intercepts mousedown/drag events in any browser -->
      <svg
        v-if="shouldShowRing"
        ref="arcSvgEl"
        :width="svgSize" :height="svgSize"
        pointer-events="none"
        class="absolute pointer-events-none"
        :style="{ top: `-${RING_PAD}px`, left: `-${RING_PAD}px`, pointerEvents: 'none' }"
      />

      <!-- Stale data badge -->
      <span
        v-if="state?.stale"
        class="absolute -bottom-1.5 -right-1.5 w-5 h-5 rounded-full bg-zinc-600 text-zinc-200 flex items-center justify-center shadow-md ring-2 ring-[var(--bg)]"
        title="Stale data"
      >
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </span>
      <!-- Acknowledged badge -->
      <span
        v-if="state?.acknowledged"
        class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-amber-400 text-zinc-900 flex items-center justify-center shadow-md ring-2 ring-[var(--bg)]"
        title="Acknowledged"
      >
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
      </span>
      <!-- Downtime badge -->
      <span
        v-if="state?.in_downtime"
        class="absolute -top-1.5 -left-1.5 w-5 h-5 rounded-full bg-blue-500 text-white flex items-center justify-center shadow-md ring-2 ring-[var(--bg)]"
        title="In downtime"
      >
        <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
          <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
        </svg>
      </span>
    </div>
    <!-- Label -->
    <div
      v-if="object.label?.show"
      class="mt-1.5 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
      :style="labelStyle"
    >
      {{ displayName }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, watchEffect, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BoardObject, ObjectState } from '@/types/api'
import GadgetRenderer from './GadgetRenderer.vue'
import { useArcRing } from '@/composables/useArcRing'
import { useMetricChart, CHART_PALETTE } from '@/composables/useMetricChart'
import { parsePerfData, utilPercent, utilColor as _utilColor } from '@/utils/perf'
import { useStatesStore } from '@/stores/states'
import type { MetricPoint } from '@/stores/states'
import { useAuthStore } from '@/stores/auth'

const BASE_URL = import.meta.env.BASE_URL
const RING_PAD = 6

const { t } = useI18n()

const props = defineProps<{
  object: BoardObject
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
  editMode?: boolean
  resizeOverride?: { width: number; height: number }
  backendId?: string
}>()

defineEmits<{
  hover: [event: MouseEvent]
  'hover-leave': []
  'context-menu': [event: MouseEvent]
  'graph-resize-start': [evt: PointerEvent]
}>()

const statesStore = useStatesStore()
const authStore = useAuthStore()

function _triggerHistoryPrefill() {
  if (props.object.type !== 'graph' || !props.object.host_name || !props.backendId) return
  const windowMins = props.object.graph_time_window ?? 60
  statesStore.prefillMetricHistory(
    props.object.id,
    props.backendId,
    props.object.host_name,
    props.object.service_description ?? null,
    windowMins,
    authStore.accessToken!,
  )
}

onMounted(_triggerHistoryPrefill)
watch(() => props.object.graph_time_window, _triggerHistoryPrefill)

// Single arc ring SVG — always a separate overlay SVG that D3 owns exclusively.
// pointer-events="none" on the SVG element (SVG attribute, not CSS) ensures it
// never intercepts mousedown/click events, preserving drag behaviour in edit mode.
const arcSvgEl = ref<SVGSVGElement | null>(null)
const imgLoadFailed = ref(false)

// ---- Graph: native chart mode ----
const chartSvgRef = ref<SVGSVGElement | null>(null)
const isNativeChart = computed(() => props.object.type === 'graph' && !!props.object.host_name)

const chartData = computed((): Record<string, MetricPoint[]> => {
  if (!isNativeChart.value) return {}
  const mv = statesStore.metricValues[props.object.id]
  if (!mv) return {}

  const windowMins = props.object.graph_time_window ?? 60
  const windowSecs = windowMins * 60
  const now = Date.now() / 1000
  const cutoff = now - windowSecs

  const applyWindow = (pts: MetricPoint[]) => {
    const filtered = pts.filter(p => p.ts >= cutoff)
    // If nothing falls in the window yet, show last point as baseline
    return filtered.length ? [...filtered] : pts.length ? [pts[pts.length - 1]] : []
  }

  if (props.object.graph_metric) {
    const pts = mv[props.object.graph_metric]
    return pts ? { [props.object.graph_metric]: applyWindow(pts) } : {}
  }
  return Object.fromEntries(Object.entries(mv).map(([k, v]) => [k, applyWindow(v)]))
})

const chartMetricLabels = computed(() => Object.keys(chartData.value))
const hasChartData = computed(() => chartMetricLabels.value.some(k => chartData.value[k].length > 0))

const chartLatestValues = computed(() =>
  Object.fromEntries(chartMetricLabels.value.map(k => [k, chartData.value[k].at(-1) ?? null]))
)

const graphW = computed(() => props.resizeOverride?.width ?? props.object.graph_width ?? 400)
const graphH = computed(() => props.resizeOverride?.height ?? props.object.graph_height ?? 200)

useMetricChart(
  chartSvgRef,
  chartData,
  () => graphW.value,
  () => Math.max(30, graphH.value - 28),
)

// ---- Graph: URL embed ----
const graphLoadFailed = ref(false)
const refreshTick = ref(0)

watch(() => props.object.graph_url, () => { graphLoadFailed.value = false })
let _refreshTimer: ReturnType<typeof setInterval> | null = null

watchEffect(() => {
  if (_refreshTimer) { clearInterval(_refreshTimer); _refreshTimer = null }
  const interval = props.object.graph_refresh_interval ?? 0
  if (props.object.type === 'graph' && interval > 0) {
    _refreshTimer = setInterval(() => { refreshTick.value++ }, interval * 1000)
  }
})
onUnmounted(() => { if (_refreshTimer) clearInterval(_refreshTimer) })

const graphSrc = computed(() => {
  const url = props.object.graph_url
  if (!url) return ''
  if ((props.object.graph_refresh_interval ?? 0) > 0) {
    const sep = url.includes('?') ? '&' : '?'
    return `${url}${sep}_t=${refreshTick.value}`
  }
  return url
})

const graphWrapperStyle = computed(() => ({
  width: `${graphW.value}px`,
  height: `${graphH.value}px`,
}))

const svgSize = computed(() => props.iconSize + RING_PAD * 2)

const iconStyle = computed(() => ({
  width: `${props.iconSize}px`,
  height: `${props.iconSize}px`,
}))

const STATE_RGB: Record<string, string> = {
  UP: 'rgb(34,197,94)', OK: 'rgb(34,197,94)',
  DOWN: 'rgb(239,68,68)', CRITICAL: 'rgb(239,68,68)',
  UNREACHABLE: 'rgb(249,115,22)', UNKNOWN: 'rgb(249,115,22)',
  WARNING: 'rgb(255,208,0)', PENDING: 'rgb(113,113,122)',
}
const stateColorRgb = computed(() => STATE_RGB[props.state?.state ?? 'PENDING'] ?? STATE_RGB['PENDING'])

const firstMetricPct = computed(() => {
  const metrics = parsePerfData(props.state?.perf_data ?? '')
  return metrics.length ? utilPercent(metrics[0]) : null
})

const ringUtilColor = computed(() =>
  firstMetricPct.value !== null ? _utilColor(firstMetricPct.value) : stateColorRgb.value,
)

const isSvgIcon = computed(() => {
  const icon = props.object.display?.image ?? props.object.image_src
  return icon?.toLowerCase().endsWith('.svg') ?? false
})

const shouldShowRing = computed(() =>
  !['textbox', 'line'].includes(props.object.type) &&
  props.object.display?.mode !== 'gadget' &&
  !(props.object.type === 'image' && imgLoadFailed.value),
)

useArcRing({
  svgRef: arcSvgEl,
  iconSize: computed(() => props.iconSize),
  pct: firstMetricPct,
  stateColor: stateColorRgb,
  utilColor: ringUtilColor,
  enabled: shouldShowRing,
})

const STATE_GLOWS: Record<string, string> = {
  UP:          'drop-shadow(0 0 5px rgba(34,197,94,0.55))',
  OK:          'drop-shadow(0 0 5px rgba(34,197,94,0.55))',
  DOWN:        'drop-shadow(0 0 6px rgba(239,68,68,0.65))',
  CRITICAL:    'drop-shadow(0 0 6px rgba(239,68,68,0.65))',
  UNREACHABLE: 'drop-shadow(0 0 5px rgba(249,115,22,0.55))',
  UNKNOWN:     'drop-shadow(0 0 5px rgba(249,115,22,0.55))',
  WARNING:     'drop-shadow(0 0 5px rgba(255,208,0,0.55))',
  PENDING:     'none',
}
const stateGlow = computed(() => STATE_GLOWS[props.state?.state ?? 'PENDING'] ?? 'none')

const charFontSize = computed(() => {
  const n = typeChar.value.length
  const factor = n === 1 ? 0.44 : n === 2 ? 0.31 : 0.26
  return Math.max(9, Math.round(props.iconSize * factor))
})

const TYPE_CHARS: Record<string, string> = {
  host: 'H', service: 'S', hostgroup: 'HG', servicegroup: 'SG',
  map: 'M', image: '◆', line: '—',
}
const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?')

const textboxStyle = computed(() => ({
  backdropFilter: 'blur(4px)',
  background: props.object.textbox_background ?? 'var(--bg-glass)',
  borderColor: props.object.textbox_border ?? undefined,
  color: 'var(--text)',
  width: props.object.textbox_width ? `${props.object.textbox_width}px` : undefined,
  height: props.object.textbox_height ? `${props.object.textbox_height}px` : undefined,
}))

const labelStyle = computed(() => {
  const bg = props.object.label?.background
  return {
    fontSize: `${props.object.label?.size ?? 11}px`,
    color: props.object.label?.color ?? '#e4e4e7',
    background: bg && bg !== 'transparent' ? bg : 'rgba(0,0,0,0.65)',
    backdropFilter: 'blur(4px)',
    textShadow: '0 1px 3px rgba(0,0,0,0.9)',
    outline: props.object.label_border
      ? `1px solid ${props.object.label_border}`
      : '1px solid rgba(255,255,255,0.12)',
  }
})

const displayName = computed(() => {
  let name = ''
  if (props.object.label?.text) name = props.object.label.text
  else if (props.object.type === 'host') name = props.object.host_name ?? props.object.id
  else if (props.object.type === 'service') name = props.object.service_description ?? props.object.id
  else if (props.object.type === 'map') name = props.object.map_name ?? props.object.id
  else name = props.object.group_name ?? props.object.id
  const maxlen = props.object.label_maxlen
  if (maxlen && maxlen > 0 && name.length > maxlen) return name.slice(0, maxlen) + '…'
  return name
})
</script>

<style scoped>
@keyframes state-pulse {
  0%, 100% { box-shadow: 0 0 6px 1px rgba(239, 68, 68, 0.5); }
  50%       { box-shadow: 0 0 18px 4px rgba(239, 68, 68, 0.85); }
}
</style>
