<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-[28rem] space-y-4"
            >
                <h3 class="text-base font-bold text-[var(--text)]">
                    {{ t('ack.bulkTitle') }}
                </h3>
                <p class="text-xs text-[var(--text-muted)] -mt-2">
                    {{
                        t('ack.bulkSubtitle', {
                            aggregation: aggregationId,
                            count: targets.length,
                        })
                    }}
                </p>

                <ul
                    class="max-h-40 overflow-y-auto rounded ring-1 ring-[var(--border)] divide-y divide-[var(--border)] text-xs"
                >
                    <li
                        v-for="(t2, i) in targets"
                        :key="i"
                        class="px-3 py-1.5 font-mono text-[var(--text)] truncate"
                        :title="t2.service ? `${t2.host} / ${t2.service}` : t2.host"
                    >
                        {{ t2.host
                        }}<span v-if="t2.service" class="text-[var(--text-muted)]">
                            / {{ t2.service }}</span
                        >
                    </li>
                </ul>

                <div class="space-y-3">
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{
                            t('ack.comment')
                        }}</label>
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
                <p v-if="successCount" class="text-xs text-green-400">
                    {{ t('ack.bulkSuccess', { count: successCount }) }}
                </p>

                <div class="flex gap-3 justify-end pt-1 border-t border-[var(--border)]">
                    <CmkButton variant="secondary" @click="$emit('close')">{{
                        t('common.cancel')
                    }}</CmkButton>
                    <CmkButton
                        variant="primary"
                        :disabled="submitting || !comment.trim()"
                        @click="submit"
                    >
                        {{
                            submitting
                                ? t('ack.bulkSubmitting', {
                                      current: progress,
                                      total: targets.length,
                                  })
                                : t('ack.bulkSubmit', { count: targets.length })
                        }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import { useEscapeClose } from '@/composables/useEscapeClose';
import type { BulkAckTarget } from '@/types/api';

const props = defineProps<{
    /** Aggregation that originated the bulk-ack — embedded in the comment
     * trailer so audit logs show "Bulk-ack: <agg> — <user comment>". */
    aggregationId: string;
    targets: BulkAckTarget[];
    checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();
useEscapeClose(() => emit('close'));

const { t } = useI18n();
// Pre-fill the comment with a tag containing the aggregation id so the
// audit trail shows which aggregation triggered the action. Operators
// can edit / append, but the prefix is what makes the entry searchable
// later.
const comment = ref(`Bulk-ack: ${props.aggregationId}`);
const sticky = ref(true);
const notify = ref(true);
const persistent = ref(false);
const submitting = ref(false);
const progress = ref(0);
const successCount = ref(0);
const error = ref('');
const commentEl = ref<HTMLInputElement | null>(null);
let closeTimer: number | null = null;
onBeforeUnmount(() => {
    if (closeTimer !== null) window.clearTimeout(closeTimer);
});

onMounted(() => commentEl.value?.focus());

async function submit() {
    if (!comment.value.trim() || submitting.value) return;
    submitting.value = true;
    error.value = '';
    progress.value = 0;
    successCount.value = 0;
    const failures: string[] = [];

    // Bounded parallelism: each leaf hits the same Checkmk site so we cap
    // concurrency to keep the GUI responsive without queueing up many
    // simultaneous COMMAND-pipe writes (livestatus serialises them
    // anyway). Five matches CMK's own bulk-action UI default.
    const CONCURRENCY = 5;
    const queue = [...props.targets];
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
                    persistent.value,
                );
            } else {
                await cmkApi.acknowledgeHost(
                    props.checkmkUrl,
                    tgt.host,
                    comment.value,
                    sticky.value,
                    notify.value,
                    persistent.value,
                );
            }
            successCount.value += 1;
        } catch (e) {
            failures.push(tgt.service ? `${tgt.host}/${tgt.service}` : tgt.host);
            console.warn('[OrbVis] bulk-ack failed for', tgt, e);
        } finally {
            progress.value += 1;
        }
    };
    const workers = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
        for (;;) {
            const next = queue.shift();
            if (!next) return;
            await ackOne(next);
        }
    });
    await Promise.all(workers);
    submitting.value = false;
    if (failures.length) {
        error.value = t('ack.bulkPartial', {
            failed: failures.length,
            total: props.targets.length,
            sample: failures.slice(0, 3).join(', '),
        });
    } else {
        closeTimer = window.setTimeout(() => emit('close'), 1200);
    }
}
</script>
