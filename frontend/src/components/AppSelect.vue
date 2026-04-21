<template>
  <div ref="containerRef" class="relative">
    <button
      type="button"
      class="w-full flex items-center justify-between px-[10px] py-[5px] bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)] transition-all text-left"
      @click="toggle"
    >
      <span>{{ selectedLabel }}</span>
      <svg
        style="width: 12px; height: 12px"
        class="text-zinc-400 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
      </svg>
    </button>
    <Teleport to="body">
      <div
        v-if="open"
        ref="dropdownRef"
        :style="dropdownStyle"
        class="fixed z-[9999] bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-lg shadow-xl shadow-black/40 overflow-y-auto max-h-[240px]"
      >
        <button
          v-for="opt in options"
          :key="opt.value"
          type="button"
          class="w-full text-left px-[10px] py-[5px] text-sm transition-colors"
          :class="
            modelValue === opt.value
              ? 'text-[var(--color-corporate-green-40)] bg-[var(--color-corporate-green-50)]/10'
              : 'text-[var(--text)] hover:bg-[var(--bg-hover)]'
          "
          @click="select(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

const props = defineProps<{
  modelValue: string;
  options: { value: string; label: string }[];
}>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();

const open = ref(false);
const containerRef = ref<HTMLElement | null>(null);
const dropdownRef = ref<HTMLElement | null>(null);
const dropdownStyle = ref<Record<string, string>>({});

const selectedLabel = computed(
  () => props.options.find((o) => o.value === props.modelValue)?.label ?? props.modelValue,
);

function toggle() {
  if (!open.value && containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const width = rect.width;
    if (spaceBelow < 200) {
      dropdownStyle.value = {
        bottom: `${window.innerHeight - rect.top + 2}px`,
        left: `${rect.left}px`,
        width: `${width}px`,
      };
    } else {
      dropdownStyle.value = {
        top: `${rect.bottom + 2}px`,
        left: `${rect.left}px`,
        width: `${width}px`,
      };
    }
  }
  open.value = !open.value;
}

function select(value: string) {
  emit('update:modelValue', value);
  open.value = false;
}

function onOutsideClick(e: MouseEvent) {
  const target = e.target as Node;
  if (
    containerRef.value &&
    !containerRef.value.contains(target) &&
    dropdownRef.value &&
    !dropdownRef.value.contains(target)
  ) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener('mousedown', onOutsideClick));
onBeforeUnmount(() => document.removeEventListener('mousedown', onOutsideClick));
</script>
