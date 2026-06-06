<template>
  <CmkPopup :open="open" @close="emit('cancel')">
    <div class="bulk-delete-dialog">
      <DialogTitle as-child>
        <h3 class="bulk-delete-dialog__title">
          {{ _t('Delete %{n} boards', { n: names.length }) }}
        </h3>
      </DialogTitle>
      <p class="bulk-delete-dialog__intro">
        {{ _t('The following boards will be permanently removed:') }}
      </p>
      <ul class="bulk-delete-dialog__list">
        <li v-for="entry in shown" :key="entry">{{ entry }}</li>
      </ul>
      <p v-if="overflow > 0" class="bulk-delete-dialog__more">
        {{ _t('… and %{n} more', { n: overflow }) }}
      </p>
      <footer class="bulk-delete-dialog__footer">
        <CmkButton variant="secondary" @click="emit('cancel')">
          {{ _t('Cancel') }}
        </CmkButton>
        <CmkButton variant="danger" :disabled="busy" @click="emit('confirm')">
          {{ _t('Delete') }}
        </CmkButton>
      </footer>
    </div>
  </CmkPopup>
</template>

<script setup lang="ts">
import { DialogTitle } from 'reka-ui'
import { computed } from 'vue'

import CmkButton from '@/components/cmk/CmkButton'
import CmkPopup from '@/components/cmk/CmkPopup'

import usei18n from '@/vendor/cmk/lib/i18n'

const MAX_VISIBLE = 20

const props = defineProps<{ open: boolean; names: string[]; busy?: boolean }>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()

const { _t } = usei18n()
const shown = computed(() => props.names.slice(0, MAX_VISIBLE))
const overflow = computed(() => Math.max(0, props.names.length - MAX_VISIBLE))
</script>

<style scoped>
.bulk-delete-dialog {
  width: 460px;
  max-width: 90vw;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  padding: var(--dimension-7) var(--dimension-8);
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

.bulk-delete-dialog__title {
  margin: 0;
  font-size: var(--font-size-large);
  line-height: 1.3;
}

.bulk-delete-dialog__intro {
  margin: 0;
  color: var(--text-muted);
}

.bulk-delete-dialog__list {
  margin: 0;
  padding: var(--dimension-3) var(--dimension-5);
  list-style: disc inside;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--dimension-2);
  background: var(--bg-subtle, var(--bg-surface));
  font-family: var(--font-family-monospace, monospace);
  font-size: 0.9em;
}

.bulk-delete-dialog__list li {
  padding: 1px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bulk-delete-dialog__more {
  margin: 0;
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.9em;
}

.bulk-delete-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--dimension-3);
  margin-top: var(--dimension-4);
}
</style>
