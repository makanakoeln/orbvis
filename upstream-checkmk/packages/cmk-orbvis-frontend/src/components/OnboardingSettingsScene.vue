<template>
  <div v-if="canvasStyle" class="scene" :style="canvasStyle">
    <!-- Background image fades in/out -->
    <div class="bg-layer" />

    <!-- Connection lines (rendered below objects) -->
    <svg class="lines-layer">
      <!-- web-server-01 → HTTP -->
      <line
        class="flow-line"
        :x1="px(22)"
        :y1="py(29)"
        :x2="px(70)"
        :y2="py(26)"
        stroke="rgb(74,222,128)"
        stroke-width="2"
        stroke-dasharray="8 4"
      />
      <!-- web-server-01 → db-server -->
      <line
        class="flow-line-slow"
        :x1="px(22)"
        :y1="py(30)"
        :x2="px(34)"
        :y2="py(52)"
        stroke="rgb(148,163,184)"
        stroke-width="1.5"
        stroke-dasharray="6 4"
      />
      <!-- db-server → Production -->
      <line
        class="flow-line"
        :x1="px(34)"
        :y1="py(52)"
        :x2="px(63)"
        :y2="py(53)"
        stroke="rgb(248,113,113)"
        stroke-width="2"
        stroke-dasharray="8 4"
      />
      <!-- Production → backup -->
      <line
        class="flow-line-slow"
        :x1="px(64)"
        :y1="py(53)"
        :x2="px(80)"
        :y2="py(71)"
        stroke="rgb(251,146,60)"
        stroke-width="1.5"
        stroke-dasharray="6 4"
      />
    </svg>

    <!-- Performance graph: CPU Load (76% = WARNING, with warn/crit threshold lines) -->
    <div class="graph-gadget" :style="graphStyle">
      <!-- Header -->
      <div class="graph-header">
        <span class="graph-title">CPU Utilization</span>
        <span class="graph-value">76%</span>
      </div>
      <!-- Chart: Y-axis 0–100, warn@75%, crit@90% -->
      <svg width="175" height="92" viewBox="0 0 175 92">
        <defs>
          <linearGradient id="cpu-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="rgb(245,158,11)" stop-opacity="0.40" />
            <stop offset="100%" stop-color="rgb(245,158,11)" stop-opacity="0.03" />
          </linearGradient>
        </defs>
        <!-- Horizontal grid lines at 0, 25, 50, 75, 100 % -->
        <line x1="30" y1="8" x2="169" y2="8" stroke="rgba(255,255,255,0.12)" />
        <line x1="30" y1="24.5" x2="169" y2="24.5" stroke="rgba(255,255,255,0.12)" />
        <line x1="30" y1="41" x2="169" y2="41" stroke="rgba(255,255,255,0.12)" />
        <line x1="30" y1="57.5" x2="169" y2="57.5" stroke="rgba(255,255,255,0.12)" />
        <line x1="30" y1="74" x2="169" y2="74" stroke="rgba(255,255,255,0.12)" />
        <!-- Y-axis line + ticks -->
        <line x1="30" y1="8" x2="30" y2="74" stroke="rgba(255,255,255,0.25)" />
        <line x1="27" y1="8" x2="30" y2="8" stroke="rgba(255,255,255,0.35)" />
        <line x1="27" y1="24.5" x2="30" y2="24.5" stroke="rgba(255,255,255,0.35)" />
        <line x1="27" y1="41" x2="30" y2="41" stroke="rgba(255,255,255,0.35)" />
        <line x1="27" y1="57.5" x2="30" y2="57.5" stroke="rgba(255,255,255,0.35)" />
        <line x1="27" y1="74" x2="30" y2="74" stroke="rgba(255,255,255,0.35)" />
        <!-- Y-axis labels -->
        <text
          x="26"
          y="11"
          text-anchor="end"
          font-size="7"
          fill="rgba(255,255,255,0.50)"
          font-family="system-ui,sans-serif"
        >
          100
        </text>
        <text
          x="26"
          y="27.5"
          text-anchor="end"
          font-size="7"
          fill="rgba(255,255,255,0.50)"
          font-family="system-ui,sans-serif"
        >
          75
        </text>
        <text
          x="26"
          y="44"
          text-anchor="end"
          font-size="7"
          fill="rgba(255,255,255,0.50)"
          font-family="system-ui,sans-serif"
        >
          50
        </text>
        <text
          x="26"
          y="60.5"
          text-anchor="end"
          font-size="7"
          fill="rgba(255,255,255,0.50)"
          font-family="system-ui,sans-serif"
        >
          25
        </text>
        <text
          x="26"
          y="77"
          text-anchor="end"
          font-size="7"
          fill="rgba(255,255,255,0.50)"
          font-family="system-ui,sans-serif"
        >
          0
        </text>
        <!-- Critical threshold at 90% (y≈14.6) -->
        <line
          x1="30"
          y1="15"
          x2="169"
          y2="15"
          stroke="rgb(248,113,113)"
          stroke-width="1"
          stroke-dasharray="4 3"
          opacity="0.75"
        />
        <text
          x="171"
          y="18"
          font-size="6"
          fill="rgb(248,113,113)"
          font-family="system-ui,sans-serif"
          opacity="0.85"
        >
          C
        </text>
        <!-- Warning threshold at 75% (y≈24.5) -->
        <line
          x1="30"
          y1="25"
          x2="169"
          y2="25"
          stroke="rgb(255,208,0)"
          stroke-width="1"
          stroke-dasharray="4 3"
          opacity="0.75"
        />
        <text
          x="171"
          y="28"
          font-size="6"
          fill="rgb(255,208,0)"
          font-family="system-ui,sans-serif"
          opacity="0.85"
        >
          W
        </text>
        <!-- Area fill (76%, jagged upward trend from ~42%) -->
        <path
          d="M 30,46 L 42,41 L 53,45 L 65,39 L 76,42 L 88,36 L 100,40 L 111,34 L 123,31 L 134,35 L 146,29 L 157,26 L 169,24 L 169,74 L 30,74 Z"
          fill="url(#cpu-grad)"
        />
        <!-- Line -->
        <polyline
          points="30,46 42,41 53,45 65,39 76,42 88,36 100,40 111,34 123,31 134,35 146,29 157,26 169,24"
          fill="none"
          stroke="rgb(245,158,11)"
          stroke-width="1.5"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <!-- Current value dot -->
        <circle cx="169" cy="24" r="3" fill="rgb(245,158,11)" class="pulse-dot" />
      </svg>
      <!-- Footer time labels -->
      <div class="graph-footer">
        <span class="graph-time">1h ago</span>
        <span class="graph-time">now</span>
      </div>
    </div>

    <!-- Monitoring objects -->
    <div
      v-for="(obj, i) in demoObjects"
      :key="obj.id"
      class="demo-object"
      :style="entryStyle(i, obj)"
    >
      <svg :width="SZ" :height="SZ" :class="glowClass(obj)">
        <circle :cx="SZ / 2" :cy="SZ / 2" :r="SZ / 2" :fill="STATE_RGB[obj.state]" />
        <text
          :x="SZ / 2"
          :y="SZ / 2"
          text-anchor="middle"
          dominant-baseline="central"
          fill="white"
          :font-size="SZ * 0.4"
          font-weight="700"
          font-family="system-ui, sans-serif"
          style="filter: drop-shadow(0 1px 2px rgb(0 0 0 / 50%))"
        >
          {{ TYPE_CHAR[obj.type] ?? '?' }}
        </text>
      </svg>
      <div class="object-label">
        {{ obj.name }}
      </div>
    </div>

    <!-- Floating "background.png" label -->
    <div class="bg-label">
      <div class="bg-label-chip">
        <svg class="bg-label-icon" viewBox="0 0 20 20" fill="currentColor">
          <path
            fill-rule="evenodd"
            d="M1 5.25A2.25 2.25 0 013.25 3h13.5A2.25 2.25 0 0119 5.25v9.5A2.25 2.25 0 0116.75 17H3.25A2.25 2.25 0 011 14.75v-9.5zm16.5 0a.75.75 0 00-.75-.75H3.25a.75.75 0 00-.75.75v6.268l3.162-3.162a.75.75 0 011.06 0l3.913 3.913 1.612-1.612a.75.75 0 011.06 0l3.693 3.693V5.25zm-2.47 9.25H3.25a.75.75 0 01-.75-.75v-.432l3.693-3.692 3.912 3.912a.75.75 0 001.06 0l1.612-1.612 3.223 3.224a.75.75 0 01-.72.34z"
            clip-rule="evenodd"
          />
        </svg>
        background.png
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

