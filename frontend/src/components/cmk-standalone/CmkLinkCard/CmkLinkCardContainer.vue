<!--
OrbVis-native CmkLinkCardContainer, swapped in for the vendored variant
when VITE_BUILD_TARGET=standalone.
-->
<script setup lang="ts">
interface CmkLinkCardContainerProps {
    orientation?: 'vertical' | 'horizontal';
}
withDefaults(defineProps<CmkLinkCardContainerProps>(), { orientation: 'vertical' });
</script>

<template>
    <div class="orb-link-card-container" :class="`orb-link-card-container--${orientation}`">
        <slot />
    </div>
</template>

<style scoped>
.orb-link-card-container {
    display: flex;
    gap: 8px;
    flex-direction: column;
}

.orb-link-card-container--horizontal {
    flex-direction: row;
}
</style>
