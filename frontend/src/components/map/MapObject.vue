<template>
  <!-- Textbox -->
  <div
    v-if="object.type === 'textbox'"
    class="px-2.5 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap pointer-events-none ring-1 transition-all"
    :class="selected
      ? 'ring-indigo-400 bg-[var(--bg-glass)] text-[var(--text)]'
      : 'ring-[var(--border)] bg-[var(--bg-glass)] text-zinc-200'"
    style="backdrop-filter: blur(4px)"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    {{ object.label_text || 'Text' }}
  </div>

  <!-- Gadget -->
  <div
    v-else-if="object.view_type === 'gadget'"
    class="flex flex-col items-center"
    @mouseenter="$emit('hover', $event)"
    @mouseleave="$emit('hover-leave')"
    @contextmenu.prevent="$emit('context-menu', $event)"
  >
    <div :class="selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded-xl' : ''">
      <GadgetRenderer
        :type="object.gadget_type || 'gauge'"
        :metric="object.gadget_metric"
        :state="state"
        :size="iconSize"
      />
    </div>
    <div v-if="object.label_show"
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
        v-if="object.icon"
        :src="`${BASE_URL}icons/${object.icon}`"
        :style="iconStyle"
        draggable="false"
        class="object-contain transition-all duration-300 select-none"
        :class="selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950 rounded' : ''"
      />
      <!-- State circle fallback (Vue-owned, unchanged from original) -->
      <div
        v-else
        class="rounded-full flex items-center justify-center transition-colors duration-300"
        :class="[stateClass, selected ? 'ring-2 ring-indigo-400 ring-offset-2 ring-offset-zinc-950' : '']"
        :style="iconStyle"
      >
        <span class="text-white leading-none select-none" :style="charStyle">{{ typeChar }}</span>
      </div>

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
        class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-400 text-zinc-900 flex items-center justify-center leading-none shadow-sm"
        title="Acknowledged"
        style="font-size: 8px; font-weight: 900"
      >✓</span>
      <!-- Downtime badge -->
      <span
        v-if="state?.in_downtime"
        class="absolute -top-1 -left-1 w-4 h-4 rounded-full bg-blue-400 text-zinc-900 flex items-center justify-center leading-none shadow-sm"
        title="In downtime"
        style="font-size: 8px; font-weight: 900"
      >⏸</span>
    </div>
    <!-- Label -->
    <div
      v-if="object.label_show"
      class="mt-1.5 font-medium whitespace-nowrap pointer-events-none px-1.5 py-0.5 rounded"
      :style="labelStyle"
    >
      {{ displayName }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { MapObject, ObjectState } from '@/types/api'
import GadgetRenderer from './GadgetRenderer.vue'
import { useArcRing } from '@/composables/useArcRing'
import { parsePerfData, utilPercent, utilColor as _utilColor } from '@/utils/perf'

const BASE_URL = import.meta.env.BASE_URL
const RING_PAD = 6

const props = defineProps<{
  object: MapObject
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
  WARNING: 'rgb(245,158,11)', PENDING: 'rgb(113,113,122)',
}
const stateColorRgb = computed(() => STATE_RGB[props.state?.state ?? 'PENDING'] ?? STATE_RGB['PENDING'])

const firstMetricPct = computed(() => {
  const metrics = parsePerfData(props.state?.perf_data ?? '')
  return metrics.length ? utilPercent(metrics[0]) : null
})

const ringUtilColor = computed(() =>
  firstMetricPct.value !== null ? _utilColor(firstMetricPct.value) : stateColorRgb.value,
)

const shouldShowRing = computed(() =>
  !['textbox', 'line'].includes(props.object.type) &&
  props.object.view_type !== 'gadget',
)

useArcRing({
  svgRef: arcSvgEl,
  iconSize: computed(() => props.iconSize),
  pct: firstMetricPct,
  stateColor: stateColorRgb,
  utilColor: ringUtilColor,
  enabled: shouldShowRing,
})

// Original state classes — fallback div is Vue-owned, untouched by D3
const STATE_CLASSES: Record<string, string> = {
  UP: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]',
  OK: 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]',
  DOWN: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
  CRITICAL: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
  UNREACHABLE: 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)]',
  UNKNOWN: 'bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.4)]',
  WARNING: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]',
  PENDING: 'bg-zinc-500',
}
const stateClass = computed(() => STATE_CLASSES[props.state?.state ?? 'PENDING'] ?? STATE_CLASSES['PENDING'])

const charStyle = computed(() => {
  const chars = typeChar.value.length
  const factor = chars === 1 ? 0.46 : 0.30
  return {
    fontSize: `${Math.max(10, Math.round(props.iconSize * factor))}px`,
    fontWeight: '900',
    textShadow: '0 1px 2px rgba(0,0,0,0.4)',
  }
})

const TYPE_CHARS: Record<string, string> = {
  host: 'H', service: 'S', hostgroup: 'HG', servicegroup: 'SG',
  map: 'M', shape: '◆', line: '—',
}
const typeChar = computed(() => TYPE_CHARS[props.object.type] ?? '?')

const labelStyle = computed(() => ({
  fontSize: `${props.object.label_size ?? 11}px`,
  color: props.object.label_color ?? '#e4e4e7',
  background: props.object.label_background && props.object.label_background !== 'transparent'
    ? props.object.label_background
    : 'rgba(0,0,0,0.65)',
  backdropFilter: 'blur(4px)',
  textShadow: '0 1px 3px rgba(0,0,0,0.9)',
  outline: '1px solid rgba(255,255,255,0.12)',
}))

const displayName = computed(() => {
  if (props.object.label_text) return props.object.label_text
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
