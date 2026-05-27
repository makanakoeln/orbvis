<template>
    <div class="space-y-2">
        <!-- Preview when a background is set or staged -->
        <div
            v-if="hasImage"
            class="flex items-center gap-3 px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--color-corporate-green-50)]/50 rounded-lg"
        >
            <img
                v-if="!previewFailed && displayUrl"
                :src="displayUrl"
                class="w-12 h-12 object-cover rounded shrink-0"
                @error="previewFailed = true"
            />
            <div
                v-else-if="previewFailed"
                class="w-12 h-12 rounded shrink-0 bg-[var(--bg-hover)] flex items-center justify-center text-[10px] text-[var(--text-muted)]"
            >
                ?
            </div>
            <span class="flex-1 min-w-0 text-xs font-mono text-[var(--text)] truncate">
                {{ displayName }}
                <span v-if="pendingFile" class="text-[var(--text-muted)]">
                    · {{ t('board.backgroundUnsaved') }}
                </span>
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
                :title="pendingFile ? t('common.cancel') : t('board.deleteBackground')"
                @click="removeOrCancel"
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

        <!-- Upload button when empty (or pending removal) -->
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
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

const ACCEPT_TYPES = 'image/png,image/jpeg,image/svg+xml,image/webp,image/gif';

const { t } = useI18n();

const props = defineProps<{
    // Filename of the background already persisted on the server (display base).
    modelValue: string;
    // Staged selection: uploaded/deleted only when the parent saves the board.
    pendingFile: File | null;
    pendingRemove: boolean;
    // data: URL of the staged file, provided by the parent. A data: URL (not a
    // blob:) is required because Checkmk's CSP allows ``img-src ... data:`` but
    // not blob:, so a blob: thumbnail would be silently blocked on OMD sites.
    pendingPreviewUrl?: string | null;
}>();
const emit = defineEmits<{
    'update:pendingFile': [value: File | null];
    'update:pendingRemove': [value: boolean];
}>();

const BASE_URL = import.meta.env.BASE_URL;
const cacheBust = ref(Date.now());
const previewFailed = ref(false);

watch(
    () => props.pendingFile,
    () => {
        previewFailed.value = false;
    },
);
watch(
    () => props.modelValue,
    () => {
        previewFailed.value = false;
        cacheBust.value = Date.now();
    },
);

const hasImage = computed(() =>
    props.pendingFile ? true : props.pendingRemove ? false : !!props.modelValue,
);
const displayUrl = computed(() =>
    props.pendingFile
        ? (props.pendingPreviewUrl ?? '')
        : `${BASE_URL}boards/backgrounds/${props.modelValue}?v=${cacheBust.value}`,
);
const displayName = computed(() => props.pendingFile?.name ?? props.modelValue);

function onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    emit('update:pendingRemove', false);
    emit('update:pendingFile', file);
}

function removeOrCancel() {
    if (props.pendingFile) {
        // Undo the staged pick, falling back to the persisted image.
        emit('update:pendingFile', null);
        return;
    }
    emit('update:pendingRemove', true);
}
</script>
