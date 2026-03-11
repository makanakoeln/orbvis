<template>
  <!-- Traffic light -->
  <div v-if="type === 'trafficlight'"
    class="flex flex-col items-center rounded-xl ring-1"
    style="background: rgba(0,0,0,0.55); border-color: rgba(255,255,255,0.15);"
    :style="{ gap: `${Math.max(2, size * 0.08)}px`, padding: `${Math.max(4, size * 0.12)}px` }">
    <div class="rounded-full transition-all duration-300"
      :style="{ ...bulbStyle(isRed,   '239,68,68'), width: `${size * 0.55}px`, height: `${size * 0.55}px` }" />
    <div class="rounded-full transition-all duration-300"
      :style="{ ...bulbStyle(isAmber, '251,191,36'), width: `${size * 0.55}px`, height: `${size * 0.55}px` }" />
    <div class="rounded-full transition-all duration-300"
      :style="{ ...bulbStyle(isGreen, '34,197,94'),  width: `${size * 0.55}px`, height: `${size * 0.55}px` }" />
  </div>

  <!-- Progress bar -->
  <div v-else-if="type === 'bar'" class="flex flex-col items-center" :style="{ width: size + 'px', gap: Math.max(2, size * 0.05) + 'px' }">
    <div class="relative w-full rounded-full overflow-hidden ring-1"
      style="background: rgba(0,0,0,0.5); ring-color: rgba(255,255,255,0.15);"
      :style="{ height: Math.max(10, Math.round(size * 0.22)) + 'px', boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.15)' }">
      <div class="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
        :style="{ width: pct + '%', background: color }" />
      <span class="absolute inset-0 flex items-center justify-center font-bold"
        style="color: #f4f4f5; text-shadow: 0 1px 3px rgba(0,0,0,0.9);"
        :style="{ fontSize: Math.max(8, Math.round(size * 0.13)) + 'px' }">{{ pct.toFixed(0) }}%</span>
    </div>
    <span style="color: rgba(255,255,255,0.7); text-shadow: 0 1px 3px rgba(0,0,0,0.9);"
      class="truncate w-full text-center"
      :style="{ fontSize: Math.max(8, Math.round(size * 0.13)) + 'px' }">{{ valueLabel }}</span>
  </div>

  <!-- Gauge (SVG semicircle arc) -->
  <div v-else class="flex flex-col items-center">
    <svg :width="size" :height="size * 0.65" :viewBox="`0 0 ${size} ${size * 0.65}`">
      <path :d="bgArc" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="8" stroke-linecap="round" />
      <path :d="valArc" fill="none" :stroke="color" stroke-width="8" stroke-linecap="round"
        class="transition-all duration-500" />
      <text :x="size / 2" :y="size * 0.55" text-anchor="middle"
        :font-size="size * 0.18" font-weight="700"
        fill="white" style="filter: drop-shadow(0 1px 3px rgba(0,0,0,0.9))">{{ pct.toFixed(0) }}%</text>
    </svg>
    <span style="color: rgba(255,255,255,0.7); text-shadow: 0 1px 3px rgba(0,0,0,0.9);"
      class="truncate" :style="{ fontSize: '9px', maxWidth: size + 'px' }">{{ valueLabel }}</span>
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

// Bulb style: lit = solid colored glow; unlit = slightly lighter than the dark housing + colored ring
// The bulbs always sit inside the dark housing (rgba(0,0,0,0.55)), so contrast against
// the housing — not the map background — is what matters here.
function bulbStyle(active: boolean, rgb: string): Record<string, string> {
  if (active) {
    return {
      background: `rgb(${rgb})`,
      boxShadow: `0 0 10px 2px rgba(${rgb},0.7)`,
    }
  }
  return {
    background: 'rgba(255,255,255,0.07)',
    boxShadow: `inset 0 0 0 1.5px rgba(${rgb},0.55), inset 0 0 6px rgba(${rgb},0.2)`,
  }
}

// Gauge arc helpers (180° sweep from left to right)
const R = computed(() => props.size * 0.4)
const cx = computed(() => props.size / 2)
const cy = computed(() => props.size * 0.55)

function polarX(angle: number) { return cx.value + R.value * Math.cos((angle * Math.PI) / 180) }
function polarY(angle: number) { return cy.value + R.value * Math.sin((angle * Math.PI) / 180) }

const START = 180
const SWEEP = 180

const bgArc = computed(() => {
  const ex = polarX(START + SWEEP), ey = polarY(START + SWEEP)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})

const valArc = computed(() => {
  const sweep = (pct.value / 100) * SWEEP
  if (sweep < 1) return ''
  const ex = polarX(START + sweep), ey = polarY(START + sweep)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})
</script>
