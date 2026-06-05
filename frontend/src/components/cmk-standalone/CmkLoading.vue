<!--
OrbVis-native CmkLoading, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script setup lang="ts">
import { computed } from 'vue'

interface CmkLoadingProps {
  height?: string
}
const props = withDefaults(defineProps<CmkLoadingProps>(), { height: '8px' })
const dotSize = computed(() => ({ width: props.height, height: props.height }))
</script>

<template>
  <div class="orb-loading">
    <div class="orb-loading__dot orb-loading__dot--1" :style="dotSize"></div>
    <div class="orb-loading__dot orb-loading__dot--2" :style="dotSize"></div>
    <div class="orb-loading__dot orb-loading__dot--3" :style="dotSize"></div>
  </div>
</template>

<style scoped>
.orb-loading {
  display: inline-flex;
  gap: 4px;
  align-items: center;
}

.orb-loading__dot {
  background-color: var(--color-corporate-green-50, #15d1a0);
  border-radius: 100%;
  display: inline-block;
  animation: orb-bounce 1.4s infinite ease-in-out both;
}

.orb-loading__dot--1 {
  animation-delay: -0.32s;
}

.orb-loading__dot--2 {
  animation-delay: -0.16s;
}

@keyframes orb-bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}
</style>
