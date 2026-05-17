<template>
    <OrbModal :open="true" :title="t('ack.title')" closable @close="$emit('close')">
        <p class="ack-modal__subtitle">{{ displayName }}</p>
        <p v-if="isGroup" class="ack-modal__group-hint" :title="t('ack.groupHint')">
            {{ t('ack.groupScope', { type: groupTypeLabel }) }}
        </p>

        <div class="ack-modal__fields">
            <div>
                <label class="ack-modal__label">{{ t('ack.comment') }}</label>
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
        <p v-if="success" class="ack-modal__success">{{ t('ack.success') }}</p>

        <template #footer>
            <CmkButton variant="secondary" @click="$emit('close')">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton variant="primary" :disabled="submitting || !comment.trim()" @click="submit">
                {{ submitting ? t('ack.submitting') : t('ack.submit') }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import CmkAlertBox from '@/components/cmk/CmkAlertBox';
import CmkButton from '@/components/cmk/CmkButton';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import OrbModal from '@/components/OrbModal.vue';
import type { BoardObject } from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';

const props = defineProps<{
    object: BoardObject;
    checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();

const { t } = useI18n();
const comment = ref('');
const sticky = ref(true);
const notify = ref(true);
const persistent = ref(false);
const submitting = ref(false);
const error = ref('');
const success = ref(false);
const commentEl = ref<HTMLInputElement | null>(null);

const displayName = computed(() => getBoardObjectName(props.object));

const isGroup = computed(
    () => props.object.type === 'hostgroup' || props.object.type === 'servicegroup',
);
const groupTypeLabel = computed(() =>
    props.object.type === 'hostgroup' ? t('ack.groupHostgroup') : t('ack.groupServicegroup'),
);

onMounted(() => commentEl.value?.focus());

async function submit() {
    if (!comment.value.trim() || submitting.value) return;
    submitting.value = true;
    error.value = '';
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
                persistent.value,
            );
        } else if (props.object.type === 'servicegroup' && props.object.group_name) {
            await cmkApi.acknowledgeServicegroup(
                props.checkmkUrl,
                props.object.group_name,
                comment.value,
                sticky.value,
                notify.value,
                persistent.value,
            );
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
            );
        } else if (props.object.host_name) {
            await cmkApi.acknowledgeHost(
                props.checkmkUrl,
                props.object.host_name,
                comment.value,
                sticky.value,
                notify.value,
                persistent.value,
            );
        }
        success.value = true;
        setTimeout(() => emit('close'), 1200);
    } catch (e) {
        error.value = enrichGroupError(e);
    } finally {
        submitting.value = false;
    }
}

// CMK rejects bulk group-actions when the group is not WATO-configured (only
// implicit via livestatus group-membership). The raw error is "These fields
// have problems: hostgroup_name" — we tack on a hint pointing the operator
// at Setup → Host groups so they don't chase a code bug.
function enrichGroupError(e: unknown): string {
    const msg = e instanceof Error ? e.message : String(e);
    if (!isGroup.value) return msg;
    if (/hostgroup_name|servicegroup_name|Group missing|not monitored/i.test(msg)) {
        return `${msg}\n\n${t('ack.groupNotConfigured', { type: groupTypeLabel.value })}`;
    }
    return msg;
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
