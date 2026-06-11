<template>
  <!-- Traffic light -->
  <div
    v-if="type === 'trafficlight'"
    class="orb-gadget__traffic"
    style="background: var(--gadget-bg); border-color: var(--gadget-ring)"
    :style="{ gap: `${Math.max(2, size * 0.08)}px`, padding: `${Math.max(4, size * 0.12)}px` }"
  >
    <div
      class="orb-gadget__bulb"
      :style="{
        ...bulbStyle(isRed, '239,68,68'),
        width: `${size * 0.55}px`,
        height: `${size * 0.55}px`
      }"
    />
    <div
      class="orb-gadget__bulb"
      :style="{
        ...bulbStyle(isAmber, '255,208,0'),
        width: `${size * 0.55}px`,
        height: `${size * 0.55}px`
      }"
    />
    <div
      class="orb-gadget__bulb"
      :style="{
        ...bulbStyle(isGreen, '34,197,94'),
        width: `${size * 0.55}px`,
        height: `${size * 0.55}px`
      }"
    />
  </div>

  <!-- Progress bar -->
  <div
    v-else-if="type === 'bar'"
    class="orb-gadget__stack"
    :style="{ width: size + 'px', gap: Math.max(2, size * 0.05) + 'px' }"
  >
    <div
      class="orb-gadget__track"
      style="background: var(--gadget-bar-bg)"
      :style="{
        height: Math.max(10, Math.round(size * 0.22)) + 'px',
        boxShadow: 'inset 0 0 0 1px var(--gadget-ring)'
      }"
    >
      <div class="orb-gadget__fill" :style="{ width: fillPct + '%', background: color }" />
      <span
        class="orb-gadget__pct"
        style="color: var(--gadget-text); text-shadow: var(--shadow-text)"
        :style="{ fontSize: Math.max(8, Math.round(size * 0.13 * readoutScale)) + 'px' }"
        >{{ readout }}</span
      >
    </div>
    <span
      v-if="caption"
      style="color: var(--gadget-text-dim); text-shadow: var(--shadow-text)"
      class="orb-gadget__value orb-gadget__value--bar"
      :style="{ fontSize: Math.max(8, Math.round(size * 0.13)) + 'px' }"
      >{{ caption }}</span
    >
  </div>

  <!-- Gauge (SVG semicircle arc) -->
  <div v-else class="orb-gadget__stack">
    <svg :width="size" :height="size * 0.65" :viewBox="`0 0 ${size} ${size * 0.65}`">
      <path
        :d="bgArc"
        fill="none"
        :stroke="`var(--gadget-track)`"
        stroke-width="8"
        stroke-linecap="round"
      />
      <path
        :d="valArc"
        fill="none"
        :stroke="color"
        stroke-width="8"
        stroke-linecap="round"
        class="orb-gadget__arc"
      />
      <text
        :x="size / 2"
        :y="size * 0.55"
        text-anchor="middle"
        :font-size="size * 0.18 * readoutScale"
        font-weight="700"
        fill="var(--gadget-text)"
        stroke="rgb(0 0 0 / 0.9)"
        :stroke-width="size * 0.05"
        stroke-linejoin="round"
        paint-order="stroke"
      >
        {{ readout }}
      </text>
    </svg>
    <span
      v-if="caption"
      style="color: var(--gadget-text-dim); text-shadow: var(--shadow-text)"
      class="orb-gadget__value"
      :style="{ fontSize: '9px', maxWidth: size + 'px' }"
      >{{ caption }}</span
    >
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { MetricUnitMap, ObjectState, PerfometerResult } from '@/types/api'
import { renderMetricValue } from '@/utils/metricFormat'
import {
  getMetric,
  hasFillScale,
  hasPercentScale,
  parsePerfData,
  utilColor,
  utilPercent
} from '@/utils/perf'
import { stateColor } from '@/utils/stateColors'

const props = defineProps<{
  type: string // 'gauge' | 'bar' | 'trafficlight'
  metric?: string | null
  state: ObjectState | undefined
  size: number
  // CMK perfometer for the bound service. Supplies the fill percentage when
  // the raw perf_data carries no scale (no max/crit and not a % unit) and the
  // CMK-formatted value for the caption.
  perfometer?: PerfometerResult | null
  // Registered display units per raw perfdata label (CMK metric registry) —
  // the readout then matches the Checkmk GUI exactly.
  metricUnits?: MetricUnitMap | null
}>()

