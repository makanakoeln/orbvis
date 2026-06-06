<template>
  <OrbModal :open="true" :title="_t('Acknowledge problem')" closable @close="$emit('close')">
    <p class="ack-modal__subtitle">{{ displayName }}</p>
    <p
      v-if="isGroup"
      class="ack-modal__group-hint"
      :title="
        _t(
          'Checkmk fans this command out across all members; partial failures abort the operation.'
        )
      "
    >
      {{ _t('Applies to every member of the %{type}', { type: groupTypeLabel }) }}
    </p>

    <div class="ack-modal__fields">
      <div>
        <label class="ack-modal__label">{{ _t('Comment') }}</label>
        <CmkInput
          ref="commentEl"
          v-model="comment"
          field-size="FILL"
          :placeholder="_t('Comment') + '…'"
        />
      </div>
      <CmkCheckbox v-model="sticky" :label="_t('Sticky (stays until OK)')" />
      <CmkCheckbox v-model="notify" :label="_t('Send notification')" />
      <CmkCheckbox v-model="persistent" :label="_t('Persistent')" />
    </div>

    <CmkAlertBox v-if="error" variant="error" size="small">
      <span style="white-space: pre-line">{{ error }}</span>
    </CmkAlertBox>
    <p v-if="success" class="ack-modal__success">{{ _t('Acknowledgement set') }}</p>

    <template #footer>
      <CmkButton variant="secondary" @click="$emit('close')">
        {{ _t('Cancel') }}
      </CmkButton>
      <CmkButton variant="primary" :disabled="submitting || !comment.trim()" @click="submit">
        {{ submitting ? _t('Acknowledging…') : _t('Acknowledge') }}
      </CmkButton>
    </template>
  </OrbModal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import OrbModal from '@/components/OrbModal.vue'
import CmkAlertBox from '@/components/cmk/CmkAlertBox'
import CmkButton from '@/components/cmk/CmkButton'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'
import CmkInput from '@/components/cmk/user-input/CmkInput'

import { cmkApi } from '@/api/client'
import { useStatesStore } from '@/stores/states'
import type { BoardObject } from '@/types/api'
import { getBoardObjectName } from '@/utils/naming'
import usei18n from '@/vendor/cmk/lib/i18n'

const props = defineProps<{
  object: BoardObject
  checkmkUrl: string
}>()

const emit = defineEmits<{ close: [] }>()

const { _t } = usei18n()
const comment = ref('')
const sticky = ref(true)
const notify = ref(true)
const persistent = ref(false)
const submitting = ref(false)
const error = ref('')
const success = ref(false)
const commentEl = ref<HTMLInputElement | null>(null)

const displayName = computed(() => getBoardObjectName(props.object))

const isGroup = computed(
  () => props.object.type === 'hostgroup' || props.object.type === 'servicegroup'
)
const groupTypeLabel = computed(() =>
  props.object.type === 'hostgroup' ? _t('host group') : _t('service group')
)

const statesStore = useStatesStore()

onMounted(() => commentEl.value?.focus())

async function submit() {
  if (!comment.value.trim() || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    // Group acks fan out via CMK's acknowledge_type=hostgroup|servicegroup
    // — one REST call applies to every member, much faster (and atomic
    // wrt failures) than looping per-member from the UI.
    if (props.object.type === 'hostgroup' && props.object.group_name) {
      await cmkApi.acknowledgeHostgroup(
        props.checkmkUrl,
        props.object.group_name,
        comment.value,
        sticky.value,
        notify.value,
        persistent.value
      )
    } else if (props.object.type === 'servicegroup' && props.object.group_name) {
      await cmkApi.acknowledgeServicegroup(
        props.checkmkUrl,
        props.object.group_name,
        comment.value,
        sticky.value,
        notify.value,
        persistent.value
      )
    } else if (
      props.object.type === 'service' &&
      props.object.host_name &&
      props.object.service_description
    ) {
      await cmkApi.acknowledgeService(
        props.checkmkUrl,
        props.object.host_name,
        props.object.service_description,
        comment.value,
        sticky.value,
        notify.value,
        persistent.value,
        statesStore.getState(props.object.id)?.site_id ?? null
      )
    } else if (props.object.host_name) {
      await cmkApi.acknowledgeHost(
        props.checkmkUrl,
        props.object.host_name,
        comment.value,
        sticky.value,
        notify.value,
        persistent.value,
        statesStore.getState(props.object.id)?.site_id ?? null
      )
    }
    success.value = true
    setTimeout(() => emit('close'), 1200)
  } catch (e) {
    error.value = enrichGroupError(e)
  } finally {
    submitting.value = false
  }
}

// CMK rejects bulk group-actions when the group is not WATO-configured (only
// implicit via livestatus group-membership). The raw error is "These fields
// have problems: hostgroup_name" — we tack on a hint pointing the operator
// at Setup → Host groups so they don't chase a code bug.
function enrichGroupError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e)
  if (!isGroup.value) return msg
  if (/hostgroup_name|servicegroup_name|Group missing|not monitored/i.test(msg)) {
    return `${msg}\n\n${_t('Tip: Checkmk only accepts bulk actions on %{type}s that are configured in Setup → Host groups (or Service groups). Implicit / livestatus-only groups are rejected by the REST API.', { type: groupTypeLabel.value })}`
  }
  return msg
}
</script>

<style scoped>
.ack-modal__subtitle {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

.ack-modal__group-hint {
  font-size: var(--font-size-normal);
  color: var(--color-yellow-50);
  margin: calc(-1 * var(--dimension-4)) 0 0;
}

.ack-modal__fields {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  margin-top: var(--dimension-5);
}

.ack-modal__label {
  display: block;
  font-size: var(--font-size-normal);
  font-weight: 500;
  color: var(--text-muted);
  margin-bottom: var(--dimension-3);
}

.ack-modal__success {
  font-size: var(--font-size-normal);
  color: var(--color-corporate-green-50);
  margin-top: var(--dimension-4);
}
</style>