const SZ = 44
const PAD = 10

// ─── Locate canvas via DOM ────────────────────────────────────────────────────

const canvasRect = ref<DOMRect | null>(null)

function measureCanvas() {
  const el = document.querySelector('[data-tour="map-canvas"]')
  canvasRect.value = el ? el.getBoundingClientRect() : null
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  measureCanvas()
  resizeObserver = new ResizeObserver(measureCanvas)
  const el = document.querySelector('[data-tour="map-canvas"]')
  if (el) resizeObserver.observe(el)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

const canvasStyle = computed(() => {
  const r = canvasRect.value
  if (!r) return null
  return {
    top: `${Math.max(0, r.top - PAD)}px`,
    left: `${Math.max(0, r.left - PAD)}px`,
    width: `${r.width + PAD * 2}px`,
    height: `${r.height + PAD * 2}px`
  }
})

// ─── State colours ────────────────────────────────────────────────────────────

const STATE_RGB: Record<string, string> = {
  OK: 'rgb(74,222,128)',
  WARNING: 'rgb(255,208,0)',
  CRITICAL: 'rgb(248,113,113)',
  UNKNOWN: 'rgb(251,146,60)'
}

const TYPE_CHAR: Record<string, string> = {
  host: 'H',
  service: 'S',
  hostgroup: 'HG'
}

function glowClass(obj: DemoObj): string {
  return (
    { OK: 'glow-ok', WARNING: 'glow-warning', CRITICAL: 'glow-crit', UNKNOWN: 'glow-unknown' }[
      obj.state
    ] ?? ''
  )
}

// ─── Demo objects — positioned to match the Data Center background ────────────

interface DemoObj {
  id: string
  type: 'host' | 'service' | 'hostgroup'
  name: string
  state: string
  px: number // % of overlay width
  py: number // % of overlay height
}

const demoObjects: DemoObj[] = [
  { id: 'h1', type: 'host', name: 'web-server-01', state: 'OK', px: 22, py: 29 },
  { id: 's1', type: 'service', name: 'HTTP', state: 'WARNING', px: 70, py: 26 },
  { id: 'h2', type: 'host', name: 'db-server', state: 'CRITICAL', px: 34, py: 52 },
  { id: 'hg', type: 'hostgroup', name: 'Production', state: 'OK', px: 63, py: 53 },
  { id: 's2', type: 'service', name: 'backup', state: 'UNKNOWN', px: 80, py: 71 }
]

// ─── Position helpers ─────────────────────────────────────────────────────────

function px(pct: number): number {
  const r = canvasRect.value
  if (!r) return 0
  return (pct / 100) * (r.width + PAD * 2)
}

function py(pct: number): number {
  const r = canvasRect.value
  if (!r) return 0
  return (pct / 100) * (r.height + PAD * 2)
}

function entryStyle(index: number, obj: DemoObj) {
  return {
    left: `${px(obj.px)}px`,
    top: `${py(obj.py)}px`,
    transform: 'translate(-50%, -50%)',
    animation: `demo-fade-in 0.4s cubic-bezier(0.34,1.56,0.64,1) both ${index * 150}ms`
  }
}

// Graph positioned below the central server cluster
const graphStyle = computed(() => ({
  left: `${px(51)}px`,
  top: `${py(68)}px`,
  transform: 'translate(-50%, -50%)',
  animation: 'demo-fade-in 0.4s cubic-bezier(0.34,1.56,0.64,1) both 600ms'
}))
</script>

<style scoped>
.scene {
  position: fixed;
  overflow: hidden;
  pointer-events: none;
}

.lines-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.demo-object {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.object-label {
  margin-top: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: 10px;
  font-weight: 500;
  color: var(--color-white-100);
  white-space: nowrap;
  background: rgb(0 0 0 / 65%);
  border-radius: 4px;
}

/* ─── Entry animation ─────────────────────────────────────────────────────── */
@keyframes demo-fade-in {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.6);
  }

  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

/* ─── Background image ───────────────────────────────────────────────────── */
.bg-layer {
  position: absolute;
  inset: 0;
  background-image: url('/demo-bg.png');
  background-size: cover;
  background-position: top center;
  border-radius: 10px;
  opacity: 0;
  animation: bg-reveal 4s ease-in-out 0.5s infinite;
}

/* ─── Floating filename label ─────────────────────────────────────────────── */
.bg-label {
  position: absolute;
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  animation: bg-reveal 4s ease-in-out 0.5s infinite;
}

.bg-label-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
  color: var(--color-corporate-green-40);
  background: rgb(0 0 0 / 70%);
  border-radius: 8px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 40%, transparent);
}

