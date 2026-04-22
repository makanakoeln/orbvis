<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
  open: boolean;
  contentId?: string;
}>();
</script>

<template>
  <div :id="contentId" class="cmk-collapsible" :class="{ 'cmk-collapsible--open': open }">
    <slot></slot>
  </div>
</template>

<style scoped>
.cmk-collapsible {
  display: grid !important;
  grid-template-rows: 0fr;
  overflow: hidden;
  transition: grid-template-rows 200ms ease;
}

.cmk-collapsible--open {
  grid-template-rows: 1fr;
}

.cmk-collapsible > :deep(*) {
  min-height: 0;
}
</style>
