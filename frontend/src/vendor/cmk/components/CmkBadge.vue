<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
defineProps<{
    size?: 'small' | 'medium' | 'large';
    color?: 'default' | 'success' | 'warning' | 'danger';
    type?: 'fill' | 'outline';
    shape?: 'default' | 'circle';
}>();
</script>

<template>
    <span
        class="cmk-badge"
        :class="[
            `cmk-badge--${size ?? 'medium'}`,
            `cmk-badge--${color ?? 'default'}`,
            `cmk-badge--${type ?? 'fill'}`,
            shape === 'circle' ? 'cmk-badge--circle' : '',
        ]"
    >
        <slot></slot>
    </span>
</template>

<style scoped>
.cmk-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    font-weight: 500;
    white-space: nowrap;
    border: 1px solid transparent;
}

/* Sizes */
.cmk-badge--small {
    font-size: 10px;
    padding: 1px 5px;
}
.cmk-badge--medium {
    font-size: 12px;
    padding: 2px 7px;
}
.cmk-badge--large {
    font-size: 13px;
    padding: 3px 9px;
}
.cmk-badge--circle {
    border-radius: 50%;
    padding: 2px 5px;
}

/* Fill colors */
.cmk-badge--fill.cmk-badge--default {
    background: var(--color-daylight-grey-60, #6b6b6b);
    color: #fff;
}
.cmk-badge--fill.cmk-badge--success {
    background: var(--color-corporate-green-50, #0f9b5e);
    color: #fff;
}
.cmk-badge--fill.cmk-badge--warning {
    background: #f59e0b;
    color: #fff;
}
.cmk-badge--fill.cmk-badge--danger {
    background: #ef4444;
    color: #fff;
}

/* Outline colors */
.cmk-badge--outline.cmk-badge--default {
    background: transparent;
    border-color: var(--color-daylight-grey-60, #6b6b6b);
    color: var(--color-daylight-grey-60, #6b6b6b);
}
.cmk-badge--outline.cmk-badge--success {
    background: transparent;
    border-color: var(--color-corporate-green-50, #0f9b5e);
    color: var(--color-corporate-green-50, #0f9b5e);
}
.cmk-badge--outline.cmk-badge--warning {
    background: transparent;
    border-color: #f59e0b;
    color: #f59e0b;
}
.cmk-badge--outline.cmk-badge--danger {
    background: transparent;
    border-color: #ef4444;
    color: #ef4444;
}
</style>
