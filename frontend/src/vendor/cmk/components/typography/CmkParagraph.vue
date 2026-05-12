<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
Vendored from cmk-frontend-vue.
-->
<script setup lang="ts"></script>

<template>
    <p class="cmk-paragraph">
        <slot />
    </p>
</template>

<style scoped>
.cmk-paragraph {
    font-size: var(--font-size-normal);
    font-weight: var(--font-weight-default);
    color: var(--font-color);
    margin: 0;
    line-height: normal;
    letter-spacing: 0.36px;
}
</style>
