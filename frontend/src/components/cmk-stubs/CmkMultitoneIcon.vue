<template>
    <span class="cmk-multitone-icon" :data-icon="name" :data-size="size" />
</template>

<script setup lang="ts">
defineProps<{ name?: string; size?: string; primaryColor?: string }>();
</script>
