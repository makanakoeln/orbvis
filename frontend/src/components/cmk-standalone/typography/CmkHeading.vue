<!--
OrbVis-native CmkHeading, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script setup lang="ts">
export type HeadingType = 'h1' | 'h2' | 'h3' | 'h4'

export interface CmkHeadingProps {
  type?: HeadingType
  onClick?: (() => void) | null
}

withDefaults(defineProps<CmkHeadingProps>(), { type: 'h1' })
</script>

<template>
  <component
    :is="type || 'h1'"
    class="orb-heading"
    :class="[`orb-heading--${type || 'h1'}`, { 'orb-heading--clickable': !!onClick }]"
    @click="onClick"
  >
    <slot />
  </component>
</template>

<style scoped>
.orb-heading {
  font-weight: var(--font-weight-bold, 700);
  color: var(--font-color, #f4f4f5);
  margin: 0;
}

.orb-heading--h1 {
  font-size: var(--font-size-xxlarge, 18px);
}

.orb-heading--h2 {
  font-size: var(--font-size-xlarge, 15px);
}

.orb-heading--h3 {
  font-size: var(--font-size-large, 14px);
}

.orb-heading--h4 {
  font-size: var(--font-size-normal, 13px);
}

.orb-heading--clickable {
  cursor: pointer;
}
</style>
