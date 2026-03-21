<template>
  <!-- Textbox -->
  <div
    v-if="object.type === 'textbox'"
    class="px-2.5 py-1.5 rounded-lg text-sm font-medium whitespace-pre-wrap pointer-events-none ring-1 transition-all"
    :class="selected
      ? 'ring-indigo-400 bg-[var(--bg-glass)] text-[var(--text)]'
      : 'ring-[var(--border)] bg-[var(--bg-glass)] text-zinc-200'"
    style="backdrop-filter: blur(4px)"
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
        v-if="object.display?.image ?? object.image_src"
        :src="`${BASE_URL}images/${object.display?.image ?? object.image_src}`"
        :style="iconStyle"
        draggable="false"
        class="object-contain transition-all duration-300 select-none"
        :class="[isSvgIcon ? 'svg-icon' : '', selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded' : '']"
      />
      <!-- State circle fallback — SVG for crisp sub-pixel text centering -->
      <svg
        v-else
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
import { computed, ref } from 'vue'
import type { BoardObject, ObjectState } from '@/types/api'
import GadgetRenderer from './GadgetRenderer.vue'
import { useArcRing } from '@/composables/useArcRing'
import { parsePerfData, utilPercent, utilColor as _utilColor } from '@/utils/perf'

const BASE_URL = import.meta.env.BASE_URL
const RING_PAD = 6

const props = defineProps<{
  object: BoardObject
  state: ObjectState | undefined
  iconSize: number
  selected?: boolean
}>()

defineEmits<{
  hover: [event: MouseEvent]
  'hover-leave': []
  'context-menu': [event: MouseEvent]
}>()

// Single arc ring SVG — always a separate overlay SVG that D3 owns exclusively.
// pointer-events="none" on the SVG element (SVG attribute, not CSS) ensures it
// never intercepts mousedown/click events, preserving drag behaviour in edit mode.
const arcSvgEl = ref<SVGSVGElement | null>(null)

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
  props.object.display?.mode !== 'gadget',
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

const labelStyle = computed(() => ({
  fontSize: `${props.object.label?.size ?? 11}px`,
  color: props.object.label?.color ?? '#e4e4e7',
  background: props.object.label?.background && props.object.label.background !== 'transparent'
    ? props.object.label.background
    : 'rgba(0,0,0,0.65)',
  backdropFilter: 'blur(4px)',
  textShadow: '0 1px 3px rgba(0,0,0,0.9)',
  outline: '1px solid rgba(255,255,255,0.12)',
}))

const displayName = computed(() => {
  if (props.object.label?.text) return props.object.label.text
  if (props.object.type === 'host') return props.object.host_name ?? props.object.id
  if (props.object.type === 'service') return props.object.service_description ?? props.object.id
  if (props.object.type === 'map') return props.object.map_name ?? props.object.id
  if (props.object.group_name) return props.object.group_name
  return props.object.id
})
</script>

<style scoped>
@keyframes state-pulse {
  0%, 100% { box-shadow: 0 0 6px 1px rgba(239, 68, 68, 0.5); }
  50%       { box-shadow: 0 0 18px 4px rgba(239, 68, 68, 0.85); }
}
</style>
