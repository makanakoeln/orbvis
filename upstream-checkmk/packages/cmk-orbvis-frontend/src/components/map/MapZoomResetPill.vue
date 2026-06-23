<template>
  <Teleport to="body">
    <button
      v-if="visible"
      type="button"
      class="map-zoom-reset"
      :style="offset"
      title="Reset to fit"
      @click="$emit('reset')"
    >
      {{ Math.round(zoom * 100) }}% ↺
    </button>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  zoom: number
  visible: boolean
  offset?: { bottom?: string; left?: string }
}>()
defineEmits<{ reset: [] }>()
</script>

<style scoped>
.map-zoom-reset {
  position: fixed;
  bottom: var(--dimension-5);
  left: var(--dimension-5);
  z-index: 6;
  padding: 6px 14px;
  border-radius: var(--border-radius);
  background: var(--bg-glass);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  backdrop-filter: blur(6px);
}

.map-zoom-reset:hover {
  border-color: var(--color-corporate-green-50);
}
</style>
