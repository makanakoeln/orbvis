<!--
Bulk acknowledge / schedule-downtime for every host in a SETUP folder — the
NOC's most common folder-scoped action (rack/rollout/site maintenance). Reuses
the per-host CMK commands with bounded concurrency (like BulkAckModal); a
recursion toggle includes sub-folders and a live count preview prevents
mis-fires.
-->
<template>
    <OrbModal
        :open="true"
        :title="t('board.ftBulkTitle', { folder: folder.title })"
        closable
        @close="$emit('close')"
    >
        <div class="fbulk__seg" role="tablist">
            <button
                type="button"
                class="fbulk__seg-btn"
                :class="{ 'fbulk__seg-btn--active': mode === 'ack' }"
                role="tab"
                :aria-selected="mode === 'ack'"
                @click="mode = 'ack'"
            >
                {{ t('board.ftBulkAck') }}
            </button>
            <button
                type="button"
                class="fbulk__seg-btn"
                :class="{ 'fbulk__seg-btn--active': mode === 'downtime' }"
                role="tab"
                :aria-selected="mode === 'downtime'"
                @click="mode = 'downtime'"
            >
                {{ t('board.ftBulkDowntime') }}
            </button>
        </div>

        <p class="fbulk__count">
            {{ t('board.ftBulkAffects', { count: hosts.length, folder: folder.title }) }}
        </p>
        <CmkCheckbox v-model="recursive" :label="t('board.ftBulkRecursive')" />

        <div class="fbulk__fields">
            <div>
                <label class="fbulk__label">{{ t('ack.comment') }}</label>
                <CmkInput
                    ref="commentEl"
                    v-model="comment"
                    field-size="FILL"
                    :placeholder="t('ack.comment') + '…'"
                />
            </div>
            <template v-if="mode === 'ack'">
                <CmkCheckbox v-model="sticky" :label="t('ack.sticky')" />
                <CmkCheckbox v-model="notify" :label="t('ack.notify')" />
                <CmkCheckbox v-model="persistent" :label="t('ack.persistent')" />
            </template>
            <div v-else>
                <label class="fbulk__label">{{ t('board.ftBulkDuration') }}</label>
                <select v-model.number="durationH" class="fbulk__select">
                    <option v-for="d in durations" :key="d" :value="d">{{ d }} h</option>
                </select>
            </div>
        </div>

        <CmkAlertBox v-if="error" variant="error" size="small">
            <span style="white-space: pre-line">{{ error }}</span>
        </CmkAlertBox>
        <p v-if="successCount" class="fbulk__success">
            {{ t('board.ftBulkDone', { count: successCount }) }}
        </p>

        <template #footer>
            <CmkButton variant="secondary" @click="$emit('close')">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton
                variant="primary"
                :disabled="submitting || !comment.trim() || hosts.length === 0"
                @click="submit"
            >
                {{
                    submitting
                        ? t('ack.bulkSubmitting', { current: progress, total: hosts.length })
                        : mode === 'ack'
                          ? t('board.ftBulkAckSubmit', { count: hosts.length })
                          : t('board.ftBulkDowntimeSubmit', { count: hosts.length })
                }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import CmkAlertBox from '@/components/cmk/CmkAlertBox';
import CmkButton from '@/components/cmk/CmkButton';
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox';
import CmkInput from '@/components/cmk/user-input/CmkInput';
import OrbModal from '@/components/OrbModal.vue';
import type { FolderTreeNode } from '@/types/api';

const props = defineProps<{ folder: FolderTreeNode; checkmkUrl: string }>();
const emit = defineEmits<{ close: [] }>();

const { t } = useI18n();

const mode = ref<'ack' | 'downtime'>('downtime');
const recursive = ref(true);
const comment = ref('');
const sticky = ref(true);
const notify = ref(true);
const persistent = ref(false);
const durations = [1, 2, 4, 8, 24];
const durationH = ref(2);

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

interface BulkHost {
    host: string;
    siteId: string | null;
}

function collectHosts(node: FolderTreeNode, deep: boolean): BulkHost[] {
    const out: BulkHost[] = [];
    for (const c of node.children) {
        if (c.kind === 'host') out.push({ host: c.title, siteId: c.site_id ?? null });
        else if (deep && c.kind === 'folder') out.push(...collectHosts(c, true));
    }
    return out;
}
// De-dup by host name (unique per board scope) and keep it reactive on toggle.
const hosts = computed(() => {
    const seen = new Set<string>();
    const out: BulkHost[] = [];
    for (const h of collectHosts(props.folder, recursive.value)) {
        if (seen.has(h.host)) continue;
        seen.add(h.host);
        out.push(h);
    }
    return out;
});

async function submit() {
    if (!comment.value.trim() || submitting.value || hosts.value.length === 0) return;
    submitting.value = true;
    error.value = '';
    progress.value = 0;
    successCount.value = 0;
    const failures: string[] = [];

    const start = new Date().toISOString();
    const end = new Date(Date.now() + durationH.value * 3600_000).toISOString();

    const runOne = async ({ host, siteId }: BulkHost): Promise<void> => {
        try {
            if (mode.value === 'ack') {
                await cmkApi.acknowledgeHost(
                    props.checkmkUrl,
                    host,
                    comment.value,
                    sticky.value,
                    notify.value,
                    persistent.value,
                    siteId,
                );
            } else {
                await cmkApi.downtimeHost(
                    props.checkmkUrl,
                    host,
                    start,
                    end,
                    comment.value,
                    siteId,
                );
            }
            successCount.value += 1;
        } catch (e) {
            failures.push(host);
            console.warn('[OrbVis] folder bulk action failed for', host, e);
        } finally {
            progress.value += 1;
        }
    };

    // Bounded concurrency — same site/COMMAND pipe; 5 matches CMK's bulk default.
    const queue = [...hosts.value];
    const workers = Array.from({ length: Math.min(5, queue.length) }, async () => {
        for (;;) {
            const next = queue.shift();
            if (next === undefined) return;
            await runOne(next);
        }
    });
    await Promise.all(workers);
    submitting.value = false;
    if (failures.length) {
        error.value = t('ack.bulkPartial', {
            failed: failures.length,
            total: hosts.value.length,
            sample: failures.slice(0, 3).join(', '),
        });
    } else {
        closeTimer = window.setTimeout(() => emit('close'), 1200);
    }
}
</script>

<style scoped>
.fbulk__seg {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    overflow: hidden;
    margin-bottom: var(--dimension-4);
}

.fbulk__seg-btn {
    font-size: var(--font-size-normal);
    padding: 4px 14px;
    border: none;
    background: var(--bg-surface);
    color: var(--text-muted);
    cursor: pointer;
}

.fbulk__seg-btn + .fbulk__seg-btn {
    border-left: 1px solid var(--border);
}

.fbulk__seg-btn--active {
    background: var(--accent);
    color: white;
}

.fbulk__count {
    font-size: var(--font-size-normal);
    color: var(--text);
    margin: 0 0 var(--dimension-3);
}

.fbulk__fields {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-4);
    margin-top: var(--dimension-5);
}

.fbulk__label {
    display: block;
    font-size: var(--font-size-normal);
    font-weight: 500;
    color: var(--text-muted);
    margin-bottom: var(--dimension-3);
}

.fbulk__select {
    background: var(--bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--border-radius);
    padding: 4px 8px;
    font-size: var(--font-size-normal);
}

.fbulk__success {
    font-size: var(--font-size-normal);
    color: var(--color-corporate-green-50);
    margin-top: var(--dimension-4);
}
</style>
