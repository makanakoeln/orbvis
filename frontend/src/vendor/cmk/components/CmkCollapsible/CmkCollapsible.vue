<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';

const props = defineProps<{
    open: boolean;
    contentId?: string;
}>();

const innerOverflow = ref<'hidden' | 'visible'>(props.open ? 'visible' : 'hidden');
let timer: ReturnType<typeof setTimeout> | null = null;

watch(
    () => props.open,
    (val) => {
        if (timer) clearTimeout(timer);
        if (val) {
            timer = setTimeout(() => {
                innerOverflow.value = 'visible';
            }, 210);
        } else {
            innerOverflow.value = 'hidden';
        }
    },
);

onBeforeUnmount(() => {
    if (timer) clearTimeout(timer);
});
</script>

<template>
    <div :id="contentId" class="cmk-collapsible" :class="{ 'cmk-collapsible--open': open }">
        <div class="cmk-collapsible__inner" :style="{ overflow: innerOverflow }">
            <slot></slot>
        </div>
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

.cmk-collapsible__inner {
    min-height: 0;
    overflow: hidden;
}
</style>
