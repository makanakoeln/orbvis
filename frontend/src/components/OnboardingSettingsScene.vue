<template>
  <div v-if="canvasStyle" class="fixed pointer-events-none overflow-hidden" :style="canvasStyle">
    <!-- Background image fades in/out -->
    <div class="absolute inset-0 rounded-[10px] bg-layer" />

    <!-- Connection lines (rendered below objects) -->
    <svg class="absolute inset-0 h-full w-full">
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

    <!-- Sparkline graph: CPU Load near db-server -->
    <div class="absolute graph-panel" :style="graphStyle">
      <div class="mb-1 flex items-center justify-between gap-3">
        <span class="text-[9px] font-semibold uppercase tracking-wide text-zinc-400">CPU Load</span>
        <span class="text-[10px] font-bold text-red-400">94%</span>
      </div>
      <svg width="110" height="36" class="overflow-visible">
        <!-- Area fill -->
        <defs>
          <linearGradient id="cpu-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="rgb(248,113,113)" stop-opacity="0.35" />
            <stop offset="100%" stop-color="rgb(248,113,113)" stop-opacity="0" />
          </linearGradient>
        </defs>
        <path
          d="M0,30 L9,26 L18,22 L27,18 L36,14 L45,10 L54,8 L63,6 L72,4 L81,3 L90,2 L99,1 L110,1 L110,36 L0,36 Z"
          fill="url(#cpu-grad)"
        />
        <!-- Line -->
        <polyline
          points="0,30 9,26 18,22 27,18 36,14 45,10 54,8 63,6 72,4 81,3 90,2 99,1 110,1"
          fill="none"
          stroke="rgb(248,113,113)"
          stroke-width="1.5"
          stroke-linejoin="round"
          stroke-linecap="round"
        />
        <!-- Current value dot -->
        <circle cx="110" cy="1" r="3" fill="rgb(248,113,113)" class="pulse-dot" />
      </svg>
    </div>

    <!-- Monitoring objects -->
    <div
      v-for="(obj, i) in demoObjects"
      :key="obj.id"
      class="absolute flex flex-col items-center"
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
      <div
        class="mt-1 whitespace-nowrap rounded bg-black/65 px-1.5 py-0.5 text-[10px] font-medium text-zinc-200"
      >
        {{ obj.name }}
      </div>
    </div>

    <!-- Floating "background.png" label -->
    <div class="absolute bg-label">
      <div
        class="flex items-center gap-1.5 rounded-lg bg-black/70 px-2.5 py-1.5 text-xs font-mono font-medium text-indigo-300 ring-1 ring-indigo-500/40"
      >
        <svg class="h-3 w-3 shrink-0" viewBox="0 0 20 20" fill="currentColor">
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
import { computed, onMounted, onUnmounted, ref } from 'vue';

const SZ = 44;
const PAD = 10;

// ─── Locate canvas via DOM ────────────────────────────────────────────────────

const canvasRect = ref<DOMRect | null>(null);

function measureCanvas() {
  const el = document.querySelector('[data-tour="board-canvas"]');
  canvasRect.value = el ? el.getBoundingClientRect() : null;
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  measureCanvas();
  resizeObserver = new ResizeObserver(measureCanvas);
  const el = document.querySelector('[data-tour="board-canvas"]');
  if (el) resizeObserver.observe(el);
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});

const canvasStyle = computed(() => {
  const r = canvasRect.value;
  if (!r) return null;
  return {
    top: `${Math.max(0, r.top - PAD)}px`,
    left: `${Math.max(0, r.left - PAD)}px`,
    width: `${r.width + PAD * 2}px`,
    height: `${r.height + PAD * 2}px`,
  };
});

// ─── State colours ────────────────────────────────────────────────────────────

const STATE_RGB: Record<string, string> = {
  OK: 'rgb(74,222,128)',
  WARNING: 'rgb(255,208,0)',
  CRITICAL: 'rgb(248,113,113)',
  UNKNOWN: 'rgb(251,146,60)',
};

const TYPE_CHAR: Record<string, string> = {
  host: 'H',
  service: 'S',
  hostgroup: 'HG',
};

function glowClass(obj: DemoObj): string {
  return (
    { OK: 'glow-ok', WARNING: 'glow-warning', CRITICAL: 'glow-crit', UNKNOWN: 'glow-unknown' }[
      obj.state
    ] ?? ''
  );
}

// ─── Demo objects — positioned to match the Data Center background ────────────

interface DemoObj {
  id: string;
  type: 'host' | 'service' | 'hostgroup';
  name: string;
  state: string;
  px: number; // % of overlay width
  py: number; // % of overlay height
}

const demoObjects: DemoObj[] = [
  { id: 'h1', type: 'host', name: 'web-server-01', state: 'OK', px: 22, py: 29 },
  { id: 's1', type: 'service', name: 'HTTP', state: 'WARNING', px: 70, py: 26 },
  { id: 'h2', type: 'host', name: 'db-server', state: 'CRITICAL', px: 34, py: 52 },
  { id: 'hg', type: 'hostgroup', name: 'Production', state: 'OK', px: 63, py: 53 },
  { id: 's2', type: 'service', name: 'backup', state: 'UNKNOWN', px: 80, py: 71 },
];

// ─── Position helpers ─────────────────────────────────────────────────────────

function px(pct: number): number {
  const r = canvasRect.value;
  if (!r) return 0;
  return (pct / 100) * (r.width + PAD * 2);
}

function py(pct: number): number {
  const r = canvasRect.value;
  if (!r) return 0;
  return (pct / 100) * (r.height + PAD * 2);
}

function entryStyle(index: number, obj: DemoObj) {
  return {
    left: `${px(obj.px)}px`,
    top: `${py(obj.py)}px`,
    transform: 'translate(-50%, -50%)',
    animation: `demo-fade-in 0.4s cubic-bezier(0.34,1.56,0.64,1) both ${index * 150}ms`,
  };
}

// Graph positioned between db-server and Production
const graphStyle = computed(() => ({
  left: `${px(43)}px`,
  top: `${py(60)}px`,
  transform: 'translate(-50%, -50%)',
  animation: 'demo-fade-in 0.4s cubic-bezier(0.34,1.56,0.64,1) both 600ms',
}));
</script>

<style scoped>
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
  background-image: url('/demo-bg.png');
  background-size: cover;
  background-position: center;
  opacity: 0;
  animation: bg-reveal 4s ease-in-out 0.5s infinite;
}

/* ─── Floating filename label ─────────────────────────────────────────────── */
.bg-label {
  bottom: 28px;
  left: 50%;
  transform: translateX(-50%);
  opacity: 0;
  animation: bg-reveal 4s ease-in-out 0.5s infinite;
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

/* ─── Sparkline graph panel ──────────────────────────────────────────────── */
.graph-panel {
  background: rgb(0 0 0 / 70%);
  border: 1px solid rgb(248 113 113 / 30%);
  border-radius: 8px;
  padding: 6px 8px;
  width: 130px;
  backdrop-filter: blur(4px);
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