.bg-label-icon {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
}

@keyframes bg-reveal {
  0% {
    opacity: 0;
  }

  20% {
    opacity: 1;
  }

  70% {
    opacity: 1;
  }

  100% {
    opacity: 0;
  }
}

/* ─── Graph object (mimics real graph object container) ──────────────────── */
.graph-gadget {
  position: absolute;
  background: rgb(9 9 11 / 90%);
  border: 1px solid rgb(255 255 255 / 10%);
  border-radius: 8px;
  overflow: hidden;
  padding: 6px 8px 5px;
  width: 195px;
}

.graph-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--dimension-3);
}

.graph-title {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.025em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.graph-value {
  font-size: 10px;
  font-weight: 700;
  color: var(--color-yellow-50);
}

.graph-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--dimension-2);
}

.graph-time {
  font-size: 7px;
  color: var(--text-muted);
}

.pulse-dot {
  animation: pulse-dot 1.2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%,
  100% {
    opacity: 1;
    r: 3;
  }

  50% {
    opacity: 0.4;
    r: 2;
  }
}

/* ─── Line flow animations ───────────────────────────────────────────────── */
.flow-line {
  stroke-dashoffset: 0;
  animation: flow 1.2s linear infinite;
}

.flow-line-slow {
  stroke-dashoffset: 0;
  animation: flow 2.2s linear infinite;
}

