<template>
  <div class="pco">
    <div
      v-for="slot in slots"
      :key="slot.id"
      class="pco__slot"
      :class="{
        'pco__slot--current': slot.id === currentId,
        'pco__slot--bound': slot.bound
      }"
      :style="slotStyle(slot)"
      @pointerdown.stop="!slot.bound && emit('pick', slot.id)"
    >
      <span
        class="pco__badge"
        :class="{
          'pco__badge--bound': slot.bound,
          'pco__badge--current': slot.id === currentId && !slot.bound
        }"
        :style="badgeStyle"
      >
        {{ slot.bound ? '✓' : slot.n }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface ConnectSlotBox {
  id: string
  x: number
  y: number
  w: number
  h: number
  // Stable session number — binding a slot must not renumber the others.
  n: number
  bound: boolean
}

const props = defineProps<{
  // Pre-resolved on-slide bounds (a connector's box spans its endpoints).
  slots: ConnectSlotBox[]
  currentId: string | null
  scale: number
}>()

const emit = defineEmits<{ pick: [string] }>()

// Slide-space overlay: outlines hug the slot's box; chrome (border, badge) is
// divided by the zoom factor so it keeps a constant on-screen size.
function slotStyle(box: ConnectSlotBox): Record<string, string> {
  return {
    left: `${box.x}px`,
    top: `${box.y}px`,
    width: `${box.w}px`,
    height: `${box.h}px`,
    borderWidth: `${2 / props.scale}px`,
    borderRadius: `${10 / props.scale}px`
  }
}

const badgeStyle = computed(() => ({
  width: `${26 / props.scale}px`,
  height: `${26 / props.scale}px`,
  fontSize: `${13 / props.scale}px`,
  top: `${-12 / props.scale}px`,
  left: `${-12 / props.scale}px`,
  borderWidth: `${2 / props.scale}px`
}))
</script>

<style scoped>
.pco {
  position: absolute;
  inset: 0;
  z-index: 1002;
  pointer-events: none;
}

.pco__slot {
  position: absolute;
  border-style: dashed;

  /* Waiting slots recede so the eye lands on the one current slot. */
  border-color: color-mix(in srgb, var(--pres-accent, #38bdf8) 45%, transparent);
  cursor: pointer;
  pointer-events: auto;
  transition:
    border-color 0.15s ease,
    background 0.15s ease;
}

.pco__slot--bound {
  border-color: color-mix(in srgb, var(--pres-accent, #38bdf8) 30%, transparent);
  cursor: default;
}

/* The current slot reads as "fill me now": solid border + accent tint, kept
   distinct without motion so it still stands out under prefers-reduced-motion. */
.pco__slot--current {
  border-style: solid;
  border-color: var(--pres-accent, #38bdf8);
  background: color-mix(in srgb, var(--pres-accent, #38bdf8) 14%, transparent);
  animation: pco-pulse 1.4s ease-in-out infinite;
}

@keyframes pco-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--pres-accent, #38bdf8) 70%, transparent);
  }

  50% {
    box-shadow: 0 0 0 12px color-mix(in srgb, var(--pres-accent, #38bdf8) 0%, transparent);
  }
}

@media (prefers-reduced-motion: reduce) {
  .pco__slot--current {
    animation: none;
  }
}

.pco__badge {
  position: absolute;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-style: solid;
  border-color: var(--pres-bg, #0b1020);
  border-radius: 9999px;
  background: var(--pres-accent, #38bdf8);
  color: var(--pres-bg, #0b1020);
  font-weight: 700;
}

.pco__badge--bound {
  background: #22c55e;
}

/* Lift the current slot's number off the muted ones with a contrasting ring. */
.pco__badge--current {
  box-shadow: 0 0 0 2px var(--pres-bg, #0b1020);
  outline: 2px solid var(--pres-accent, #38bdf8);
}
</style>
