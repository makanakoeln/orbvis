<!--
OrbVis-native CmkHelpText, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).

Renders a hover-tooltip via the native browser title attribute instead
of the upstream reka-ui popover stack; sufficient for OrbVis surfaces
which mostly need short hint text.
-->
<script setup lang="ts">
defineOptions({ inheritAttrs: false });

defineProps<{
    help: string;
    ariaLabel?: string | undefined;
}>();
</script>

<template>
    <span v-if="help" class="orb-help-text" :title="help" :aria-label="ariaLabel || '?'">?</span>
</template>

<style scoped>
.orb-help-text {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--ux-theme-4, #4b5563);
    color: var(--font-color, #f4f4f5);
    font-size: 10px;
    font-weight: 700;
    cursor: help;
    vertical-align: middle;
    user-select: none;
}
</style>