@keyframes flow {
  to {
    stroke-dashoffset: -24;
  }
}

/* ─── Glow pulses ─────────────────────────────────────────────────────────── */
.glow-ok {
  filter: drop-shadow(0 0 7px rgb(74 222 128 / 80%));
  animation: glow-ok-pulse 2.2s ease-in-out 1s infinite;
}

@keyframes glow-ok-pulse {
  0%,
  100% {
    filter: drop-shadow(0 0 7px rgb(74 222 128 / 80%));
  }

  50% {
    filter: drop-shadow(0 0 14px rgb(74 222 128 / 40%));
  }
}

.glow-warning {
  filter: drop-shadow(0 0 7px rgb(255 208 0 / 80%));
}

.glow-crit {
  filter: drop-shadow(0 0 8px rgb(248 113 113 / 90%));
  animation: glow-crit-pulse 1.2s ease-in-out 1s infinite;
}

@keyframes glow-crit-pulse {
  0%,
  100% {
    filter: drop-shadow(0 0 8px rgb(248 113 113 / 90%));
  }

  50% {
    filter: drop-shadow(0 0 4px rgb(248 113 113 / 40%));
  }
}

.glow-unknown {
  filter: drop-shadow(0 0 6px rgb(251 146 60 / 75%));
}
</style>
