<template>
  <g :class="{ 'pres-conn--selected': selected }" @pointerdown="$emit('pointerdown', $event)">
    <!-- Wide transparent hit area for selecting / dragging the connector. -->
    <line
      v-if="interactive"
      class="pres-conn__hit"
      :x1="start.x"
      :y1="start.y"
      :x2="end.x"
      :y2="end.y"
      :stroke-width="16 / scale"
    />
    <!-- Selection halo. -->
    <line
      v-if="selected"
      class="pres-conn__halo"
      :x1="start.x"
      :y1="start.y"
      :x2="end.x"
      :y2="end.y"
      :stroke-width="vis.width + 8"
    />
    <!-- The connector itself. -->
    <line
      class="pres-conn__line"
      :class="{ 'pres-conn__line--flow': vis.durationSec !== null }"
      :x1="start.x"
      :y1="start.y"
      :x2="arrowBase.x"
      :y2="arrowBase.y"
      :stroke="vis.color"
      :stroke-width="vis.width"
      :stroke-dasharray="vis.dashArray"
      :style="flowStyle"
      stroke-linecap="round"
    />
    <!-- Arrowhead. -->
    <polygon v-if="isArrow" :points="arrowPoints" :fill="vis.color" />
    <!-- Endpoint handles: drag onto an element to dock, off to free. -->
    <template v-if="selected && interactive">
      <circle
        :cx="start.x"
        :cy="start.y"
        :r="8 / scale"
        :stroke-width="2 / scale"
        class="pres-conn__dot"
        @pointerdown.stop="$emit('endpointDown', 'start', $event)"
      />
      <circle
        :cx="end.x"
        :cy="end.y"
        :r="8 / scale"
        :stroke-width="2 / scale"
        class="pres-conn__dot"
        @pointerdown.stop="$emit('endpointDown', 'end', $event)"
      />
    </template>
    <!-- Value pill at the midpoint. -->
    <g v-if="showPill" :transform="`translate(${mid.x}, ${mid.y})`">
      <rect :x="-pillW / 2" y="-9" :width="pillW" height="18" rx="9" class="pres-conn__pill-bg" />
      <text class="pres-conn__pill-text" text-anchor="middle" dominant-baseline="central">
        {{ vis.valueText }}
      </text>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { ObjectState, ShapeElement } from '@/types/api'
import { flowVisual } from '@/utils/connectorFlow'

interface Pt {
  x: number
  y: number
}

const props = defineProps<{
  element: ShapeElement
  start: Pt
  end: Pt
  state: ObjectState | undefined
  selected: boolean
  interactive: boolean
  scale: number
}>()

defineEmits<{
  pointerdown: [PointerEvent]
  endpointDown: [which: 'start' | 'end', event: PointerEvent]
}>()

const vis = computed(() => flowVisual(props.element, props.state))
const isArrow = computed(() => props.element.shape === 'arrow')

const angle = computed(() => Math.atan2(props.end.y - props.start.y, props.end.x - props.start.x))
const headLen = computed(() => Math.max(10, vis.value.width * 2.4))

// Pull the line back so it meets the arrowhead's base instead of poking through.
const arrowBase = computed<Pt>(() => {
  if (!isArrow.value) return props.end
  return {
    x: props.end.x - Math.cos(angle.value) * headLen.value,
    y: props.end.y - Math.sin(angle.value) * headLen.value
  }
})
const arrowPoints = computed(() => {
  const a = angle.value
  const w = Math.max(6, vis.value.width * 1.6)
  const tip = props.end
  const baseL = {
    x: arrowBase.value.x - Math.sin(a) * w,
    y: arrowBase.value.y + Math.cos(a) * w
  }
  const baseR = {
    x: arrowBase.value.x + Math.sin(a) * w,
    y: arrowBase.value.y - Math.cos(a) * w
  }
  return `${tip.x},${tip.y} ${baseL.x},${baseL.y} ${baseR.x},${baseR.y}`
})

const mid = computed<Pt>(() => ({
  x: (props.start.x + props.end.x) / 2,
  y: (props.start.y + props.end.y) / 2
}))

const showPill = computed(() => vis.value.valueText.length > 0)
const pillW = computed(() => Math.max(28, vis.value.valueText.length * 8 + 12))

// Marching-ants flow: animate the dash offset toward the end by one dash period.
const flowStyle = computed(() => {
  if (vis.value.durationSec === null) return {}
  const period =
    (vis.value.dashArray ?? '')
      .split(/\s+/)
      .map(Number)
      .reduce((a, b) => a + b, 0) || 18
  return {
    '--pres-flow-shift': `${-period}px`,
    animationDuration: `${vis.value.durationSec}s`
  }
})
</script>

<style scoped>
.pres-conn__hit {
  stroke: transparent;
  stroke-width: 16;
  cursor: pointer;
  pointer-events: stroke;
}

.pres-conn__halo {
  stroke: color-mix(in srgb, var(--accent, #15d1a0) 55%, transparent);
  pointer-events: none;
}

.pres-conn__line {
  pointer-events: none;
}

.pres-conn__line--flow {
  animation-name: pres-flow;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
}

@keyframes pres-flow {
  to {
    stroke-dashoffset: var(--pres-flow-shift, -18px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .pres-conn__line--flow {
    animation: none;
  }
}

.pres-conn__dot {
  fill: #fff;
  stroke: var(--accent, #15d1a0);
  pointer-events: auto;
  cursor: grab;
}

.pres-conn__dot:active {
  cursor: grabbing;
}

.pres-conn__pill-bg {
  fill: rgb(0 0 0 / 65%);
  pointer-events: none;
}

.pres-conn__pill-text {
  fill: #fff;
  font-size: 11px;
  font-weight: 600;
  pointer-events: none;
}
</style>