const metrics = computed(() => parsePerfData(props.state?.perf_data ?? ''))
const m = computed(() => getMetric(metrics.value, props.metric))
const scaled = computed(() => (m.value ? hasPercentScale(m.value) : false))
const pct = computed(() => (m.value ? utilPercent(m.value) : 0))
// Fill is proportional (NagVis scales to crit when there's no max). Metrics
// without any client-side scale fall back to the CMK perfometer percentage,
// which is computed from the plugin's focus_range. The readout text stays
// absolute unless the unit is %.
const fillPct = computed(() => {
  if (m.value && !hasFillScale(m.value)) return props.perfometer?.pcts[0] ?? 0
  return pct.value
})
const color = computed(() => (scaled.value ? utilColor(pct.value) : stateColor(props.state?.state)))

const valueLabel = computed(() =>
  m.value ? renderMetricValue(m.value.value, props.metricUnits?.[m.value.label], m.value.unit) : '—'
)

// Primary readout inside the gauge/bar: a percentage only when one is
// meaningful, otherwise the absolute value (the caption below is then redundant).
// The caption prefers the CMK perfometer label ("RAM used 8.32 GiB") over the
// client-side formatting of the raw perf value.
const readout = computed(() => (scaled.value ? `${pct.value.toFixed(0)}%` : valueLabel.value))
const caption = computed(() => (scaled.value ? props.perfometer?.label || valueLabel.value : ''))

// Shrink the readout font for long absolute values so e.g. "512 MB" still fits.
const readoutScale = computed(() => {
  const n = readout.value.length
  if (n <= 3) return 1
  if (n <= 5) return 0.78
  if (n <= 7) return 0.62
  return 0.5
})

// Traffic light state
const monState = computed(() => props.state?.state ?? 'PENDING')
const isRed = computed(() => ['DOWN', 'CRITICAL'].includes(monState.value))
const isAmber = computed(() => ['WARNING', 'UNKNOWN', 'UNREACHABLE'].includes(monState.value))
const isGreen = computed(() => ['UP', 'OK'].includes(monState.value))

// Bulb style: lit = solid colored glow; unlit = slightly lighter than the dark housing + colored ring
// The bulbs always sit inside the dark housing (rgba(0,0,0,0.55)), so contrast against
// the housing — not the map background — is what matters here.
function bulbStyle(active: boolean, rgb: string): Record<string, string> {
  if (active) {
    return {
      background: `rgb(${rgb})`,
      boxShadow: `0 0 10px 2px rgba(${rgb},0.7)`
    }
  }
  return {
    background: 'rgba(255,255,255,0.07)',
    boxShadow: `inset 0 0 0 1.5px rgba(${rgb},0.55), inset 0 0 6px rgba(${rgb},0.2)`
  }
}

// Gauge arc helpers (180° sweep from left to right)
const R = computed(() => props.size * 0.4)
const cx = computed(() => props.size / 2)
const cy = computed(() => props.size * 0.55)

function polarX(angle: number) {
  return cx.value + R.value * Math.cos((angle * Math.PI) / 180)
}
function polarY(angle: number) {
  return cy.value + R.value * Math.sin((angle * Math.PI) / 180)
}

const START = 180
const SWEEP = 180

const bgArc = computed(() => {
  const ex = polarX(START + SWEEP),
    ey = polarY(START + SWEEP)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})

const valArc = computed(() => {
  const sweep = (fillPct.value / 100) * SWEEP
  if (sweep < 1) return ''
  const ex = polarX(START + sweep),
    ey = polarY(START + sweep)
  return `M ${polarX(START)} ${polarY(START)} A ${R.value} ${R.value} 0 0 1 ${ex} ${ey}`
})
</script>

<style scoped>
.orb-gadget__traffic {
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 12px;
  box-shadow: 0 0 0 1px currentcolor;
}

.orb-gadget__bulb {
  border-radius: 9999px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-gadget__stack {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.orb-gadget__track {
  position: relative;
  overflow: hidden;
  width: 100%;
  border-radius: 9999px;
}

.orb-gadget__fill {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  border-radius: 9999px;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-gadget__pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.orb-gadget__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-gadget__value--bar {
  width: 100%;
  text-align: center;
}

.orb-gadget__arc {
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>
