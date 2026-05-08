<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-[28rem] space-y-4"
            >
                <h3 class="text-base font-bold text-[var(--text)]">
                    {{ t('removeDowntimeModal.title') }}
                </h3>
                <p class="text-xs text-[var(--text-muted)] -mt-2">
                    {{ objectName }} &mdash; {{ t('removeDowntimeModal.active', downtimes.length) }}
                </p>

                <CmkScrollContainer max-height="16rem" height="auto">
                    <div class="divide-y divide-[var(--border)]">
                        <div
                            v-for="dt in downtimes"
                            :key="dt.id"
                            class="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0"
                        >
                            <div class="min-w-0 space-y-0.5">
                                <p class="text-sm font-medium text-[var(--text)] truncate">
                                    {{ dt.author
                                    }}<span v-if="dt.comment"> &bull; {{ dt.comment }}</span>
                                </p>
                                <p class="text-xs text-[var(--text-muted)]">
                                    {{ formatTime(dt.start_time) }} &ndash;
                                    {{ formatTime(dt.end_time) }}
                                </p>
                            </div>
                            <CmkButton
                                variant="danger"
                                :disabled="removingId !== null"
                                class="shrink-0"
                                @click="remove(dt)"
                            >
                                {{
                                    removingId === dt.id
                                        ? t('removeDowntimeModal.removing')
                                        : t('removeDowntimeModal.remove')
                                }}
                            </CmkButton>
                        </div>
                    </div>
                </CmkScrollContainer>

                <CmkAlertBox v-if="error" variant="error" size="small">{{ error }}</CmkAlertBox>

                <div class="flex justify-end pt-1 border-t border-[var(--border)]">
                    <CmkButton variant="secondary" @click="$emit('close')">{{
                        t('common.cancel')
                    }}</CmkButton>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import CmkAlertBox from '@cmk/components/CmkAlertBox.vue';
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkScrollContainer from '@cmk/components/CmkScrollContainer.vue';
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import { useEscapeClose } from '@/composables/useEscapeClose';
import type { DowntimeEntry } from '@/types/api';

const props = defineProps<{
    downtimes: DowntimeEntry[];
    checkmkUrl: string;
    objectName: string;
}>();

const emit = defineEmits<{ close: [] }>();
useEscapeClose(() => emit('close'));

const { t } = useI18n();
const removingId = ref<string | null>(null);
const error = ref('');

function formatTime(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

async function remove(dt: DowntimeEntry) {
    if (removingId.value !== null) return;
    removingId.value = dt.id;
    error.value = '';
    try {
        await cmkApi.removeDowntimeById(props.checkmkUrl, dt.id, dt.site_id);
        emit('close');
    } catch (e) {
        error.value = e instanceof Error ? e.message : t('removeDowntimeModal.error');
        removingId.value = null;
    }
}
</script>
