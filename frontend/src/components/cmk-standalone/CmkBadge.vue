<!--
OrbVis-native CmkBadge, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script setup lang="ts">
export type Sizes = 'small' | 'medium' | 'large'
export type Colors = 'default' | 'success' | 'warning' | 'danger'
export type Types = 'fill' | 'outline'
export type Shapes = 'default' | 'circle'

export interface CmkBadgeProps {
  size?: Sizes
  color?: Colors
  type?: Types
  shape?: Shapes
}

withDefaults(defineProps<CmkBadgeProps>(), {
  size: 'medium',
  color: 'default',
  type: 'fill',
  shape: 'default'
})
</script>

<template>
  <div
    class="orb-badge"
    :class="[
      `orb-badge--size-${size}`,
      `orb-badge--color-${color}`,
      `orb-badge--type-${type}`,
      `orb-badge--shape-${shape}`
    ]"
  >
    <slot />
  </div>
</template>

<style scoped>
.orb-badge {
  border-radius: 99999px;
  border: 2px solid transparent;
  text-align: center;
  margin: 4px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
}

.orb-badge--size-small {
  font-size: 10px;
  min-width: 12px;
  height: 12px;
}

.orb-badge--size-medium {
  font-size: 12px;
  min-width: 18px;
  height: 18px;
}

.orb-badge--size-large {
  font-size: 14px;
  min-width: 24px;
  height: 24px;
}

.orb-badge--color-default {
  background: var(--ux-theme-4, #48566a);
  color: white;
}

.orb-badge--color-danger {
  background: var(--default-button-danger-color, #ef4444);
  color: white;
}

.orb-badge--color-warning {
  background: var(--color-warning, #ffd000);
  color: black;
}

.orb-badge--color-success {
  background: var(--color-corporate-green-50, #15d1a0);
  color: black;
}

.orb-badge--type-outline {
  background: transparent;
}

.orb-badge--type-outline.orb-badge--color-default {
  color: var(--ux-theme-4, #48566a);
  border-color: var(--ux-theme-4, #48566a);
}

.orb-badge--type-outline.orb-badge--color-warning {
  color: var(--color-warning, #ffd000);
  border-color: var(--color-warning, #ffd000);
}

.orb-badge--type-outline.orb-badge--color-danger {
  color: var(--default-button-danger-color, #ef4444);
  border-color: var(--default-button-danger-color, #ef4444);
}

.orb-badge--type-outline.orb-badge--color-success {
  color: var(--color-corporate-green-50, #15d1a0);
  border-color: var(--color-corporate-green-50, #15d1a0);
}

.orb-badge--shape-circle.orb-badge--size-small {
  max-width: 12px;
}

.orb-badge--shape-circle.orb-badge--size-medium {
  max-width: 18px;
}

.orb-badge--shape-circle.orb-badge--size-large {
  max-width: 24px;
}
</style>
