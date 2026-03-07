<template>
  <!-- Traffic light -->
  <div v-if="type === 'trafficlight'"
    class="flex flex-col items-center rounded-xl bg-zinc-900/80 ring-1 ring-white/10"
    :style="{ gap: `${Math.max(2, size * 0.08)}px`, padding: `${Math.max(4, size * 0.12)}px` }">
    <div class="rounded-full" :style="{ width: `${size * 0.55}px`, height: `${size * 0.55}px` }" :class="isRed    ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]'    : 'bg-red-950'" />
    <div class="rounded-full" :style="{ width: `${size * 0.55}px`, height: `${size * 0.55}px` }" :class="isAmber  ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]' : 'bg-amber-950'" />
    <div class="rounded-full" :style="{ width: `${size * 0.55}px`, height: `${size * 0.55}px` }" :class="isGreen  ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]'  : 'bg-green-950'" />
  </div>

  <!-- Progress bar -->
  <div v-else-if="type === 'bar'" class="flex flex-col items-center" :style="{ width: size + 'px', gap: Math.max(2, size * 0.05) + 'px' }">
    <div class="relative w-full rounded-full overflow-hidden bg-zinc-800 ring-1 ring-zinc-700"
      :style="{ height: Math.max(10, Math.round(size * 0.22)) + 'px' }">
      <div class="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
        :style="{ width: pct + '%', background: color }" />
      <span class="absolute inset-0 flex items-center justify-center text-white font-bold"
        :style="{ fontSize: Math.max(8, Math.round(size * 0.13)) + 'px' }">{{ pct.toFixed(0) }}%</span>
    </div>
    <span class="text-zinc-400 truncate w-full text-center"
      :style="{ fontSize: Math.max(8, Math.round(size * 0.13)) + 'px' }">{{ valueLabel }}</span>
  </div>

  <!-- Gauge (SVG semicircle arc) -->
  <div v-else class="flex flex-col items-center">
    <svg :width="size" :height="size * 0.65" :viewBox="`0 0 ${size} ${size * 0.65}`">
      <path :d="bgArc"   fill="none" stroke="#3f3f46" stroke-width="8" stroke-linecap="round" />
      <path :d="valArc"  fill="none" :stroke="color"  stroke-width="8" stroke-linecap="round"
        class="transition-all duration-500" />
      <text :x="size / 2" :y="size * 0.55" text-anchor="middle"
        :font-size="size * 0.18" font-weight="700" fill="white">{{ pct.toFixed(0) }}%</text>
    </svg>
    <span class="text-zinc-400 truncate" :style="{ fontSize: '9px', maxWidth: size + 'px' }">{{ valueLabel }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ObjectState } from '@/types/api'
import { parsePerfData, getMetric, utilPercent, utilColor } from '@/utils/perf'

const props = defineProps<{
  type: string          // 'gauge' | 'bar' | 'trafficlight'
  metric?: string | null
  state: ObjectState | undefined
  size: number
}>()

const metrics = computed(() => parsePerfData(props.state?.perf_data ?? ''))
const m       = computed(() => getMetric(metrics.value, props.metric))
const pct     = computed(() => m.value ? utilPercent(m.value) : 0)
const color   = computed(() => utilColor(pct.value))

const valueLabel = computed(() => {
  if (!m.value) return '—'
  const { value, unit } = m.value
  return unit ? `${value.toFixed(1)} ${unit}` : value.toFixed(1)
})

// Traffic light state
const monState = computed(() => props.state?.state ?? 'PENDING')
const isRed   = computed(() => ['DOWN', 'CRITICAL'].includes(monState.value))
const isAmber = computed(() => ['WARNING', 'UNKNOWN', 'UNREACHABLE'].includes(monState.value))
const isGreen = computed(() => ['UP', 'OK'].includes(monState.value))

// Gauge arc helpers (180° sweep from left to right)
const R = computed(() => props.size * 0.4)
const cx = computed(() => props.size / 2)
const cy = computed(() => props.size * 0.55)

function polarX(angle: number) { return cx.value + R.value * Math.cos((angle * Math.PI) / 180) }
function polarY(angle: number) { return cy.value + R.value * Math.sin((angle * Math.PI) / 180) }

const START = 180  // left
const SWEEP = 180  // half circle

const bgArc = computed(() => {
  const ex = polarX(START + SWEEP), ey = polarY(START + SWEEP)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})

const valArc = computed(() => {
  const sweep = (pct.value / 100) * SWEEP
  if (sweep < 1) return ''
  const ex = polarX(START + sweep), ey = polarY(START + sweep)
  const large = sweep > 180 ? 1 : 0
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 ${large} 1 ${ex} ${ey}`
})
</script>
