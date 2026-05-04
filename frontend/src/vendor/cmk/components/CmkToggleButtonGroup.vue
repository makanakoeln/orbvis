<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
interface ToggleButtonOption {
    label: string;
    value: string;
    disabled?: boolean | string;
}

const props = defineProps<{
    options: ToggleButtonOption[];
    modelValue?: string | null;
}>();

const emit = defineEmits<{
    'update:modelValue': [value: string];
}>();

function select(value: string) {
    emit('update:modelValue', value);
}

function isDisabled(option: ToggleButtonOption): boolean {
    return option.disabled === true || typeof option.disabled === 'string';
}
</script>

<template>
    <div class="cmk-toggle-button-group" role="group">
        <button
            v-for="option in options"
            :key="option.value"
            type="button"
            class="cmk-toggle-button"
            :class="{ 'cmk-toggle-button--active': props.modelValue === option.value }"
            :disabled="isDisabled(option)"
            @click="select(option.value)"
        >
            {{ option.label }}
        </button>
    </div>
</template>

<style scoped>
.cmk-toggle-button-group {
    display: inline-flex !important;
    width: auto !important;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid var(--border, #3a3a3a);
}

.cmk-toggle-button {
    flex: none !important;
    padding: 4px 10px;
    font-size: 12px;
    line-height: 1.5;
    background: transparent;
    color: var(--text, #ccc);
    border: none;
    border-left: 1px solid var(--border, #3a3a3a);
    cursor: pointer;
    transition:
        background 150ms,
        color 150ms;
}

.cmk-toggle-button:first-child {
    border-left: none;
}

.cmk-toggle-button:hover:not(:disabled) {
    background: var(--bg-hover, rgba(255, 255, 255, 0.06));
}

.cmk-toggle-button--active {
    background: var(--color-corporate-green-50, #0f9b5e);
    color: #fff;
}

.cmk-toggle-button--active:hover:not(:disabled) {
    background: var(--color-corporate-green-50, #0f9b5e);
}

.cmk-toggle-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
</style>
