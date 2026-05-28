<template>
    <OrbModal :open="true" :title="t('downtime.title')" closable @close="$emit('close')">
        <p class="downtime-modal__subtitle">{{ displayName }}</p>
        <p v-if="isGroup" class="downtime-modal__group-hint" :title="t('ack.groupHint')">
            {{ t('ack.groupScope', { type: groupTypeLabel }) }}
        </p>

        <div class="downtime-modal__fields">
            <div>
                <label class="downtime-modal__label">{{ t('downtime.startTime') }}</label>
                <input v-model="startTime" type="datetime-local" class="downtime-modal__input" />
            </div>
            <div>
                <label class="downtime-modal__label">{{ t('downtime.endTime') }}</label>
                <input v-model="endTime" type="datetime-local" class="downtime-modal__input" />
            </div>
            <div class="downtime-modal__cmk-field">
                <CmkLabel>{{ t('downtime.comment') }}</CmkLabel>
                <CmkInput
                    v-model="comment"
                    field-size="FILL"
                    :placeholder="t('downtime.comment') + '…'"
                />
            </div>
        </div>

        <CmkAlertBox v-if="error" variant="error" size="small">
            <span style="white-space: pre-line">{{ error }}</span>
        </CmkAlertBox>
        <p v-if="success" class="downtime-modal__success">{{ t('downtime.success') }}</p>

        <template #footer>
            <CmkButton variant="secondary" @click="$emit('close')">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton variant="primary" :disabled="submitting || !comment.trim()" @click="submit">
                {{ submitting ? t('downtime.submitting') : t('downtime.submit') }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import CmkAlertBox from '@/components/cmk/CmkAlertBox';
import CmkButton from '@/components/cmk/CmkButton';
import CmkLabel from '@/components/cmk/CmkLabel';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import OrbModal from '@/components/OrbModal.vue';
import { useStatesStore } from '@/stores/states';
import type { BoardObject } from '@/types/api';
import { flattenAggregationLeaves } from '@/utils/aggregationTree';
import { getBoardObjectName } from '@/utils/naming';

const { t } = useI18n();

const props = defineProps<{
    object: BoardObject;
    checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();

function toLocalDatetimeString(d: Date): string {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const now = new Date();
const oneHourLater = new Date(now.getTime() + 3600_000);

const startTime = ref(toLocalDatetimeString(now));
const endTime = ref(toLocalDatetimeString(oneHourLater));
const comment = ref('');
const submitting = ref(false);
const error = ref('');
const success = ref(false);

const displayName = computed(() => getBoardObjectName(props.object));

const isGroup = computed(
    () => props.object.type === 'hostgroup' || props.object.type === 'servicegroup',
);
const isAggregation = computed(() => props.object.type === 'aggregation');
const groupTypeLabel = computed(() =>
    props.object.type === 'hostgroup' ? t('ack.groupHostgroup') : t('ack.groupServicegroup'),
);

const statesStore = useStatesStore();

interface DowntimeTarget {
    host: string;
    service: string | null;
}

function aggregationDowntimeTargets(): DowntimeTarget[] {
    const state = statesStore.getState(props.object.id);
    const tree = state?.tree;
    if (!tree) return [];
    return flattenAggregationLeaves(tree)
        .filter((l) => !!l.host_name)
        .map((l) => ({ host: l.host_name as string, service: l.service_description ?? null }));
}

async function submit() {
    if (!comment.value.trim() || submitting.value) return;
    submitting.value = true;
    error.value = '';
    const commentText = comment.value;
    try {
        const start = new Date(startTime.value).toISOString();
        const end = new Date(endTime.value).toISOString();
        if (isAggregation.value) {
            const targets = aggregationDowntimeTargets();
            if (!targets.length) {
                error.value = t('downtime.error');
                return;
            }
            const CONCURRENCY = 5;
            const queue = [...targets];
            const failures: string[] = [];
            const downtimeOne = async (tgt: DowntimeTarget): Promise<void> => {
                try {
                    if (tgt.service) {
                        await cmkApi.downtimeService(
                            props.checkmkUrl,
                            tgt.host,
                            tgt.service,
                            start,
                            end,
                            commentText,
                        );
                    } else {
                        await cmkApi.downtimeHost(
                            props.checkmkUrl,
                            tgt.host,
                            start,
                            end,
                            commentText,
                        );
                    }
                } catch (e) {
                    failures.push(tgt.service ? `${tgt.host}/${tgt.service}` : tgt.host);
                    console.warn('[OrbVis] bulk-downtime failed for', tgt, e);
                }
            };
            const workers: Promise<void>[] = [];
            for (let i = 0; i < Math.min(CONCURRENCY, queue.length); i += 1) {
                workers.push(
                    (async () => {
                        while (queue.length) {
                            const tgt = queue.shift();
                            if (tgt) await downtimeOne(tgt);
                        }
                    })(),
                );
            }
            await Promise.all(workers);
            if (failures.length) {
                error.value = `${failures.length}/${targets.length} ${t('downtime.error')}`;
                return;
            }
        } else if (props.object.type === 'hostgroup' && props.object.group_name) {
            await cmkApi.downtimeHostgroup(
                props.checkmkUrl,
                props.object.group_name,
                start,
                end,
                commentText,
            );
        } else if (props.object.type === 'servicegroup' && props.object.group_name) {
            await cmkApi.downtimeServicegroup(
                props.checkmkUrl,
                props.object.group_name,
                start,
                end,
                commentText,
            );
        } else if (
            props.object.type === 'service' &&
            props.object.host_name &&
            props.object.service_description
        ) {
            await cmkApi.downtimeService(
                props.checkmkUrl,
                props.object.host_name,
                props.object.service_description,
                start,
                end,
                commentText,
                statesStore.getState(props.object.id)?.site_id ?? null,
            );
        } else if (props.object.host_name) {
            await cmkApi.downtimeHost(
                props.checkmkUrl,
                props.object.host_name,
                start,
                end,
                commentText,
                statesStore.getState(props.object.id)?.site_id ?? null,
            );
        }
        success.value = true;
        setTimeout(() => emit('close'), 1200);
    } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : t('downtime.error');
        error.value = enrichGroupError(msg);
    } finally {
        submitting.value = false;
    }
}

// Same enrichment as AckModal — implicit hostgroups (livestatus-only) are
// rejected by the WATO-backed downtime endpoint with an opaque field error.
function enrichGroupError(msg: string): string {
    if (!isGroup.value) return msg;
    if (/hostgroup_name|servicegroup_name|Group missing|not monitored/i.test(msg)) {
        return `${msg}\n\n${t('ack.groupNotConfigured', { type: groupTypeLabel.value })}`;
    }
    return msg;
}
</script>

<style scoped>
.downtime-modal__subtitle {
    font-size: var(--font-size-normal);
    color: var(--text-muted);
    margin: calc(-1 * var(--dimension-4)) 0 0;
}

.downtime-modal__group-hint {
    font-size: var(--font-size-normal);
    color: var(--color-yellow-50);
    margin: calc(-1 * var(--dimension-4)) 0 0;
}

.downtime-modal__fields {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-4);
    margin-top: var(--dimension-5);
}

.downtime-modal__cmk-field {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-2);
}

.downtime-modal__label {
    display: block;
    font-size: var(--font-size-normal);
    font-weight: 500;
    color: var(--text-muted);
    margin-bottom: var(--dimension-3);
}

.downtime-modal__input {
    width: 100%;
    padding: var(--dimension-4) var(--dimension-5);
    background: var(--default-form-element-bg-color);
    border: 1px solid var(--default-form-element-border-color);
    border-radius: var(--dimension-3);
    font-size: var(--font-size-large);
    color: var(--text);
}

.downtime-modal__input:focus {
    outline: none;
    border-color: var(--color-corporate-green-50);
    box-shadow: 0 0 0 2px var(--color-corporate-green-50);
}

.downtime-modal__success {
    font-size: var(--font-size-normal);
    color: var(--color-corporate-green-50);
    margin-top: var(--dimension-4);
}
</style>
