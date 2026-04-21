<template>
  <span class="cmk-icon" :data-icon="name" :data-size="size" />
</template>

<script setup lang="ts">
defineProps<{ name?: string; size?: string }>();
</script>
