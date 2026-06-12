<template>
  <div class="orb-autocomplete">
    <input
      ref="inputRef"
      :value="displayValue"
      :placeholder="placeholder"
      :disabled="disabled"
      class="orb-field orb-autocomplete__input"
      @input="onInput"
      @focus="!disabled && (open = true)"
      @click="!disabled && (open = true)"
      @blur="onBlur"
      @keydown.down.prevent="moveDown"
      @keydown.up.prevent="moveUp"
      @keydown.enter.prevent="confirmSelection"
      @keydown.escape="open = false"
    />
    <span v-if="loading" class="orb-autocomplete__loading">…</span>

    <Teleport to="body">
      <div
        v-if="open && filtered.length > 0"
        class="orb-autocomplete__dropdown"
        :style="dropdownStyle"
      >
        <button
          v-for="(item, i) in filtered"
          :key="item.value"
          type="button"
          class="orb-autocomplete__option"
          :class="i === activeIndex ? 'orb-autocomplete__option--active' : ''"
          @mousedown.prevent="select(item.value)"
        >
          {{ item.label }}
        </button>
        <div v-if="truncated > 0" class="orb-autocomplete__more">
          +{{ truncated }} more — keep typing to narrow results
        </div>
      </div>
    </Teleport>
    <p v-if="emptyText && !loading && suggestions.length === 0" class="orb-autocomplete__empty">
      {{ emptyText }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { CSSProperties } from 'vue'

const props = defineProps<{
  modelValue: string
  suggestions: string[]
  /** Optional display labels for each suggestion (parallel array). When provided,
   *  labels are shown in the dropdown and input, while values are emitted. */
  displayLabels?: string[]
  placeholder?: string
  loading?: boolean
  disabled?: boolean
  /** Warning text shown below the input when suggestions is empty and not loading.
   *  Explicit ``undefined`` is allowed so callsites can pass conditional hints. */
  emptyText?: string | undefined
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

const open = ref(false)
const activeIndex = ref(-1)

// The dropdown is teleported to <body> so the inspector panel's `overflow:auto`
// can't clip it, and anchored with a fixed position that flips above the input
// when there isn't room below — without this a metric/service list low in the
// panel opened off-screen and its entries were unreachable.
const inputRef = ref<HTMLInputElement | null>(null)
const dropdownStyle = ref<CSSProperties>({})

const DROPDOWN_MAX_HEIGHT = 192
const DROPDOWN_GAP = 4

function updatePosition(): void {
  const el = inputRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top
  const openUp = spaceBelow < DROPDOWN_MAX_HEIGHT + DROPDOWN_GAP && spaceAbove > spaceBelow
  const base: CSSProperties = { left: `${rect.left}px`, width: `${rect.width}px` }
  dropdownStyle.value = openUp
    ? {
        ...base,
        bottom: `${window.innerHeight - rect.top + DROPDOWN_GAP}px`,
        maxHeight: `${Math.min(DROPDOWN_MAX_HEIGHT, spaceAbove - DROPDOWN_GAP * 2)}px`
      }
    : {
        ...base,
        top: `${rect.bottom + DROPDOWN_GAP}px`,
        maxHeight: `${Math.min(DROPDOWN_MAX_HEIGHT, spaceBelow - DROPDOWN_GAP * 2)}px`
      }
}

watch(open, (isOpen) => {
  if (isOpen) {
    void nextTick(updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    window.addEventListener('resize', updatePosition)
  } else {
    window.removeEventListener('scroll', updatePosition, true)
    window.removeEventListener('resize', updatePosition)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
})

/** The text currently shown in the input field. */
const displayValue = computed(() => {
  if (!props.displayLabels) return props.modelValue
  const idx = props.suggestions.indexOf(props.modelValue)
  return idx >= 0 ? (props.displayLabels[idx] ?? props.modelValue) : props.modelValue
})

// Cap kept so the dropdown stays responsive for thousands of suggestions, but
// raised from 50 — operators with hosts that have many services were missing
// entries below the previous cap when they couldn't recall the exact name to
// type. The list is virtualisable later if this proves too long.
const SUGGESTION_LIMIT = 500

const filtered = computed(() => {
  const q = displayValue.value.toLowerCase()
  const items = props.suggestions.map((value, i) => ({
    value,
    label: props.displayLabels?.[i] ?? value
  }))
  const list = q ? items.filter(({ label }) => label.toLowerCase().includes(q)) : items.slice()
  return list.sort((a, b) => a.label.localeCompare(b.label)).slice(0, SUGGESTION_LIMIT)
})

const truncated = computed(() => {
  const q = displayValue.value.toLowerCase()
  const matchCount = q
    ? props.suggestions.filter((value, i) =>
        (props.displayLabels?.[i] ?? value).toLowerCase().includes(q)
      ).length
    : props.suggestions.length
  return Math.max(0, matchCount - SUGGESTION_LIMIT)
})

function onInput(e: Event) {
  // Emit the typed text so parent can use it as a search query.
  // When displayLabels are in use, the parent receives label text while typing
  // and the actual value only after a selection is confirmed via select().
  emit('update:modelValue', (e.target as HTMLInputElement).value)
  open.value = true
  activeIndex.value = -1
  void nextTick(updatePosition)
}

function onBlur() {
  // small delay so mousedown on option fires first
  setTimeout(() => {
    open.value = false
    activeIndex.value = -1
  }, 150)
}

function select(value: string) {
  emit('update:modelValue', value)
  emit('change', value)
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
  if (activeIndex.value >= 0) {
    const item = filtered.value[activeIndex.value]
    if (item) select(item.value)
  }
}
</script>

<style scoped>
.orb-autocomplete {
  position: relative;
}

.orb-autocomplete__input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.orb-autocomplete__loading {
  position: absolute;
  top: 50%;
  right: var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
  user-select: none;
  transform: translateY(-50%);
}

.orb-autocomplete__dropdown {
  position: fixed;
  z-index: 1000;
  max-height: 192px;
  overflow: auto;
  background: var(--default-form-element-bg-color);
  border-radius: 8px;
  box-shadow:
    0 0 0 1px var(--default-form-element-border-color),
    0 25px 50px -12px rgb(0 0 0 / 50%);
}

.orb-autocomplete__option {
  overflow: hidden;
  width: 100%;
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--text);
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.orb-autocomplete__option:hover {
  background: var(--bg-hover);
}

.orb-autocomplete__option--active,
.orb-autocomplete__option--active:hover {
  color: var(--button-primary-text-color, #000);
  background: var(--color-corporate-green-50);
}

.orb-autocomplete__more {
  padding: var(--dimension-4) var(--dimension-5);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
}

.orb-autocomplete__empty {
  margin-top: var(--dimension-3);
  font-size: var(--font-size-normal);
  line-height: 1.375;
  color: color-mix(in srgb, var(--color-yellow-50) 70%, transparent);
}
</style>
