<template>
    <OrbModal :open="true" :title="t('comment.title')" closable @close="$emit('close')">
        <p class="comment-modal__subtitle">{{ displayName }}</p>

        <div class="comment-modal__field">
            <label class="comment-modal__label">{{ t('comment.comment') }}</label>
            <input
                ref="commentEl"
                v-model="comment"
                class="comment-modal__input"
                :placeholder="t('comment.comment') + '…'"
                @keydown.enter="submit"
            />
        </div>

        <p v-if="error" class="comment-modal__error">{{ error }}</p>
        <p v-if="success" class="comment-modal__success">{{ t('comment.success') }}</p>

        <template #footer>
            <CmkButton variant="secondary" @click="$emit('close')">
                {{ t('common.cancel') }}
            </CmkButton>
            <CmkButton variant="primary" :disabled="submitting || !comment.trim()" @click="submit">
                {{ submitting ? t('comment.submitting') : t('comment.submit') }}
            </CmkButton>
        </template>
    </OrbModal>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import CmkButton from '@/components/cmk/CmkButton';
import OrbModal from '@/components/OrbModal.vue';
import { useStatesStore } from '@/stores/states';
import type { BoardObject } from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';

const { t } = useI18n();

const props = defineProps<{
    object: BoardObject;
    checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();

const comment = ref('');
const submitting = ref(false);
const error = ref('');
const success = ref(false);
const commentEl = ref<HTMLInputElement | null>(null);
const statesStore = useStatesStore();

onMounted(() => {
    commentEl.value?.focus();
});

const displayName = computed(() => getBoardObjectName(props.object));

async function submit() {
    if (!comment.value.trim() || submitting.value) return;
    submitting.value = true;
    error.value = '';
    try {
        const siteId = statesStore.getState(props.object.id)?.site_id ?? null;
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
                siteId,
            );
        } else if (props.object.host_name) {
            await cmkApi.addCommentHost(
                props.checkmkUrl,
                props.object.host_name,
                comment.value,
                siteId,
            );
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

<style scoped>
.comment-modal__subtitle {
    font-size: var(--font-size-normal);
    color: var(--text-muted);
    margin: calc(-1 * var(--dimension-4)) 0 0;
}

.comment-modal__field {
    display: flex;
    flex-direction: column;
    gap: var(--dimension-3);
    margin-top: var(--dimension-5);
}

.comment-modal__label {
    font-size: var(--font-size-normal);
    font-weight: 500;
    color: var(--text-muted);
}

.comment-modal__input {
    width: 100%;
    padding: var(--dimension-4) var(--dimension-5);
    background: var(--default-form-element-bg-color);
    border: 1px solid var(--default-form-element-border-color);
    border-radius: var(--dimension-3);
    font-size: var(--font-size-large);
    color: var(--text);
}

.comment-modal__input:focus {
    outline: none;
    border-color: var(--color-corporate-green-50);
    box-shadow: 0 0 0 2px var(--color-corporate-green-50);
}

.comment-modal__error {
    font-size: var(--font-size-normal);
    color: var(--color-light-red-40);
    margin-top: var(--dimension-4);
}

.comment-modal__success {
    font-size: var(--font-size-normal);
    color: var(--color-corporate-green-50);
    margin-top: var(--dimension-4);
}
</style>
