<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
            <div
                class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-[26rem] space-y-4"
            >
                <h3 class="text-base font-bold text-[var(--text)]">{{ t('comment.title') }}</h3>
                <p class="text-xs text-[var(--text-muted)] -mt-2">{{ displayName }}</p>

                <div>
                    <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{
                        t('comment.comment')
                    }}</label>
                    <input
                        ref="commentEl"
                        v-model="comment"
                        class="w-full px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)]"
                        :placeholder="t('comment.comment') + '…'"
                        @keydown.enter="submit"
                        @keydown.esc="$emit('close')"
                    />
                </div>

                <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
                <p v-if="success" class="text-xs text-green-400">{{ t('comment.success') }}</p>

                <div class="flex gap-3 justify-end pt-1 border-t border-[var(--border)]">
                    <CmkButton variant="secondary" @click="$emit('close')">{{
                        t('common.cancel')
                    }}</CmkButton>
                    <CmkButton
                        variant="primary"
                        :disabled="submitting || !comment.trim()"
                        @click="submit"
                    >
                        {{ submitting ? t('comment.submitting') : t('comment.submit') }}
                    </CmkButton>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import { computed, onMounted, ref } from 'vue';
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

const comment = ref('');
const submitting = ref(false);
const error = ref('');
const success = ref(false);
const commentEl = ref<HTMLInputElement | null>(null);

onMounted(() => {
    commentEl.value?.focus();
});

const displayName = computed(() => getBoardObjectName(props.object));

async function submit() {
    if (!comment.value.trim() || submitting.value) return;
    submitting.value = true;
    error.value = '';
    try {
        if (
            props.object.type === 'service' &&
            props.object.host_name &&
            props.object.service_description
        ) {
            await cmkApi.addCommentService(
                props.checkmkUrl,
                props.object.host_name,
                props.object.service_description,
                comment.value,
            );
        } else if (props.object.host_name) {
            await cmkApi.addCommentHost(props.checkmkUrl, props.object.host_name, comment.value);
        }
        success.value = true;
        setTimeout(() => emit('close'), 1200);
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : t('comment.error');
    } finally {
        submitting.value = false;
    }
}
</script>
