<!--
OrbVis-native CmkHelpText, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).

Renders a hover-tooltip via the native browser title attribute instead
of the upstream reka-ui popover stack; sufficient for OrbVis surfaces
which mostly need short hint text.
-->
<script setup lang="ts">
defineOptions({ inheritAttrs: false })

defineProps<{
  help: string
  ariaLabel?: string | undefined
}>()
</script>

<template>
  <span
    v-if="help"
    class="orb-help-text"
    :title="help"
    :aria-label="ariaLabel || 'More information'"
  >
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="12" x2="12" y2="16" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  </span>
</template>

<style scoped>
.orb-help-text {
  display: inline-flex;
  align-items: center;
  color: var(--font-color-dimmed, #9ca3af);
  cursor: help;
  vertical-align: middle;
  transition: color 120ms ease;
}

.orb-help-text:hover {
  color: var(--font-color, #f4f4f5);
}

.orb-help-text svg {
  width: 12px;
  height: 12px;
}
</style>
