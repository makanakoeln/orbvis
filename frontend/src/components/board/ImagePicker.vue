<template>
    <div class="space-y-2">
        <!-- Selected image preview + clear -->
        <div
            v-if="modelValue"
            class="flex items-center gap-2 px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--color-corporate-green-50)]/50 rounded-lg"
        >
            <img
                :src="`${BASE_URL}images/${modelValue}`"
                class="w-8 h-8 object-contain shrink-0"
                :class="modelValue.endsWith('.svg') ? 'svg-icon' : ''"
            />
            <span class="flex-1 text-xs font-mono text-[var(--text)] truncate">{{
                modelValue
            }}</span>
            <button
                class="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                type="button"
                @click="$emit('update:modelValue', '')"
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

        <!-- Toggle button (hidden once an image is selected — clear via X to pick another) -->
        <button
            v-if="!modelValue"
            type="button"
            class="w-full px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-lg text-sm text-left flex items-center gap-2 hover:ring-[var(--default-form-element-border-color)] transition-all focus:outline-none focus:ring-[var(--color-corporate-green-50)]"
            @click="open = !open"
        >
            <svg
                class="w-4 h-4 text-[var(--text-muted)] shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
            </svg>
            <span :class="modelValue ? 'text-[var(--text-muted)]' : 'text-[var(--text-muted)]'">
                {{ modelValue ? t('boardSettings.customIcon') : t('boardSettings.iconName') }}
            </span>
            <svg
                class="w-3.5 h-3.5 text-[var(--text-muted)] ml-auto transition-transform duration-150"
                :class="open ? 'rotate-180' : ''"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2.5"
            >
                <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M19.5 8.25l-7.5 7.5-7.5-7.5"
                />
            </svg>
        </button>

        <!-- Dropdown panel -->
        <Transition
            enter-from-class="opacity-0 -translate-y-1"
            enter-active-class="transition-all duration-200 ease-out"
            leave-to-class="opacity-0 -translate-y-1"
            leave-active-class="transition-all duration-150 ease-in"
        >
            <div
                v-if="open"
                class="rounded-lg ring-1 ring-[var(--default-border-color)] bg-[var(--bg-surface)] overflow-hidden"
            >
                <!-- Search -->
                <div class="p-2 border-b border-[var(--border)]">
                    <input
                        v-model="query"
                        :placeholder="t('boardSettings.searchIcons')"
                        class="w-full px-2.5 py-1.5 text-xs bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--default-form-element-border-color)] rounded-md text-[var(--text)] placeholder-[var(--default-form-element-placeholder-color)] focus:outline-none focus:ring-[var(--color-corporate-green-50)] transition-all"
                    />
                </div>

                <!-- Loading -->
                <div
                    v-if="loading"
                    class="flex items-center justify-center py-6 text-[var(--text-muted)] text-xs gap-2"
                >
                    <svg
                        class="animate-spin w-4 h-4 text-[var(--color-corporate-green-50)]"
                        fill="none"
                        viewBox="0 0 24 24"
                    >
                        <circle
                            class="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            stroke-width="4"
                        />
                        <path
                            class="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                        />
                    </svg>
                    {{ t('common.loading') }}
                </div>

                <!-- No images at all → upload prompt -->
                <template v-else-if="!images.length">
                    <div class="px-4 pt-5 pb-3 text-center">
                        <svg
                            class="w-8 h-8 mx-auto mb-2 text-[var(--text-muted)]"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="1.5"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                            />
                        </svg>
                        <p class="text-xs text-[var(--text-muted)] mb-3">
                            {{ t('admin.noIcons') }}
                        </p>
                        <label
                            class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-60)] rounded-lg text-xs font-semibold text-[var(--button-primary-text-color,#000)] transition-all cursor-pointer"
                        >
                            <svg
                                class="w-3.5 h-3.5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2.5"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                                />
                            </svg>
                            {{ t('boardSettings.uploadIconInline') }}
                            <input
                                type="file"
                                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                                multiple
                                class="hidden"
                                @change="uploadImages"
                            />
                        </label>
                    </div>

                    <!-- Upload progress / error -->
                    <Transition
                        enter-from-class="opacity-0 max-h-0"
                        enter-active-class="transition-all duration-300 ease-out overflow-hidden"
                        leave-to-class="opacity-0 max-h-0"
                        leave-active-class="transition-all duration-200 ease-in overflow-hidden"
                    >
                        <div v-if="uploading || uploadError" class="px-3 pb-3">
                            <div
                                v-if="uploading"
                                class="flex items-center gap-2 text-xs text-[var(--text-muted)] justify-center py-1"
                            >
                                <svg
                                    class="animate-spin w-3.5 h-3.5 text-[var(--color-corporate-green-50)]"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                >
                                    <circle
                                        class="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        stroke-width="4"
                                    />
                                    <path
                                        class="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                    />
                                </svg>
                                {{ t('common.saving') }}
                            </div>
                            <div
                                v-else-if="uploadError"
                                class="text-xs text-[var(--color-light-red-40)] text-center"
                            >
                                {{ uploadError }}
                            </div>
                        </div>
                    </Transition>
                </template>

                <!-- No search match -->
                <div
                    v-else-if="!filtered.length"
                    class="py-5 text-center text-xs text-[var(--text-muted)]"
                >
                    {{ t('home.noSearchResults', { q: query }) }}
                </div>

                <!-- Image grid + upload button at bottom -->
                <template v-else>
                    <div class="grid grid-cols-4 gap-1 p-2 max-h-52 overflow-y-auto">
                        <button
                            v-for="image in filtered"
                            :key="image.name"
                            type="button"
                            class="flex flex-col items-center gap-1 p-1.5 rounded-lg transition-all hover:bg-[var(--bg-hover)]"
                            :class="
                                modelValue === image.name
                                    ? 'ring-1 ring-[var(--color-corporate-green-50)] bg-[var(--color-corporate-green-50)]/10'
                                    : ''
                            "
                            :title="image.name"
                            @click="select(image.name)"
                        >
                            <img
                                :src="`${BASE_URL}${image.url}`"
                                :alt="image.name"
                                class="w-8 h-8 object-contain"
                                :class="image.name.endsWith('.svg') ? 'svg-icon' : ''"
                            />
                            <span
                                class="text-[9px] font-mono text-[var(--text-muted)] truncate w-full text-center leading-tight"
                                >{{ image.name }}</span
                            >
                        </button>
                    </div>

                    <!-- Upload more -->
                    <div
                        class="px-2 pb-2 border-t border-[var(--border)] pt-2 flex items-center justify-between"
                    >
                        <span class="text-[10px] text-[var(--text-muted)]"
                            >{{ images.length }} icon{{ images.length === 1 ? '' : 's' }}</span
                        >
                        <label
                            class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all cursor-pointer"
                        >
                            <svg
                                class="w-3 h-3"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                stroke-width="2.5"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
                                />
                            </svg>
                            {{ t('boardSettings.uploadIconInline') }}
                            <input
                                type="file"
                                accept="image/png,image/jpeg,image/svg+xml,image/webp"
                                multiple
                                class="hidden"
                                @change="uploadImages"
                            />
                        </label>
                        <div
                            v-if="uploading"
                            class="flex items-center gap-1 text-[10px] text-[var(--text-muted)]"
                        >
                            <svg
                                class="animate-spin w-3 h-3 text-[var(--color-corporate-green-50)]"
                                fill="none"
                                viewBox="0 0 24 24"
                            >
                                <circle
                                    class="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    stroke-width="4"
                                />
                                <path
                                    class="opacity-75"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                />
                            </svg>
                        </div>
                    </div>
                </template>
            </div>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { imagesApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import type { ImageEntry } from '@/types/api';

const BASE_URL = import.meta.env.BASE_URL;

const { t } = useI18n();
const auth = useAuthStore();

defineProps<{ modelValue: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();

const open = ref(false);
const query = ref('');
const images = ref<ImageEntry[]>([]);
const loading = ref(false);
const uploading = ref(false);
const uploadError = ref('');

const filtered = computed(() =>
    query.value
        ? images.value.filter((i) => i.name.toLowerCase().includes(query.value.toLowerCase()))
        : images.value,
);

async function fetchImages() {
    loading.value = true;
    try {
        images.value = await imagesApi.list(auth.accessToken!);
    } catch {
        images.value = [];
    } finally {
        loading.value = false;
    }
}

async function uploadImages(event: Event) {
    const files = (event.target as HTMLInputElement).files;
    if (!files?.length) return;
    uploadError.value = '';
    uploading.value = true;
    try {
        for (const file of Array.from(files)) {
            await imagesApi.upload(file, auth.accessToken!);
        }
        await fetchImages();
    } catch (e: unknown) {
        uploadError.value = e instanceof Error ? e.message : 'Upload failed';
    } finally {
        uploading.value = false;
        (event.target as HTMLInputElement).value = '';
    }
}

function select(name: string) {
    emit('update:modelValue', name);
    open.value = false;
    query.value = '';
}

watch(open, (isOpen) => {
    if (isOpen && !images.value.length) fetchImages();
});
</script>
