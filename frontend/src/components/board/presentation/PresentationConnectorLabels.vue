<template>
  <g>
    <g v-for="(pill, i) in pills" :key="i" :transform="`translate(${pill.x}, ${pill.y})`">
      <rect
        :x="-pill.w / 2"
        :y="-pill.h / 2"
        :width="pill.w"
        :height="pill.h"
        :rx="pill.h / 2"
        class="pres-conn__pill-bg"
        :style="{ fill: pillBg }"
      />
      <text
        class="pres-conn__pill-text"
        text-anchor="middle"
        dominant-baseline="central"
        :style="{ fill: pillColor, fontSize: `${pillFontSize}px` }"
      >
        {{ pill.text }}
      </text>
    </g>
  </g>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { splitPerfometerLabel, usePerfometer } from '@/composables/usePerfometer'
import type { ObjectState, ShapeElement } from '@/types/api'
import { connectorLabelVisible, flowVisual } from '@/utils/connectorFlow'
import { hasBinding, isMetriclessBinding } from '@/utils/presentationSampleState'

interface Pt {
  x: number
  y: number
}

const props = defineProps<{
  element: ShapeElement
  start: Pt
  end: Pt
  state: ObjectState | undefined
  connectionId?: string | null
}>()

const visForward = computed(() => flowVisual(props.element, props.state))
const visBack = computed(() =>
  flowVisual(props.element, props.state, props.element.flow_metric_back ?? null)
)
const twoWay = computed(() => !!props.element.flow && !!props.element.flow_metric_back)

const labelShow = computed(() => connectorLabelVisible(props.element))
const pillFontSize = computed(() => props.element.label?.size ?? 11)
const pillColor = computed(() => props.element.label?.color || '#fff')
const pillBg = computed(() => props.element.label?.background || 'rgb(0 0 0 / 65%)')

// CMK perfometer for the bound service: supplies properly formatted values
// with units ("244 bit/s") where the raw perf_data has none. The bidirectional
// interface perfometer renders "in / out" — split into the two direction
// halves. A one-way link with an explicit label text never reads the result,
// so it doesn't fetch either.
const perfometer = usePerfometer({
  connectionId: () => props.connectionId,
  hostName: () => props.element.host_name,
  serviceDescription: () => props.element.service_description,
  perfData: () => props.state?.perf_data,
  enabled: () =>
    labelShow.value &&
    hasBinding(props.element) &&
    !isMetriclessBinding(props.element) &&
    !!props.element.service_description &&
    (twoWay.value || !props.element.label?.text)
})

const cmkSplit = computed(() => splitPerfometerLabel(perfometer.value?.label))

interface Pill {
  x: number
  y: number
  text: string
  w: number
  h: number
}

function lerp(t: number): Pt {
  return {
    x: props.start.x + (props.end.x - props.start.x) * t,
    y: props.start.y + (props.end.y - props.start.y) * t
  }
}

function pillFor(at: Pt, text: string): Pill {
  const h = Math.max(18, pillFontSize.value + 8)
  return {
    x: at.x,
    y: at.y,
    text,
    w: Math.max(28, text.length * pillFontSize.value * 0.72 + 12),
    h
  }
}

// A known utilization keeps its "%" display; only raw unitless values are
// upgraded to the CMK-formatted bandwidth string.
function directionText(vis: { util: number | null; valueText: string }, half: 0 | 1): string {
  if (vis.util !== null) return vis.valueText
  return cmkSplit.value[half] || vis.valueText
}

const pills = computed<Pill[]>(() => {
  if (!labelShow.value) return []
  if (!twoWay.value) {
    const text = props.element.label?.text || directionText(visForward.value, 0)
    return text ? [pillFor(lerp(0.5), text)] : []
  }
  const out: Pill[] = []
  const fwd = directionText(visForward.value, 0)
  const back = directionText(visBack.value, 1)
  if (fwd) out.push(pillFor(lerp(0.25), fwd))
  if (back) out.push(pillFor(lerp(0.75), back))
  return out
})
</script>

<style scoped>
.pres-conn__pill-bg {
  pointer-events: none;
}

.pres-conn__pill-text {
  font-weight: 600;
  pointer-events: none;
}
</style>
