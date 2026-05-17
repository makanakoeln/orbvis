<!--
OrbVis-native CmkScrollContainer, swapped in for the vendored variant
when VITE_BUILD_TARGET=standalone.
-->
<script setup lang="ts">
export interface ScrollContainerProps {
    maxHeight?: string;
    height?: string;
    type?: 'inner' | 'outer';
}
const { type = 'inner', maxHeight = '100%', height = '100%' } = defineProps<ScrollContainerProps>();
</script>

<template>
    <div
        :style="{ maxHeight, height, overflow: 'auto' }"
        :class="{ 'orb-scroll--outer': type === 'outer' }"
    >
        <slot />
    </div>
</template>

<style scoped>
.orb-scroll--outer::-webkit-scrollbar {
    width: 10px;
}

.orb-scroll--outer::-webkit-scrollbar-track {
    background: transparent;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}

.orb-scroll--outer::-webkit-scrollbar-thumb {
    background-color: var(--scrollbar-color, #52525b);
    border-radius: 16px;
    border: 3px solid transparent;
    background-clip: content-box;
    width: 8px;
}
</style>
