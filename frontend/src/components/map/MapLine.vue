<template>
  <!-- A line object connects two points; x/y is the start, extra.x2/y2 is the end -->
  <g v-if="hasCoords">
    <line
      :x1="object.x"
      :y1="object.y"
      :x2="x2"
      :y2="y2"
      :stroke="lineColor"
      stroke-width="2"
      stroke-linecap="round"
      pointer-events="none"
    />
    <!-- Arrowhead marker at end point -->
    <circle :cx="x2" :cy="y2" r="4" :fill="lineColor" />
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { MapObject, ObjectState } from '@/types/api'

const props = defineProps<{
  object: MapObject
  state: ObjectState | undefined
}>()

const x2 = computed(() => (props.object.extra?.x2 as number) ?? props.object.x + 50)
const y2 = computed(() => (props.object.extra?.y2 as number) ?? props.object.y + 50)
const hasCoords = computed(() => true)

const STATE_COLORS: Record<string, string> = {
  UP: '#00ff00',
  OK: '#00ff00',
  DOWN: '#ff0000',
  CRITICAL: '#ff0000',
  UNREACHABLE: '#ff8800',
  UNKNOWN: '#ff8800',
  WARNING: '#ffff00',
  PENDING: '#aaaaaa',
}

const lineColor = computed(() => {
  const s = props.state?.state ?? 'PENDING'
  return STATE_COLORS[s] ?? STATE_COLORS['PENDING']
})
</script>
