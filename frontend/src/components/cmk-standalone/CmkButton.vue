<!--
OrbVis-native CmkButton, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script lang="ts">
export interface ButtonProps {
    variant?: 'primary' | 'secondary' | 'optional' | 'success' | 'warning' | 'danger' | 'info';
    disabled?: boolean | string | undefined;
    title?: string | undefined;
    href?: string | undefined;
    target?: string | undefined;
}
</script>

<script setup lang="ts">
import { computed, ref } from 'vue';

const buttonRef = ref<HTMLButtonElement | HTMLAnchorElement | null>(null);

defineExpose({
    focus: () => buttonRef.value?.focus(),
});

const props = withDefaults(defineProps<ButtonProps>(), { variant: 'optional' });
defineEmits(['click']);

const isDisabled = computed(() => props.disabled === true || props.disabled === 'true');
const isLink = computed(() => props.href !== undefined);
const variantClass = computed(() => `orb-button--${props.variant}`);
</script>

<template>
    <a
        v-if="isLink"
        ref="buttonRef"
        class="orb-button"
        :class="[variantClass, { 'orb-button--disabled': isDisabled }]"
        :href="isDisabled ? undefined : props.href"
        :target="props.target"
        :title="title || ''"
        @click="
            (e) => {
                if (isDisabled) {
                    e.preventDefault();
                    return;
                }
                $emit('click', e);
            }
        "
    >
        <slot />
    </a>
    <button
        v-else
        ref="buttonRef"
        type="button"
        class="orb-button"
        :class="[variantClass, { 'orb-button--disabled': isDisabled }]"
        :disabled="isDisabled"
        :aria-disabled="isDisabled"
        :title="title || ''"
        @click.prevent="(e) => $emit('click', e)"
    >
        <slot />
    </button>
</template>

<style scoped>
.orb-button {
    display: inline-flex;
    height: 24px;
    margin: 0;
    padding: 0 10px;
    align-items: center;
    justify-content: center;
    letter-spacing: unset;
    border-radius: 4px;
    font-weight: 700;
    font-size: 13px;
    text-decoration: none;
    cursor: pointer;
    box-sizing: border-box;
    transition: background-color 120ms ease;
}

.orb-button--primary,
.orb-button--success {
    color: var(--button-primary-text-color, #000);
    background-color: var(--default-button-primary-color, #15d1a0);
    border: 1px solid var(--button-primary-border-color, #15d1a0);
}

.orb-button--primary:hover:not(.orb-button--disabled),
.orb-button--success:hover:not(.orb-button--disabled) {
    background-color: color-mix(
        in srgb,
        var(--default-button-primary-color, #15d1a0) 80%,
        #fff 20%
    );
}

.orb-button--danger {
    color: var(--button-danger-text-color, #fff);
    background-color: var(--default-button-danger-color, #e53f3f);
    border: 1px solid var(--button-danger-border-color, #e53f3f);
}

.orb-button--danger:hover:not(.orb-button--disabled) {
    background-color: color-mix(in srgb, var(--default-button-danger-color, #e53f3f) 85%, #fff 15%);
}

.orb-button--warning {
    color: var(--button-warning-text-color, black);
    background-color: var(--color-warning, #ffd000);
    border: 1px solid var(--color-warning, #ffd000);
}

.orb-button--warning:hover:not(.orb-button--disabled) {
    background-color: color-mix(in srgb, var(--color-warning, #ffd000) 80%, #fff 20%);
}

.orb-button--secondary,
.orb-button--optional,
.orb-button--info {
    color: var(--text, #f4f4f5);
    background-color: var(--bg-hover, rgb(255 255 255 / 8%));
    border: 1px solid var(--default-form-element-border-color, var(--ux-theme-4, #4b5563));
}

.orb-button--secondary:hover:not(.orb-button--disabled),
.orb-button--optional:hover:not(.orb-button--disabled),
.orb-button--info:hover:not(.orb-button--disabled) {
    background-color: var(--bg-glass, rgb(255 255 255 / 14%));
}

.orb-button--disabled,
button.orb-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    filter: none;
}

.orb-button:focus-visible {
    outline: 2px solid var(--color-corporate-green-50, #15d1a0);
    outline-offset: 2px;
}
</style>
