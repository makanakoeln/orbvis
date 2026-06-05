<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  modelValue: boolean
  title?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const { t } = useI18n()
</script>

<template>
  <button
    type="button"
    class="problems-only-toggle"
    :class="{ 'problems-only-toggle--active': modelValue }"
    :title="props.title ?? t('board.problemsOnly')"
    :aria-pressed="modelValue"
    @click="emit('update:modelValue', !modelValue)"
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M12 9v4m0 4h.01M10.29 3.86l-8.48 14.7A1.5 1.5 0 003.1 21h17.8a1.5 1.5 0 001.29-2.44l-8.48-14.7a1.5 1.5 0 00-2.42 0z"
      />
    </svg>
  </button>
</template>

<style scoped>
.problems-only-toggle {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  padding: 0;
}

.problems-only-toggle svg {
  width: 14px;
  height: 14px;
}

.problems-only-toggle:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.problems-only-toggle--active {
  color: var(--color-yellow-50, #fbbf24);
  border-color: var(--color-yellow-50, #fbbf24);
  background: rgb(251 191 36 / 12%);
}
</style>
