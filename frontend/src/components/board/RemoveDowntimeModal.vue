<template>
  <OrbModal :open="true" :title="_t('Remove downtime')" closable @close="$emit('close')">
    <p class="remove-downtime__subtitle">
      {{ objectName }} &mdash;
      {{
        downtimes.length === 0
          ? _t('no active downtimes')
          : _tn('%{n} downtime active', '%{n} downtimes active', downtimes.length, {
              n: downtimes.length
            })
      }}
    </p>

    <CmkScrollContainer max-height="16rem" height="auto">
      <div class="remove-downtime__list">
        <div v-for="dt in downtimes" :key="dt.id" class="remove-downtime__item">
          <div class="remove-downtime__meta">
            <p class="remove-downtime__author">
              {{ dt.author }}<span v-if="dt.comment"> &bull; {{ dt.comment }}</span>
            </p>
            <p class="remove-downtime__period">
              {{ formatTime(dt.start_time) }} &ndash; {{ formatTime(dt.end_time) }}
            </p>
          </div>
          <CmkButton variant="danger" :disabled="removingId !== null" @click="remove(dt)">
            {{ removingId === dt.id ? _t('Removing…') : _t('Remove') }}
          </CmkButton>
        </div>
      </div>
    </CmkScrollContainer>

    <CmkAlertBox v-if="error" variant="error" size="small">{{ error }}</CmkAlertBox>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
    </template>
  </OrbModal>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import OrbModal from '@/components/OrbModal.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'

import { cmkApi } from '@/api/client'
import type { DowntimeEntry } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

const props = defineProps<{
  downtimes: DowntimeEntry[]
  checkmkUrl: string
  objectName: string
}>()

const emit = defineEmits<{ close: [] }>()

const { _t, _tn } = usei18n()
const removingId = ref<string | null>(null)
const error = ref('')

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function remove(dt: DowntimeEntry) {
  if (removingId.value !== null) return
  removingId.value = dt.id
  error.value = ''
  try {
    await cmkApi.removeDowntimeById(props.checkmkUrl, dt.id, dt.site_id)
    emit('close')
  } catch (e) {
    error.value = e instanceof Error ? e.message : _t('Failed to remove downtime')
    removingId.value = null
  }
}
</script>

<style scoped>
.remove-downtime__subtitle {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
  margin: calc(-1 * var(--dimension-4)) 0 var(--dimension-5);
}

.remove-downtime__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--dimension-5);
  padding: var(--dimension-4) 0;
}

.remove-downtime__list > .remove-downtime__item + .remove-downtime__item {
  border-top: 1px solid var(--border);
}

.remove-downtime__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.remove-downtime__author {
  font-size: var(--font-size-large);
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-downtime__period {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}
</style>
