<template>
  <div class="fixed pointer-events-none overflow-hidden" :style="overlayStyle">
    <!-- Backdrop so demo objects are readable over any existing board content -->
    <div class="absolute inset-0 bg-black/55 rounded-[10px]" />

    <!-- Connection lines -->
    <svg class="absolute inset-0 w-full h-full">
      <line
        class="flow-line"
        :x1="px(25)"
        :y1="py(30)"
        :x2="px(65)"
        :y2="py(30)"
        stroke="rgb(74,222,128)"
        stroke-width="2"
        stroke-dasharray="8 4"
      />
      <line
        class="flow-line-slow"
        :x1="px(25)"
        :y1="py(65)"
        :x2="px(65)"
        :y2="py(65)"
        stroke="rgb(248,113,113)"
        stroke-width="2"
        stroke-dasharray="8 4"
      />
    </svg>

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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

const props = defineProps<{
  canvasRect: DOMRect;
}>();

const SZ = 48;
const PAD = 10;

const overlayStyle = computed(() => ({
  top: `${Math.max(0, props.canvasRect.top - PAD)}px`,
  left: `${Math.max(0, props.canvasRect.left - PAD)}px`,
  width: `${props.canvasRect.width + PAD * 2}px`,
  height: `${props.canvasRect.height + PAD * 2}px`,
}));

// ─── State colours ────────────────────────────────────────────────────────

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

// ─── Demo objects ─────────────────────────────────────────────────────────

interface DemoObj {
  id: string;
  type: 'host' | 'service' | 'hostgroup';
  name: string;
  state: string;
  px: number; // percent of canvas width
  py: number; // percent of canvas height
}

const cycleState = ref<'WARNING' | 'CRITICAL'>('WARNING');

const demoObjects = computed<DemoObj[]>(() => [
  { id: 'h1', type: 'host', name: 'web-server-01', state: 'OK', px: 25, py: 32 },
  { id: 's1', type: 'service', name: 'HTTP', state: cycleState.value, px: 65, py: 32 },
  { id: 'h2', type: 'host', name: 'db-server', state: 'CRITICAL', px: 25, py: 68 },
  { id: 'hg', type: 'hostgroup', name: 'Production', state: 'OK', px: 65, py: 68 },
  { id: 's2', type: 'service', name: 'backup', state: 'UNKNOWN', px: 45, py: 50 },
]);

let cycleTimer: ReturnType<typeof setInterval> | null = null;
onMounted(() => {
  cycleTimer = setInterval(() => {
    cycleState.value = cycleState.value === 'WARNING' ? 'CRITICAL' : 'WARNING';
  }, 2500);
});
onUnmounted(() => {
  if (cycleTimer !== null) clearInterval(cycleTimer);
});

// ─── Position helpers ─────────────────────────────────────────────────────

function px(pct: number): number {
  return (pct / 100) * (props.canvasRect.width + PAD * 2);
}
function py(pct: number): number {
  return (pct / 100) * (props.canvasRect.height + PAD * 2);
}

function entryStyle(index: number, obj: DemoObj) {
  return {
    left: `${px(obj.px)}px`,
    top: `${py(obj.py)}px`,
    transform: 'translate(-50%, -50%)',
    animationDelay: `${index * 180}ms`,
    animation: `demo-fade-in 0.4s cubic-bezier(0.34,1.56,0.64,1) both ${index * 180}ms`,
  };
}
</script>

<style scoped>
/* ─── Entry animation ────────────────────────────────────────────────────── */
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

/* ─── Glow pulses ────────────────────────────────────────────────────────── */
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
  animation: glow-warning-pulse 2.5s ease-in-out 0.8s infinite;
}

@keyframes glow-warning-pulse {
  0%,
  100% {
    filter: drop-shadow(0 0 7px rgb(255 208 0 / 80%));
  }

  50% {
    filter: drop-shadow(0 0 14px rgb(255 208 0 / 30%));
  }
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

/* ─── Line flow animations ───────────────────────────────────────────────── */
.flow-line {
  stroke-dashoffset: 0;
  animation: flow 1.2s linear infinite;
}

.flow-line-slow {
  stroke-dashoffset: 0;
  animation: flow 2s linear infinite;
}

@keyframes flow {
  to {
    stroke-dashoffset: -24;
  }
}
</style>
