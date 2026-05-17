<!--
OrbVis-native CmkParagraph, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<template>
    <p class="orb-paragraph">
        <slot />
    </p>
</template>

<style scoped>
.orb-paragraph {
    font-size: var(--font-size-normal, 13px);
    font-weight: var(--font-weight-default, 400);
    color: var(--font-color, #f4f4f5);
    margin: 0;
    line-height: normal;
    letter-spacing: 0.36px;
}
</style>
