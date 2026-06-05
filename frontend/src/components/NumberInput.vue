<template>
    <div class="orb-number" :class="wrapperClass">
        <input
            type="number"
            :value="displayValue"
            v-bind="inputAttrs"
            class="orb-number__input"
            @input="onInput"
            @change="onCommit"
            @blur="onCommit"
            @keydown.up.prevent="step(1)"
            @keydown.down.prevent="step(-1)"
        />
        <div class="orb-number__spinner">
            <button
                type="button"
                tabindex="-1"
                class="orb-number__btn"
                @mousedown.prevent="step(1)"
            >
                <svg
                    class="orb-number__chevron"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M4.5 15.75l7.5-7.5 7.5 7.5"
                    />
                </svg>
            </button>
            <button
                type="button"
                tabindex="-1"
                class="orb-number__btn orb-number__btn--down"
                @mousedown.prevent="step(-1)"
            >
                <svg
                    class="orb-number__chevron"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                    />
                </svg>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import type { ClassValue } from 'vue';
import { computed, useAttrs } from 'vue';

const props = defineProps<{
    modelValue: number | null | undefined;
    precision?: number;
}>();

const emit = defineEmits<{
    'update:modelValue': [value: number | null];
}>();

defineOptions({ inheritAttrs: false });

const attrs = useAttrs();

const wrapperClass = computed<ClassValue>(() => attrs.class as ClassValue);

const inputAttrs = computed(() => {
    const { class: _, ...rest } = attrs;
    return rest;
});

const displayValue = computed(() => {
    if (props.modelValue == null) return '';
    if (props.precision !== undefined) return Number(props.modelValue.toFixed(props.precision));
    return props.modelValue;
});

const stepSize = computed(() => {
    const s = attrs.step as string | undefined;
    if (!s || s === 'any') return 1;
    return Number(s);
});

const minVal = computed(() => (attrs.min !== undefined ? Number(attrs.min) : undefined));
const maxVal = computed(() => (attrs.max !== undefined ? Number(attrs.max) : undefined));

function onInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    if (val === '') {
        emit('update:modelValue', null);
        return;
    }
    const next = Number(val);
    if (Number.isNaN(next)) return;
    // Don't clamp during typing — a partial value like "1" must survive long
    // enough for the user to add the next digit "11". Final clamping happens
    // on commit (blur/change/step buttons).
    emit('update:modelValue', next);
}

function onCommit(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    if (val === '') return;
    let next = Number(val);
    if (Number.isNaN(next)) return;
    if (minVal.value !== undefined) next = Math.max(minVal.value, next);
    if (maxVal.value !== undefined) next = Math.min(maxVal.value, next);
    if (next !== props.modelValue) emit('update:modelValue', next);
}

function step(dir: 1 | -1) {
    const current = props.modelValue ?? 0;
    let next = current + dir * stepSize.value;
    if (minVal.value !== undefined) next = Math.max(minVal.value, next);
    if (maxVal.value !== undefined) next = Math.min(maxVal.value, next);
    const decimals =
        stepSize.value < 1 ? (stepSize.value.toString().split('.')[1]?.length ?? 0) : 0;
    emit('update:modelValue', Number(next.toFixed(decimals)));
}
</script>

<style scoped>
.orb-number {
    position: relative;
}

.orb-number__input {
    width: 100%;
    padding: 5px 24px 5px 8px;
    appearance: textfield;
    font-size: var(--font-size-large);
    line-height: 20px;
    color: var(--text);
    background: var(--default-form-element-bg-color);
    border-radius: 8px;
    box-shadow: 0 0 0 1px var(--default-form-element-border-color);
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-number__input::placeholder {
    color: var(--default-form-element-placeholder-color);
}

.orb-number__input:focus {
    outline: none;
    box-shadow: 0 0 0 2px var(--color-corporate-green-50);
}

.orb-number__input::-webkit-outer-spin-button,
.orb-number__input::-webkit-inner-spin-button {
    display: none;
}

.orb-number__spinner {
    position: absolute;
    inset: 0 0 0 auto;
    display: flex;
    flex-direction: column;
    width: 20px;
    overflow: hidden;
    border-left: 1px solid var(--border);
    border-radius: 0 0.5rem 0.5rem 0;
}

.orb-number__btn {
    display: flex;
    flex: 1;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    transition:
        color 0.15s,
        background-color 0.15s;
}

.orb-number__btn:hover {
    color: var(--text);
    background: var(--bg-hover);
}

.orb-number__btn--down {
    border-top: 1px solid var(--border);
}

.orb-number__chevron {
    width: 8px;
    height: 8px;
}
</style>
