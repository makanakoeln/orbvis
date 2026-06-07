<!--
OrbVis-native CmkSwitch, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script setup lang="ts">
const modelValue = defineModel({ type: Boolean, default: false })
</script>

<template>
  <label class="orb-switch">
    <input v-model="modelValue" type="checkbox" />
    <span class="orb-switch__slider"></span>
  </label>
</template>

<style scoped>
.orb-switch {
  position: relative;
  display: inline-block;
  width: 18px;
  height: 10px;
}

.orb-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.orb-switch__slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: var(--ux-theme-4, #4b5563);
  transition: background-color 0.2s ease;
  border-radius: 5px;
}

.orb-switch__slider::before {
  position: absolute;
  content: '';
  height: 8px;
  width: 8px;
  left: 1px;
  bottom: 1px;
  background-color: white;
  transition: transform 0.2s ease;
  border-radius: 50%;
}

input:checked + .orb-switch__slider {
  background-color: var(--color-corporate-green-50, #15d1a0);
}

input:checked + .orb-switch__slider::before {
  transform: translateX(8px);
}

input:focus + .orb-switch__slider {
  box-shadow: 0 0 0 2px
    color-mix(in srgb, var(--color-corporate-green-50, #15d1a0) 40%, transparent);
}
</style>
