<template>
  <div class="pco">
    <div
      v-for="(slot, i) in slots"
      :key="slot.id"
      class="pco__slot"
      :class="{ 'pco__slot--current': slot.id === currentId }"
      :style="slotStyle(slot)"
      @pointerdown.stop="emit('pick', slot.id)"
    >
      <span class="pco__badge" :style="badgeStyle">{{ i + 1 }}</span>
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
  border-color: var(--pres-accent, #38bdf8);
  cursor: pointer;
  pointer-events: auto;
}

.pco__slot--current {
  animation: pco-pulse 1.4s ease-in-out infinite;
}

@keyframes pco-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--pres-accent, #38bdf8) 55%, transparent);
  }

  50% {
    box-shadow: 0 0 0 10px color-mix(in srgb, var(--pres-accent, #38bdf8) 0%, transparent);
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
</style>
