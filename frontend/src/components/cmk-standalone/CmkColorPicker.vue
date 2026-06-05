<!--
OrbVis-native CmkColorPicker, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone.
-->
<script setup lang="ts">
const data = defineModel('data', { type: String, default: '#ff0000' })
</script>

<template>
  <input v-model="data" class="orb-color-picker" type="color" />
</template>

<style scoped>
.orb-color-picker {
  margin-right: 10px;
  width: 26px;
  height: 30px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
}
</style>
