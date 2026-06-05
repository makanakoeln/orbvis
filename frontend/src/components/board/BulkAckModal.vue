<template>
  <OrbModal :open="true" :title="t('ack.bulkTitle')" closable @close="$emit('close')">
    <p class="bulk-ack__subtitle">
      {{
        t('ack.bulkSubtitle', {
          aggregation: aggregationId,
          count: targets.length
        })
      }}
    </p>

    <ul class="bulk-ack__list">
      <li
        v-for="(t2, i) in targets"
        :key="i"
        class="bulk-ack__item"
        :title="t2.service ? `${t2.host} / ${t2.service}` : t2.host"
      >
        {{ t2.host }}<span v-if="t2.service" class="bulk-ack__service"> / {{ t2.service }}</span>
      </li>
    </ul>

    <div class="bulk-ack__fields">
      <div>
        <label class="bulk-ack__label">{{ t('ack.comment') }}</label>
        <CmkInput
          ref="commentEl"
          v-model="comment"
          field-size="FILL"
          :placeholder="t('ack.comment') + '…'"
        />
      </div>
      <CmkCheckbox v-model="sticky" :label="t('ack.sticky')" />
      <CmkCheckbox v-model="notify" :label="t('ack.notify')" />
      <CmkCheckbox v-model="persistent" :label="t('ack.persistent')" />
    </div>

    <CmkAlertBox v-if="error" variant="error" size="small">
      <span style="white-space: pre-line">{{ error }}</span>
    </CmkAlertBox>
    <p v-if="successCount" class="bulk-ack__success">
      {{ t('ack.bulkSuccess', { count: successCount }) }}
    </p>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ t('common.cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="submitting || !comment.trim()" @click="submit">
        {{
          submitting
            ? t('ack.bulkSubmitting', {
                current: progress,
                total: targets.length
              })
            : t('ack.bulkSubmit', { count: targets.length })
        }}
      </CmkButton>
    </template>
  </OrbModal>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import OrbModal from '@/components/OrbModal.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { cmkApi } from '@/api/client'
import type { BulkAckTarget } from '@/types/api'

const props = defineProps<{
  /** Aggregation that originated the bulk-ack — embedded in the comment
   * trailer so audit logs show "Bulk-ack: <agg> — <user comment>". */
  aggregationId: string
  targets: BulkAckTarget[]
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

const { t } = useI18n()
const comment = ref(`Bulk-ack: ${props.aggregationId}`)
const sticky = ref(true)
const notify = ref(true)
const persistent = ref(false)
const submitting = ref(false)
const progress = ref(0)
const successCount = ref(0)
const error = ref('')
const commentEl = ref<HTMLInputElement | null>(null)
let closeTimer: number | null = null
onBeforeUnmount(() => {
  if (closeTimer !== null) window.clearTimeout(closeTimer)
})

onMounted(() => commentEl.value?.focus())

async function submit() {
  if (!comment.value.trim() || submitting.value) return
  submitting.value = true
  error.value = ''
  progress.value = 0
  successCount.value = 0
  const failures: string[] = []

  // Bounded parallelism: each leaf hits the same Checkmk site so we cap
  // concurrency to keep the GUI responsive without queueing up many
  // simultaneous COMMAND-pipe writes (livestatus serialises them
  // anyway). Five matches CMK's own bulk-action UI default.
  const CONCURRENCY = 5
  const queue = [...props.targets]
  const ackOne = async (tgt: BulkAckTarget): Promise<void> => {
    try {
      if (tgt.service) {
        await cmkApi.acknowledgeService(
          props.checkmkUrl,
          tgt.host,
          tgt.service,
          comment.value,
          sticky.value,
          notify.value,
          persistent.value
        )
      } else {
        await cmkApi.acknowledgeHost(
          props.checkmkUrl,
          tgt.host,
          comment.value,
          sticky.value,
          notify.value,
          persistent.value
        )
      }
      successCount.value += 1
    } catch (e) {
      failures.push(tgt.service ? `${tgt.host}/${tgt.service}` : tgt.host)
      console.warn('[OrbVis] bulk-ack failed for', tgt, e)
    } finally {
      progress.value += 1
    }
  }
  const workers = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
    for (;;) {
      const next = queue.shift()
      if (!next) return
      await ackOne(next)
    }
  })
  await Promise.all(workers)
  submitting.value = false
  if (failures.length) {
    error.value = t('ack.bulkPartial', {
      failed: failures.length,
      total: props.targets.length,
      sample: failures.slice(0, 3).join(', ')
    })
  } else {
    closeTimer = window.setTimeout(() => emit('close'), 1200)
  }
}
</script>

<style scoped>
.bulk-ack__subtitle {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
  margin: calc(-1 * var(--dimension-4)) 0 var(--dimension-5);
}

.bulk-ack__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 160px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--dimension-3);
  font-size: var(--font-size-normal);
}

.bulk-ack__item {
  padding: var(--dimension-3) var(--dimension-5);
  font-family: monospace;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bulk-ack__list > .bulk-ack__item + .bulk-ack__item {
  border-top: 1px solid var(--border);
}

.bulk-ack__service {
  color: var(--text-muted);
}

.bulk-ack__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.bulk-ack__label {
  display: block;
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: var(--dimension-3);
}

.bulk-ack__success {
  font-size: var(--font-size-normal);
  color: var(--color-corporate-green-50);
  margin-top: var(--dimension-4);
}
</style>
