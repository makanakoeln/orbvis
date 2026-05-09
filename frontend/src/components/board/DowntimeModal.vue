<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-[26rem] space-y-4"
            >
                <h3 class="text-base font-bold text-[var(--text)]">{{ t('downtime.title') }}</h3>
                <p class="text-xs text-[var(--text-muted)] -mt-2">{{ displayName }}</p>
                <p v-if="isGroup" class="text-xs text-amber-400 -mt-2" :title="t('ack.groupHint')">
                    {{ t('ack.groupScope', { type: groupTypeLabel }) }}
                </p>

                <div class="space-y-3">
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{
                            t('downtime.startTime')
                        }}</label>
                        <input
                            v-model="startTime"
                            type="datetime-local"
                            class="w-full px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)]"
                        />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{
                            t('downtime.endTime')
                        }}</label>
                        <input
                            v-model="endTime"
                            type="datetime-local"
                            class="w-full px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)]"
                        />
                    </div>
                    <div class="space-y-[4px]">
                        <CmkLabel>{{ t('downtime.comment') }}</CmkLabel>
                        <CmkInput
                            v-model="comment"
                            field-size="FILL"
                            :placeholder="t('downtime.comment') + '…'"
                        />
                    </div>
                </div>

                <CmkAlertBox v-if="error" variant="error" size="small">{{ error }}</CmkAlertBox>
                <p v-if="success" class="text-xs text-green-400">{{ t('downtime.success') }}</p>

                <div class="flex gap-3 justify-end pt-1 border-t border-[var(--border)]">
                    <CmkButton variant="secondary" @click="$emit('close')">{{
                        t('common.cancel')
                    }}</CmkButton>
                    <CmkButton
                        variant="primary"
                        :disabled="submitting || !comment.trim()"
                        @click="submit"
                    >
                        {{ submitting ? t('downtime.submitting') : t('downtime.submit') }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import { useEscapeClose } from '@/composables/useEscapeClose';
import type { BoardObject } from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';

const { t } = useI18n();

const props = defineProps<{
    object: BoardObject;
    checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();
useEscapeClose(() => emit('close'));

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
const groupTypeLabel = computed(() =>
    props.object.type === 'hostgroup' ? t('ack.groupHostgroup') : t('ack.groupServicegroup'),
);

async function submit() {
    if (!comment.value.trim() || submitting.value) return;
    submitting.value = true;
    error.value = '';
    const commentText = comment.value;
    try {
        const start = new Date(startTime.value).toISOString();
        const end = new Date(endTime.value).toISOString();
        // Group downtimes fan out via CMK's downtime_type=hostgroup|servicegroup
        // — one REST call covers every member.
        if (props.object.type === 'hostgroup' && props.object.group_name) {
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
            );
        } else if (props.object.host_name) {
            await cmkApi.downtimeHost(
                props.checkmkUrl,
                props.object.host_name,
                start,
                end,
                commentText,
            );
        }
        success.value = true;
        setTimeout(() => emit('close'), 1200);
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : t('downtime.error');
    } finally {
        submitting.value = false;
    }
}
</script>
