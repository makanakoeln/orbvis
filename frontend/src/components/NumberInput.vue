<template>
    <div class="relative" :class="wrapperClass">
        <input
            type="number"
            :value="displayValue"
            v-bind="inputAttrs"
            class="w-full bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text)] placeholder-[var(--default-form-element-placeholder-color)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] transition-all duration-150 [appearance:textfield] [&::-webkit-outer-spin-button]:hidden [&::-webkit-inner-spin-button]:hidden"
            style="padding: 5px 24px 5px 8px"
            @input="onInput"
            @keydown.up.prevent="step(1)"
            @keydown.down.prevent="step(-1)"
        />
        <div
            class="absolute right-0 inset-y-0 flex flex-col border-l border-[var(--border)] rounded-r-lg overflow-hidden"
            style="width: 20px"
        >
            <button
                type="button"
                tabindex="-1"
                class="flex-1 flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors"
                @mousedown.prevent="step(1)"
            >
                <svg
                    style="width: 8px; height: 8px"
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
                class="flex-1 flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors border-t border-[var(--border)]"
                @mousedown.prevent="step(-1)"
            >
                <svg
                    style="width: 8px; height: 8px"
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
    emit('update:modelValue', val === '' ? null : Number(val));
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
