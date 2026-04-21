<template>
  <div class="relative">
    <input
      :value="displayValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full px-[10px] py-[5px] bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
      @input="onInput"
      @focus="!disabled && (open = true)"
      @click="!disabled && (open = true)"
      @blur="onBlur"
      @keydown.down.prevent="moveDown"
      @keydown.up.prevent="moveUp"
      @keydown.enter.prevent="confirmSelection"
      @keydown.escape="open = false"
    />
    <span
      v-if="loading"
      class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-600 text-xs select-none"
      >…</span
    >

    <div
      v-if="open && filtered.length > 0"
      class="absolute z-50 top-full left-0 right-0 mt-1 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg shadow-2xl shadow-black/50 overflow-auto max-h-48"
    >
      <button
        v-for="(item, i) in filtered"
        :key="item.value"
        type="button"
        class="w-full text-left px-3 py-2 text-sm truncate transition-colors"
        :class="
          i === activeIndex
            ? 'bg-[var(--color-corporate-green-50)] text-[var(--button-primary-text-color,#000)]'
            : 'text-zinc-200 hover:bg-zinc-700 hover:text-[var(--text)]'
        "
        @mousedown.prevent="select(item.value)"
      >
        {{ item.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

const props = defineProps<{
  modelValue: string;
  suggestions: string[];
  /** Optional display labels for each suggestion (parallel array). When provided,
   *  labels are shown in the dropdown and input, while values are emitted. */
  displayLabels?: string[];
  placeholder?: string;
  loading?: boolean;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  change: [value: string];
}>();

const open = ref(false);
const activeIndex = ref(-1);

/** The text currently shown in the input field. */
const displayValue = computed(() => {
  if (!props.displayLabels) return props.modelValue;
  const idx = props.suggestions.indexOf(props.modelValue);
  return idx >= 0 ? (props.displayLabels[idx] ?? props.modelValue) : props.modelValue;
});

const filtered = computed(() => {
  const q = displayValue.value.toLowerCase();
  const items = props.suggestions.map((value, i) => ({
    value,
    label: props.displayLabels?.[i] ?? value,
  }));
  const list = q ? items.filter(({ label }) => label.toLowerCase().includes(q)) : items.slice();
  return list.sort((a, b) => a.label.localeCompare(b.label)).slice(0, 50);
});

function onInput(e: Event) {
  // Emit the typed text so parent can use it as a search query.
  // When displayLabels are in use, the parent receives label text while typing
  // and the actual value only after a selection is confirmed via select().
  emit('update:modelValue', (e.target as HTMLInputElement).value);
  open.value = true;
  activeIndex.value = -1;
}

function onBlur() {
  // small delay so mousedown on option fires first
  setTimeout(() => {
    open.value = false;
    activeIndex.value = -1;
  }, 150);
}

function select(value: string) {
  emit('update:modelValue', value);
  emit('change', value);
  open.value = false;
  activeIndex.value = -1;
}

function moveDown() {
  activeIndex.value = Math.min(activeIndex.value + 1, filtered.value.length - 1);
}

function moveUp() {
  activeIndex.value = Math.max(activeIndex.value - 1, -1);
}

function confirmSelection() {
  if (activeIndex.value >= 0) {
    const item = filtered.value[activeIndex.value];
    if (item) select(item.value);
  }
}
</script>
