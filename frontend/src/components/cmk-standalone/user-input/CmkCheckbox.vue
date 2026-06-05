<!--
OrbVis-native CmkCheckbox, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone (see vite.config.ts STANDALONE_OVERRIDES).
-->
<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from 'reka-ui'
import { computed, useId } from 'vue'

defineOptions({ inheritAttrs: false })

const value = defineModel<boolean>({ required: false, default: false })

interface CmkCheckboxProps {
  label?: string
  padding?: 'top' | 'bottom' | 'both'
  help?: string
  externalErrors?: string[]
  disabled?: boolean
  dots?: boolean
}

const {
  padding = 'both',
  label,
  disabled = false,
  externalErrors
} = defineProps<CmkCheckboxProps>()

const id = useId()
const hasError = computed(() => !!externalErrors?.length)
</script>

<template>
  <span class="orb-checkbox" v-bind="$attrs">
    <div
      class="orb-checkbox__row"
      :class="{
        'orb-checkbox__row--pad-top': padding !== 'bottom',
        'orb-checkbox__row--pad-bottom': padding !== 'top',
        'orb-checkbox__row--disabled': disabled
      }"
    >
      <CheckboxRoot
        :id="id"
        v-model="value"
        class="orb-checkbox__button"
        :class="{ 'orb-checkbox__button--error': hasError }"
        :disabled="disabled"
      >
        <CheckboxIndicator class="orb-checkbox__indicator">
          <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
            <g transform="rotate(45,9,9)">
              <path d="m18.5 6.5v5h-7v7h-5v-7h-7v-5h7v-7h5v7z" fill="currentcolor" />
            </g>
          </svg>
        </CheckboxIndicator>
      </CheckboxRoot>
      <label v-if="label" :for="id" class="orb-checkbox__label">{{ label }}</label>
      <span v-if="help" class="orb-checkbox__help" :title="help" aria-label="More information">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="12" x2="12" y2="16" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
      </span>
    </div>
    <ul v-if="hasError" class="orb-checkbox__errors">
      <li v-for="(msg, idx) in externalErrors" :key="idx">{{ msg }}</li>
    </ul>
  </span>
</template>

<style scoped>
.orb-checkbox {
  max-width: 100%;
  display: inline-block;
  vertical-align: middle;
}

.orb-checkbox__row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.orb-checkbox__row--pad-top {
  padding-top: 2px;
}

.orb-checkbox__row--pad-bottom {
  padding-bottom: 2px;
}

.orb-checkbox__row--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.orb-checkbox__button {
  background-color: var(--default-form-element-bg-color, #27272a);
  border: 1px solid var(--default-form-element-border-color, #71717a);
  border-radius: 2px;
  height: 15px;
  width: 15px;
  min-width: 15px;
  min-height: 15px;
  padding: 0;
  margin: 0;
  vertical-align: middle;
  cursor: pointer;
}

.orb-checkbox__row--disabled .orb-checkbox__button {
  cursor: not-allowed;
}

.orb-checkbox__button:hover:not([disabled]) {
  background-color: var(--input-hover-bg-color, var(--ux-theme-3, #38404a));
}

.orb-checkbox__button[data-state='checked'] {
  background-color: var(--color-corporate-green-50, #15d1a0);
  border-color: var(--color-corporate-green-50, #15d1a0);
}

.orb-checkbox__button--error {
  border-color: var(--inline-error-border-color, #ef4444);
}

.orb-checkbox__indicator {
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--font-color, #f4f4f5);
}

.orb-checkbox__indicator svg {
  width: 9px;
}

.orb-checkbox__label {
  cursor: pointer;
  color: var(--font-color, #f4f4f5);
  font-size: 13px;
}

.orb-checkbox__row--disabled .orb-checkbox__label {
  cursor: not-allowed;
}

.orb-checkbox__help {
  display: inline-flex;
  align-items: center;
  color: var(--font-color-dimmed, #9ca3af);
  cursor: help;
  margin-left: 4px;
  transition: color 120ms ease;
}

.orb-checkbox__help:hover {
  color: var(--font-color, #f4f4f5);
}

.orb-checkbox__help svg {
  width: 12px;
  height: 12px;
}

.orb-checkbox__errors {
  margin: 4px 0 0 18px;
  padding: 0;
  color: var(--inline-error-text-color, #ef4444);
  font-size: 12px;
  list-style: disc;
}
</style>
