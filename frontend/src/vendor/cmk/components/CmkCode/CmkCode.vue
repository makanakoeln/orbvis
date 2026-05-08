<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, ref } from 'vue';

const props = defineProps<{
    codeTxt: string;
    width?: 'default' | 'fill';
}>();

const MAX_LINES = 10;
const isExpanded = ref(false);

const codeLines = computed(() => props.codeTxt.split('\n'));
const displayedCode = computed(() => {
    if (isExpanded.value || codeLines.value.length <= MAX_LINES) return props.codeTxt;
    return codeLines.value.slice(0, MAX_LINES).join('\n');
});
const shouldShowToggle = computed(() => codeLines.value.length > MAX_LINES);

function toggleExpansion(): void {
    isExpanded.value = !isExpanded.value;
}
</script>

<template>
    <div class="code-wrapper">
        <div
            class="code-container"
            :class="{
                'has-toggle': shouldShowToggle,
                expanded: isExpanded,
                'cmk-code--is-wide': width === 'fill',
            }"
        >
            <pre><code v-text="displayedCode" /></pre>
            <div v-if="shouldShowToggle && !isExpanded" class="fade-overlay" />
            <div v-if="shouldShowToggle" class="toggle-button-container">
                <button type="button" class="toggle-button" @click="toggleExpansion">
                    {{ isExpanded ? '−' : '+' }}
                </button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.code-wrapper {
    display: flex;
    align-items: flex-start;
    margin: var(--spacing, 4px) 0;
    max-width: 100%;
    min-width: 0;
}

.code-container {
    position: relative;
    font-family: var(--font-mono, monospace);
    font-size: var(--font-size-normal, 12px);
    font-style: normal;
    font-weight: 400;
    line-height: normal;
    padding: var(--dimension-3, 6px) var(--dimension-4, 8px);
    color: var(--font-color, var(--text));
    border-radius: var(--border-radius);
    border: 1px solid var(--code-background-color, var(--border));
    background: var(--code-background-color, var(--bg));
    max-width: 100%;
    min-width: 0;
    overflow-x: auto;

    &.cmk-code--is-wide {
        width: 100%;
    }

    pre {
        margin: 0;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }

    .fade-overlay {
        position: absolute;
        bottom: 24px;
        left: 0;
        right: 0;
        height: 30px;
        background: linear-gradient(transparent, var(--code-background-color, var(--bg)));
        pointer-events: none;
    }

    .toggle-button-container {
        position: absolute;
        bottom: 4px;
        right: 4px;
    }

    .toggle-button {
        font-size: 10px;
        font-family: var(--font-mono, monospace);
        padding: 1px 6px;
        border: 1px solid var(--font-color, var(--text));
        background: var(--code-background-color, var(--bg));
        color: var(--font-color, var(--text));
        border-radius: var(--border-radius);
        cursor: pointer;
        line-height: 1;
    }
}
</style>
