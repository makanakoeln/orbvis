<template>
  <div v-if="canvasStyle" class="fixed pointer-events-none overflow-hidden" :style="canvasStyle">
    <!-- Background image fades in/out to illustrate a background being applied -->
    <div class="absolute inset-0 rounded-[10px] bg-layer" />

    <!-- Floating "background.png" label that appears with the background -->
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

    <!-- Demo monitoring objects (static states, no cycling) -->
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

const SZ = 48;
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

// ─── Demo objects (static states — no cycling, less distraction) ──────────────

interface DemoObj {
  id: string;
  type: 'host' | 'service' | 'hostgroup';
  name: string;
  state: string;
  px: number;
  py: number;
}

const demoObjects: DemoObj[] = [
  { id: 'h1', type: 'host', name: 'web-server-01', state: 'OK', px: 25, py: 32 },
  { id: 's1', type: 'service', name: 'HTTP', state: 'WARNING', px: 65, py: 32 },
  { id: 'h2', type: 'host', name: 'db-server', state: 'CRITICAL', px: 25, py: 68 },
  { id: 'hg', type: 'hostgroup', name: 'Production', state: 'OK', px: 65, py: 68 },
  { id: 's2', type: 'service', name: 'backup', state: 'UNKNOWN', px: 45, py: 50 },
];

// ─── Position helpers ─────────────────────────────────────────────────────────

function pxCoord(pct: number): number {
  const r = canvasRect.value;
  if (!r) return 0;
  return (pct / 100) * (r.width + PAD * 2);
}

function pyCoord(pct: number): number {
  const r = canvasRect.value;
  if (!r) return 0;
  return (pct / 100) * (r.height + PAD * 2);
}

function entryStyle(index: number, obj: DemoObj) {
  return {
    left: `${pxCoord(obj.px)}px`,
    top: `${pyCoord(obj.py)}px`,
    transform: 'translate(-50%, -50%)',
    animation: `demo-fade-in 0.4s cubic-bezier(0.34,1.56,0.64,1) both ${index * 180}ms`,
  };
}

// ─── Background label position ────────────────────────────────────────────────

const bgLabelStyle = computed(() => {
  const r = canvasRect.value;
  if (!r) return {};
  return {
    bottom: `${PAD + 20}px`,
    left: '50%',
    transform: 'translateX(-50%)',
  };
});
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

/* ─── Background image layer ─────────────────────────────────────────────── */
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
