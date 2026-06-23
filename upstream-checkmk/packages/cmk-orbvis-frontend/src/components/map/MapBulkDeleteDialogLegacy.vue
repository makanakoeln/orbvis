<template>
  <Teleport to="body">
    <Transition name="orb-bulk-modal">
      <div
        v-if="open"
        class="orb-bulk-modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @keydown.esc="emit('cancel')"
      >
        <div class="orb-bulk-modal__backdrop" @click="emit('cancel')" />
        <div class="orb-bulk-modal__shell" tabindex="-1">
          <h3 :id="titleId" class="orb-bulk-modal__title">
            {{ _t('Delete %{n} maps', { n: names.length }) }}
          </h3>
          <p class="orb-bulk-modal__intro">
            {{ _t('The following maps will be permanently removed:') }}
          </p>
          <ul class="orb-bulk-modal__list">
            <li v-for="entry in shown" :key="entry">{{ entry }}</li>
          </ul>
          <p v-if="overflow > 0" class="orb-bulk-modal__more">
            {{ _t('… and %{n} more', { n: overflow }) }}
          </p>
          <footer class="orb-bulk-modal__footer">
            <button
              type="button"
              class="orb-bulk-modal__btn orb-bulk-modal__btn--ghost"
              @click="emit('cancel')"
            >
              {{ _t('Cancel') }}
            </button>
            <button
              type="button"
              class="orb-bulk-modal__btn orb-bulk-modal__btn--danger"
              :disabled="busy"
              @click="emit('confirm')"
            >
              {{ _t('Delete') }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'

import usei18n from '@cmk/lib/i18n'

const MAX_VISIBLE = 20

const props = defineProps<{ open: boolean; names: string[]; busy?: boolean }>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()

const { _t } = usei18n()
const titleId = useId()
const shown = computed(() => props.names.slice(0, MAX_VISIBLE))
const overflow = computed(() => Math.max(0, props.names.length - MAX_VISIBLE))
</script>

<style scoped>
.orb-bulk-modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
}

.orb-bulk-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgb(0 0 0 / 55%);
}

.orb-bulk-modal__shell {
  position: relative;
  width: 460px;
  max-width: 90vw;
  background: var(--bg-surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 12px 32px rgb(0 0 0 / 45%);
}

.orb-bulk-modal__title {
  margin: 0;
  font-size: 1.1em;
  font-weight: 600;
}

.orb-bulk-modal__intro {
  margin: 0;
  color: var(--text-muted);
}

.orb-bulk-modal__list {
  margin: 0;
  padding: 10px 16px;
  list-style: disc inside;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-subtle, rgb(255 255 255 / 4%));
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.9em;
}

.orb-bulk-modal__list li {
  padding: 1px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-bulk-modal__more {
  margin: 0;
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.9em;
}

.orb-bulk-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.orb-bulk-modal__btn {
  font: inherit;
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    background-color 0.15s,
    border-color 0.15s,
    color 0.15s;
}

.orb-bulk-modal__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.orb-bulk-modal__btn--ghost {
  background: transparent;
  color: var(--text);
  border-color: var(--border);
}

.orb-bulk-modal__btn--ghost:hover:not(:disabled) {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.orb-bulk-modal__btn--danger {
  background: var(--color-light-red-50);
  color: var(--color-white-100, white);
  border-color: var(--color-light-red-50);
}

.orb-bulk-modal__btn--danger:hover:not(:disabled) {
  background: var(--color-light-red-60);
  border-color: var(--color-light-red-60);
}

.orb-bulk-modal-enter-active,
.orb-bulk-modal-leave-active {
  transition: opacity 0.15s ease;
}

.orb-bulk-modal-enter-from,
.orb-bulk-modal-leave-to {
  opacity: 0;
}
</style>
