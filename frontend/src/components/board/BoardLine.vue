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
      :style="editMode ? 'cursor: move' : 'cursor: default'"
      @mousedown.prevent.stop="editMode ? $emit('line-drag-start', $event, 'move') : undefined"
      @contextmenu.prevent.stop="$emit('context-menu', $event)"
      @click.stop
    />

    <!-- Weathermap line -->
    <template v-if="isWeathermap">
      <defs>
        <linearGradient
          :id="gradientId"
          gradientUnits="userSpaceOnUse"
          :x1="x1"
          :y1="y1"
          :x2="x2"
          :y2="y2"
        >
          <stop offset="0%" :stop-color="wmColor" />
          <stop offset="100%" :stop-color="wmColor" stop-opacity="0.6" />
        </linearGradient>
      </defs>
      <line
        :x1="x1"
        :y1="y1"
        :x2="x2"
        :y2="y2"
        :stroke="`url(#${gradientId})`"
        stroke-width="4"
        stroke-linecap="round"
        pointer-events="none"
      />
      <!-- Utilization label at midpoint -->
      <text
        :x="(x1 + x2) / 2"
        :y="(y1 + y2) / 2 - 6"
        text-anchor="middle"
        font-size="11"
        font-weight="600"
        :fill="wmColor"
        style="text-shadow: 0 1px 3px rgb(0 0 0 / 80%)"
        pointer-events="none"
        >{{ wmLabel }}</text
      >
    </template>

    <!-- Normal line -->
    <template v-else>
      <!-- Border/outline line (rendered behind) -->
      <line
        v-if="lineColorBorder"
        :x1="x1"
        :y1="y1"
        :x2="x2"
        :y2="y2"
        :stroke="lineColorBorder"
        stroke-width="4"
        stroke-linecap="round"
        :stroke-dasharray="isDashed ? '6 4' : undefined"
        pointer-events="none"
      />
      <line
        :x1="x1"
        :y1="y1"
        :x2="x2"
        :y2="y2"
        :stroke="lineColor"
        stroke-width="2"
        stroke-linecap="round"
        :stroke-dasharray="isDashed ? '6 4' : undefined"
        pointer-events="none"
      />
      <!-- Arrow at endpoint -->
      <polygon
        v-if="hasEndArrow"
        :points="arrowPoints(x2, y2, x1, y1)"
        :fill="lineColor"
        pointer-events="none"
      />
      <!-- Arrow at startpoint -->
      <polygon
        v-if="hasStartArrow"
        :points="arrowPoints(x1, y1, x2, y2)"
        :fill="lineColor"
        pointer-events="none"
      />
      <!-- Dot fallback -->
      <circle
        v-if="!hasEndArrow && !hasStartArrow"
        :cx="x2"
        :cy="y2"
        r="4"
        :fill="lineColor"
        pointer-events="none"
      />
    </template>

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
import { computed } from 'vue'

import type { BoardObject, ObjectState } from '@/types/api'
import { getMetric, parsePerfData, utilColor, utilPercent } from '@/utils/perf'

const props = defineProps<{
  object: BoardObject
  state: ObjectState | undefined
  editMode: boolean
  dragCoords?: { x: number; y: number; x2: number; y2: number }
}>()

defineEmits<{
  'line-drag-start': [event: MouseEvent, mode: 'move' | 'start' | 'end']
  'context-menu': [event: MouseEvent]
}>()

const x1 = computed(() => props.dragCoords?.x ?? props.object.x)
const y1 = computed(() => props.dragCoords?.y ?? props.object.y)
const x2 = computed(() => props.dragCoords?.x2 ?? props.object.x2 ?? props.object.x + 50)
const y2 = computed(() => props.dragCoords?.y2 ?? props.object.y2 ?? props.object.y + 50)

const STATE_COLORS: Record<string, string> = {
  UP: '#4ade80',
  OK: '#4ade80',
  DOWN: '#f87171',
  CRITICAL: '#f87171',
  UNREACHABLE: '#fb923c',
  UNKNOWN: '#fb923c',
  WARNING: '#ffd000',
  PENDING: '#9ca3af',
}
const lineColor = computed(
  () =>
    props.object.line_color ??
    STATE_COLORS[props.state?.state ?? 'PENDING'] ??
    STATE_COLORS['PENDING'],
)
const lineColorBorder = computed(() => props.object.line_color_border ?? null)

const isWeathermap = computed(() => props.object.line_style === 'weathermap')
const isDashed = computed(() => props.object.line_style === 'dashed')
const hasEndArrow = computed(
  () => props.object.line_style === 'arrow_end' || props.object.line_style === 'arrow_both',
)
const hasStartArrow = computed(
  () => props.object.line_style === 'arrow_start' || props.object.line_style === 'arrow_both',
)

function arrowPoints(tx: number, ty: number, fx: number, fy: number): string {
  const angle = Math.atan2(ty - fy, tx - fx)
  const len = 12,
    w = 6
  const p1x = tx - len * Math.cos(angle) + w * Math.sin(angle)
  const p1y = ty - len * Math.sin(angle) - w * Math.cos(angle)
  const p2x = tx - len * Math.cos(angle) - w * Math.sin(angle)
  const p2y = ty - len * Math.sin(angle) + w * Math.cos(angle)
  return `${tx},${ty} ${p1x},${p1y} ${p2x},${p2y}`
}

// Weathermap
const gradientId = computed(() => `wm-grad-${props.object.id}`)

const wmMetrics = computed(() => parsePerfData(props.state?.perf_data ?? ''))
const wmMetric = computed(() =>
  getMetric(wmMetrics.value, props.object.weathermap_metric ?? undefined),
)
const wmPct = computed(() => (wmMetric.value ? utilPercent(wmMetric.value) : 0))
const wmColor = computed(() => utilColor(wmPct.value))
const wmLabel = computed(() => {
  if (!wmMetric.value) return ''
  const m = wmMetric.value
  const val =
    m.unit === '%'
      ? `${m.value.toFixed(0)}%`
      : m.unit
        ? `${m.value.toFixed(1)} ${m.unit}`
        : `${m.value.toFixed(0)}`
  return `${val} (${wmPct.value.toFixed(0)}%)`
})
</script>
