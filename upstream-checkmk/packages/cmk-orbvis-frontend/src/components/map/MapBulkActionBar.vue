<template>
  <Transition name="map-bulk-bar">
    <div v-if="count > 0" class="map-bulk-bar" role="region" :aria-label="ariaLabel">
      <div class="map-bulk-bar__info">
        <button
          type="button"
          class="map-bulk-bar__dismiss"
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
        <span class="map-bulk-bar__count">{{ _t('%{n} selected', { n: count }) }}</span>
        <label class="map-bulk-bar__selectall">
          <CmkCheckbox
            :model-value="selectAllChecked"
            @update:model-value="emit('toggle-select-all', $event)"
          />
          <span>{{ selectAllLabel }}</span>
        </label>
      </div>
      <div class="map-bulk-bar__actions">
        <CmkButton v-if="canEdit" variant="primary" :disabled="busy" @click="emit('edit')">
          {{ _t('Edit') }}
        </CmkButton>
        <CmkButton variant="secondary" :disabled="busy" @click="emit('export')">
          {{ _t('Export') }}
        </CmkButton>
        <CmkButton variant="danger" :disabled="busy" @click="emit('delete')">
          {{ _t('Delete') }}
        </CmkButton>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import CmkButton from '@/components/cmk/CmkButton'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

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
.map-bulk-bar {
  position: fixed;
  bottom: var(--dimension-6);
  left: 50%;
  transform: translateX(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--dimension-4) var(--dimension-6);
  padding: var(--dimension-3) var(--dimension-5);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--dimension-3);
  box-shadow: 0 8px 24px rgb(0 0 0 / 25%);
  max-width: calc(100vw - 24px);
}

.map-bulk-bar__info {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  flex-shrink: 0;
}

.map-bulk-bar__actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  flex-shrink: 0;
}

.map-bulk-bar__dismiss {
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

.map-bulk-bar__dismiss:hover {
  background: var(--bg-hover, rgb(255 255 255 / 8%));
  color: var(--text);
  border-color: var(--text-muted);
}

.map-bulk-bar__dismiss svg {
  width: 12px;
  height: 12px;
}

.map-bulk-bar__count {
  font-weight: 600;
  white-space: nowrap;
}

.map-bulk-bar__selectall {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
  color: var(--text-muted);
  font-size: 0.9em;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.map-bulk-bar__actions :deep(button) {
  white-space: nowrap;
  flex-shrink: 0;
}

.map-bulk-bar-enter-active,
.map-bulk-bar-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.map-bulk-bar-enter-from,
.map-bulk-bar-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}
</style>
