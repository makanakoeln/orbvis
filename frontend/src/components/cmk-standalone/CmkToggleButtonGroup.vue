<!--
OrbVis-native CmkToggleButtonGroup, swapped in for the vendored variant
when VITE_BUILD_TARGET=standalone.
-->
<script setup lang="ts">
export type ToggleButtonOption = {
    label: string;
    value: string;
    tooltip?: string | undefined;
    disabled?: boolean | string | undefined;
    disabledTooltip?: string | undefined;
};

export interface ToggleButtonGroupProps {
    options: ToggleButtonOption[];
    modelValue?: string | null;
}

const props = defineProps<ToggleButtonGroupProps>();
const emit = defineEmits({ 'update:modelValue': (_value: string) => true });

const isSelected = (value: string) => props.modelValue !== null && value === props.modelValue;
const isDisabled = (d: boolean | string | undefined) => d === true || d === 'true';
</script>

<template>
    <div class="orb-toggle-group">
        <button
            v-for="option in options"
            :key="option.value"
            type="button"
            class="orb-toggle-group__option"
            :class="{
                'orb-toggle-group__option--selected': isSelected(option.value),
                'orb-toggle-group__option--disabled': isDisabled(option.disabled),
            }"
            :aria-label="`Toggle ${option.label}`"
            :disabled="isDisabled(option.disabled)"
            :title="isDisabled(option.disabled) ? option.disabledTooltip : option.tooltip"
            @click.prevent="emit('update:modelValue', option.value)"
        >
            {{ option.label }}
        </button>
    </div>
</template>

<style scoped>
.orb-toggle-group {
    width: max-content;
    max-width: 100%;
    margin-bottom: 8px;
    padding: 5px;
    border-radius: 5px;
    border: 1px solid var(--toggle-button-group-border-color, var(--ux-theme-7, #48566a));
    background-color: var(--toggle-button-group-inactive-bg-color, var(--ux-theme-6, #252c36));
    display: flex;
    flex-wrap: wrap;
}

.orb-toggle-group__option {
    height: auto;
    min-width: 150px;
    border: none;
    background-color: var(--toggle-button-group-inactive-bg-color, var(--ux-theme-6, #252c36));
    color: var(--toggle-button-group-inactive-text-color, rgb(160 168 176));
    margin: 0 2px;
    padding: 3px;
    font-weight: var(--font-weight-default, 400);
    cursor: pointer;
    border-radius: 4px;
}

.orb-toggle-group__option--selected {
    border: 1px solid var(--toggle-button-group-border-color, var(--ux-theme-7, #48566a));
    background-color: var(--toggle-button-group-active-bg-color, var(--ux-theme-10, #6a7c95));
    color: var(--toggle-button-group-active-text-color, white);
    font-weight: var(--font-weight-bold, 700);
}

.orb-toggle-group__option--disabled {
    color: var(--toggle-button-group-disabled-text-color, rgb(80 88 96));
    cursor: not-allowed;
}

.orb-toggle-group__option:hover:not(
        .orb-toggle-group__option--selected,
        .orb-toggle-group__option--disabled
    ) {
    background-color: color-mix(
        in srgb,
        var(--toggle-button-group-hover-bg-color, var(--ux-theme-7, #48566a)) 60%,
        transparent
    );
}
</style>
