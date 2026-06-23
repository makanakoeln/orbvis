<template>
  <Transition name="orb-bulk-bar">
    <div v-if="count > 0" class="orb-bulk-bar" role="region" :aria-label="ariaLabel">
      <div class="orb-bulk-bar__info">
        <button
          type="button"
          class="orb-bulk-bar__dismiss"
          :title="_t('Cancel')"
          :aria-label="_t('Cancel')"
          @click="emit('cancel')"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            aria-hidden="true"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <span class="orb-bulk-bar__count">{{ _t('%{n} selected', { n: count }) }}</span>
        <label class="orb-bulk-bar__selectall">
          <input
            type="checkbox"
            :checked="selectAllChecked"
            @change="emit('toggle-select-all', ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ selectAllLabel }}</span>
        </label>
      </div>
      <div class="orb-bulk-bar__actions">
        <button
          v-if="canEdit"
          type="button"
          class="orb-bulk-bar__btn orb-bulk-bar__btn--primary"
          :disabled="busy"
          @click="emit('edit')"
        >
          {{ _t('Edit') }}
        </button>
        <button
          type="button"
          class="orb-bulk-bar__btn orb-bulk-bar__btn--ghost"
          :disabled="busy"
          @click="emit('export')"
        >
          {{ _t('Export') }}
        </button>
        <button
          type="button"
          class="orb-bulk-bar__btn orb-bulk-bar__btn--danger"
          :disabled="busy"
          @click="emit('delete')"
        >
          {{ _t('Delete') }}
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@cmk/lib/i18n'

const props = defineProps<{
  count: number
  busy?: boolean
  selectAllChecked: boolean
  selectAllLabel: string
  canEdit?: boolean
}>()
const emit = defineEmits<{
  cancel: []
  delete: []
  edit: []
  export: []
  'toggle-select-all': [checked: boolean]
}>()

const { _t } = usei18n()
const ariaLabel = computed(() => _t('%{n} selected', { n: props.count }))
</script>

<style scoped>
.orb-bulk-bar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 24px;
  padding: 10px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 25%);
  max-width: calc(100vw - 24px);
  color: var(--text);
}

.orb-bulk-bar__info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.orb-bulk-bar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.orb-bulk-bar__dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s,
    border-color 0.15s;
}

.orb-bulk-bar__dismiss:hover {
  background: var(--bg-hover, rgb(255 255 255 / 8%));
  color: var(--text);
  border-color: var(--text-muted);
}

.orb-bulk-bar__dismiss svg {
  width: 12px;
  height: 12px;
}

.orb-bulk-bar__count {
  font-weight: 600;
  white-space: nowrap;
}

.orb-bulk-bar__selectall {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 0.9em;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.orb-bulk-bar__btn {
  font: inherit;
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
  flex-shrink: 0;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    color 0.15s;
}

.orb-bulk-bar__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.orb-bulk-bar__btn--ghost {
  background: transparent;
  color: var(--text);
  border-color: var(--border);
}

.orb-bulk-bar__btn--ghost:hover:not(:disabled) {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.orb-bulk-bar__btn--danger {
  background: var(--color-light-red-50);
  color: var(--color-white-100, white);
  border-color: var(--color-light-red-50);
}

.orb-bulk-bar__btn--danger:hover:not(:disabled) {
  background: var(--color-light-red-60);
  border-color: var(--color-light-red-60);
}

.orb-bulk-bar__btn--primary {
  background: var(--color-corporate-green-50);
  color: var(--button-primary-text-color, #000);
  border-color: var(--color-corporate-green-50);
}

.orb-bulk-bar__btn--primary:hover:not(:disabled) {
  background: var(--color-corporate-green-60);
  border-color: var(--color-corporate-green-60);
}

.orb-bulk-bar-enter-active,
.orb-bulk-bar-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.orb-bulk-bar-enter-from,
.orb-bulk-bar-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
