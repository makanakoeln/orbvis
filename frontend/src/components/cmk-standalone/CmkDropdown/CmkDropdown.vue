<!--
OrbVis-native CmkDropdown, swapped in for the vendored variant when
VITE_BUILD_TARGET=standalone. Supports the ``fixed`` Suggestions type
used by every OrbVis call site today; ``filtered`` and
``callback-filtered`` aren't implemented because OrbVis doesn't emit
them outside FormSpec, which is itself disabled in standalone mode.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

export interface DropdownOption {
    name: string;
    title: string;
    muted?: boolean;
    divider?: boolean;
}

export interface SuggestionsFixed {
    type: 'fixed' | 'filtered' | 'callback-filtered';
    suggestions: DropdownOption[];
    querySuggestions?: unknown;
}

const {
    selectedOption,
    inputHint = '',
    disabled = false,
    componentId = null,
    noElementsText = '',
    required = false,
    width,
    options,
    label,
    formValidation = false,
} = defineProps<{
    selectedOption: string | null;
    options: SuggestionsFixed;
    inputHint?: string;
    noResultsHint?: string;
    disabled?: boolean;
    componentId?: string | null;
    noElementsText?: string;
    required?: boolean;
    label: string;
    width?: 'fill' | 'auto' | undefined;
    formValidation?: boolean;
}>();

const emit = defineEmits<{
    (e: 'update:selectedOption', value: string | null): void;
}>();

const open = ref(false);
const rootRef = ref<HTMLDivElement | null>(null);

const currentTitle = computed(() => {
    if (selectedOption === null) return inputHint || noElementsText;
    const found = options.suggestions.find((s) => s.name === selectedOption);
    return found?.title ?? selectedOption;
});

const canOpen = computed(() => !disabled && options.suggestions.length > 0);

function toggle() {
    if (canOpen.value) open.value = !open.value;
}

function select(opt: DropdownOption) {
    emit('update:selectedOption', opt.name);
    open.value = false;
}

function handleClickOutside(event: MouseEvent) {
    if (!rootRef.value) return;
    if (!rootRef.value.contains(event.target as Node)) open.value = false;
}

onMounted(() => document.addEventListener('click', handleClickOutside));
onBeforeUnmount(() => document.removeEventListener('click', handleClickOutside));
</script>

<template>
    <div ref="rootRef" class="orb-dropdown" :class="{ 'orb-dropdown--fill': width === 'fill' }">
        <slot name="buttons-start" />
        <button
            :id="componentId ?? undefined"
            type="button"
            role="combobox"
            aria-haspopup="listbox"
            class="orb-dropdown__button"
            :class="{
                'orb-dropdown__button--disabled': disabled,
                'orb-dropdown__button--error': formValidation,
                'orb-dropdown__button--fill': width === 'fill',
            }"
            :aria-label="label"
            :aria-expanded="open"
            :disabled="disabled"
            @click.stop="toggle"
        >
            <span class="orb-dropdown__label">{{ currentTitle }}</span>
            <span
                v-if="required && selectedOption === null"
                class="orb-dropdown__required"
                aria-hidden="true"
                >*</span
            >
            <span class="orb-dropdown__arrow" :class="{ 'orb-dropdown__arrow--open': open }"
                >▾</span
            >
        </button>
        <slot name="buttons-end" />
        <ul v-if="open" class="orb-dropdown__menu" role="listbox">
            <template v-for="opt in options.suggestions" :key="opt.name">
                <li v-if="opt.divider" class="orb-dropdown__divider" role="separator" />
                <li
                    class="orb-dropdown__option"
                    :class="{
                        'orb-dropdown__option--selected': opt.name === selectedOption,
                        'orb-dropdown__option--muted': opt.muted,
                    }"
                    role="option"
                    :aria-selected="opt.name === selectedOption"
                    @click="select(opt)"
                >
                    <span>{{ opt.title }}</span>
                    <svg
                        v-if="opt.name === selectedOption"
                        class="orb-dropdown__option-check"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        aria-hidden="true"
                    >
                        <polyline points="20 6 9 17 4 12" />
                    </svg>
                </li>
            </template>
        </ul>
    </div>
</template>

<style scoped>
.orb-dropdown {
    display: inline-block;
    position: relative;
    white-space: nowrap;
    align-self: flex-start;
}

.orb-dropdown--fill {
    width: 100%;
}

.orb-dropdown__button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--default-form-element-bg-color, #27272a);
    color: var(--font-color, #f4f4f5);
    border: 1px solid var(--default-form-element-border-color, #71717a);
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
    height: 24px;
    cursor: pointer;
    min-width: 120px;
}

.orb-dropdown__button--fill {
    width: 100%;
}

.orb-dropdown__button:hover:not(:disabled) {
    background: var(--input-hover-bg-color, var(--ux-theme-3, #2a3038));
}

.orb-dropdown__button--disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.orb-dropdown__button--error {
    border-color: var(--inline-error-border-color, #ef4444);
}

.orb-dropdown__label {
    flex: 1 1 auto;
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
}

.orb-dropdown__required {
    color: var(--inline-error-text-color, #ef4444);
    margin-left: 2px;
}

.orb-dropdown__arrow {
    transition: transform 120ms ease;
    flex-shrink: 0;
    font-size: 10px;
    color: var(--font-color-dimmed, #9ca3af);
}

.orb-dropdown__arrow--open {
    transform: rotate(180deg);
}

.orb-dropdown__menu {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    min-width: 100%;
    max-height: 240px;
    overflow-y: auto;
    background: var(--bg-surface, var(--ux-theme-3, #262e36));
    border: 1px solid var(--default-form-element-border-color, #71717a);
    border-radius: 4px;
    padding: 4px 0;
    margin: 0;
    list-style: none;
    z-index: 100;
    box-shadow: 0 4px 12px rgb(0 0 0 / 30%);
}

.orb-dropdown__option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 4px 10px;
    font-size: 13px;
    cursor: pointer;
    color: var(--font-color, #f4f4f5);
}

.orb-dropdown__option:hover {
    background: rgb(255 255 255 / 14%);
}

.orb-dropdown__option--selected {
    background: color-mix(in srgb, var(--color-corporate-green-50, #15d1a0) 12%, transparent);
    color: var(--font-color, #f4f4f5);
    font-weight: 600;
}

.orb-dropdown__option--selected:hover {
    background: color-mix(in srgb, var(--color-corporate-green-50, #15d1a0) 22%, transparent);
}

.orb-dropdown__option-check {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
    color: var(--color-corporate-green-50, #15d1a0);
}

.orb-dropdown__option--muted > span:first-child {
    font-style: italic;
    color: var(--font-color-dimmed, #9ca3af);
}

.orb-dropdown__divider {
    height: 1px;
    margin: 4px 0;
    background: var(--border, rgb(255 255 255 / 8%));
    padding: 0;
    cursor: default;
}
</style>
