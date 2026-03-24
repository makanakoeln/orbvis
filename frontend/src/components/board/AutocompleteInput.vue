<template>
  <div class="relative">
    <input
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
      @input="onInput"
      @focus="!disabled && (open = true)"
      @blur="onBlur"
      @keydown.down.prevent="moveDown"
      @keydown.up.prevent="moveUp"
      @keydown.enter.prevent="confirmSelection"
      @keydown.escape="open = false"
    />
    <span v-if="loading" class="absolute right-2.5 top-2.5 text-zinc-600 text-xs select-none"
      >…</span
    >

    <div
      v-if="open && filtered.length > 0"
      class="absolute z-50 top-full left-0 right-0 mt-1 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg shadow-2xl shadow-black/50 overflow-auto max-h-48"
    >
      <button
        v-for="(item, i) in filtered"
        :key="item"
        type="button"
        class="w-full text-left px-3 py-2 text-sm truncate transition-colors"
        :class="
          i === activeIndex
            ? 'bg-indigo-600 text-white'
            : 'text-zinc-200 hover:bg-zinc-700 hover:text-[var(--text)]'
        "
        @mousedown.prevent="select(item)"
      >
        {{ item }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  modelValue: string
  suggestions: string[]
  placeholder?: string
  loading?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

const open = ref(false)
const activeIndex = ref(-1)

const filtered = computed(() => {
  const q = props.modelValue.toLowerCase()
  const list = q
    ? props.suggestions.filter((s) => s.toLowerCase().includes(q))
    : props.suggestions.slice()
  return list.sort((a, b) => a.localeCompare(b)).slice(0, 50)
})

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
  open.value = true
  activeIndex.value = -1
}

function onBlur() {
  // small delay so mousedown on option fires first
  setTimeout(() => {
    open.value = false
    activeIndex.value = -1
  }, 150)
}

function select(item: string) {
  emit('update:modelValue', item)
  emit('change', item)
  open.value = false
  activeIndex.value = -1
}

function moveDown() {
  activeIndex.value = Math.min(activeIndex.value + 1, filtered.value.length - 1)
}

function moveUp() {
  activeIndex.value = Math.max(activeIndex.value - 1, -1)
}

function confirmSelection() {
  if (activeIndex.value >= 0 && filtered.value[activeIndex.value]) {
    select(filtered.value[activeIndex.value])
  }
}
</script>
