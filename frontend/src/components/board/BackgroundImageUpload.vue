<template>
    <div class="space-y-2">
        <!-- Preview when a background is set -->
        <div
            v-if="modelValue"
            class="flex items-center gap-3 px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--color-corporate-green-50)]/50 rounded-lg"
        >
            <img
                v-if="!previewFailed"
                :src="previewUrl"
                class="w-12 h-12 object-cover rounded shrink-0"
                @error="previewFailed = true"
            />
            <div
                v-else
                class="w-12 h-12 rounded shrink-0 bg-[var(--bg-hover)] flex items-center justify-center text-[10px] text-[var(--text-muted)]"
            >
                ?
            </div>
            <span class="flex-1 text-xs font-mono text-[var(--text)] truncate">
                {{ modelValue }}
            </span>
            <label
                class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors cursor-pointer"
            >
                {{ t('board.replaceBackground') }}
                <input type="file" :accept="ACCEPT_TYPES" class="hidden" @change="onFileChange" />
            </label>
            <button
                type="button"
                class="text-[var(--text-muted)] hover:text-[var(--color-light-red-40)] transition-colors"
                :title="t('board.deleteBackground')"
                @click="remove"
            >
                <svg
                    class="w-3.5 h-3.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        <!-- Upload button when empty -->
        <label
            v-else
            class="w-full inline-flex items-center justify-center gap-2 px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-[var(--text-muted)] hover:ring-[var(--color-corporate-green-50)] hover:text-[var(--text)] transition-all cursor-pointer focus-within:ring-[var(--color-corporate-green-50)]"
        >
            <svg
                class="w-4 h-4 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                />
            </svg>
            {{ t('board.uploadBackground') }}
            <input type="file" :accept="ACCEPT_TYPES" class="hidden" @change="onFileChange" />
        </label>

        <p v-if="error" class="text-xs text-[var(--color-light-red-40)]">{{ error }}</p>
        <p v-else-if="uploading" class="text-xs text-[var(--text-muted)]">
            {{ t('common.saving') }}…
        </p>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { boardsApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';

const ACCEPT_TYPES = 'image/png,image/jpeg,image/svg+xml,image/webp,image/gif';

const { t } = useI18n();
const auth = useAuthStore();

const props = defineProps<{
    modelValue: string;
    boardName: string;
}>();
// `replaced` fires on every successful upload, even when the resulting
// filename is unchanged. The backend stores the bg under a fixed
// `<board>.<ext>` name, so an in-place replacement leaves modelValue
// identical — without a side-channel signal the parent's isDirty check
// wouldn't see the change and the Save button would stay disabled.
const emit = defineEmits<{
    'update:modelValue': [value: string];
    replaced: [];
}>();

const BASE_URL = import.meta.env.BASE_URL;
const cacheBust = ref(Date.now());
const uploading = ref(false);
const error = ref('');
const previewFailed = ref(false);

const previewUrl = computed(
    () => `${BASE_URL}boards/backgrounds/${props.modelValue}?v=${cacheBust.value}`,
);

watch(
    () => props.modelValue,
    () => {
        previewFailed.value = false;
        cacheBust.value = Date.now();
    },
);

async function onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    error.value = '';
    uploading.value = true;
    try {
        const { filename } = await boardsApi.uploadBackground(
            props.boardName,
            file,
            auth.accessToken!,
        );
        cacheBust.value = Date.now();
        emit('update:modelValue', filename);
        emit('replaced');
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : 'Upload failed';
    } finally {
        uploading.value = false;
        input.value = '';
    }
}

async function remove() {
    error.value = '';
    try {
        await boardsApi.deleteBackground(props.boardName, auth.accessToken!);
        emit('update:modelValue', '');
    } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : 'Delete failed';
    }
}
</script>
