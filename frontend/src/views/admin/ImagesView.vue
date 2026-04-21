<template>
  <div>
    <div class="flex justify-between items-center mb-5">
      <div>
        <h2 class="text-base font-bold text-[var(--text)] tracking-tight">
          {{ t('admin.icons') }}
        </h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('admin.iconsSubtitle') }}</p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 ring-1 ring-[var(--default-border-color)] hover:ring-[var(--default-form-element-border-color)] rounded-lg text-sm font-medium text-zinc-300 hover:text-[var(--text)] transition-all duration-150"
        @click="fileInputEl?.click()"
      >
        <svg
          class="w-4 h-4"
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
        {{ t('admin.uploadIcon') }}
      </button>
      <input
        ref="fileInputEl"
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp"
        multiple
        class="hidden"
        @change="uploadIcons"
      />
    </div>

    <!-- Upload feedback -->
    <div
      v-if="uploadError"
      class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 ring-1 ring-red-500/20 text-red-400 text-sm flex items-center gap-2"
    >
      <svg
        class="w-4 h-4 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
      {{ uploadError }}
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg
        class="animate-spin w-4 h-4 text-[var(--color-corporate-green-50)]"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else-if="!icons.length" class="text-center py-16 text-zinc-600 text-sm">
      <svg
        class="w-10 h-10 mx-auto mb-3 text-zinc-700"
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
      {{ t('admin.noIcons') }}
    </div>

    <div v-else class="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-3">
      <div
        v-for="icon in icons"
        :key="icon.name"
        class="group relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-3 flex flex-col items-center gap-2 hover:ring-[var(--default-form-element-border-color)] transition-all"
      >
        <img
          :src="`${BASE_URL}${icon.url}`"
          :alt="icon.name"
          class="w-12 h-12 object-contain"
          :class="icon.name.endsWith('.svg') ? 'svg-icon' : ''"
        />
        <p
          class="text-[10px] text-zinc-500 font-mono text-center truncate w-full"
          :title="icon.name"
        >
          {{ icon.name }}
        </p>
        <button
          class="absolute top-1.5 right-1.5 w-5 h-5 rounded bg-red-500/0 hover:bg-red-500/20 text-zinc-700 hover:text-red-400 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
          :title="t('common.delete')"
          @click="deleteTargetName = icon.name"
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
    </div>
  </div>

  <ConfirmDialog
    v-if="deleteTargetName"
    :title="t('admin.deleteIcon', { name: deleteTargetName })"
    :message="t('board.cannotBeUndone')"
    :confirm-label="t('common.delete')"
    @confirm="confirmDeleteIcon"
    @cancel="deleteTargetName = null"
  />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { imagesApi } from '@/api/client';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import { useAuthStore } from '@/stores/auth';
import type { ImageEntry } from '@/types/api';

const BASE_URL = import.meta.env.BASE_URL;
const { t } = useI18n();
const auth = useAuthStore();

const fileInputEl = ref<HTMLInputElement | null>(null);
const icons = ref<ImageEntry[]>([]);
const loading = ref(false);
const uploadError = ref('');

async function fetchIcons() {
  loading.value = true;
  try {
    icons.value = await imagesApi.list(auth.accessToken!);
  } finally {
    loading.value = false;
  }
}

async function uploadIcons(event: Event) {
  const files = (event.target as HTMLInputElement).files;
  if (!files?.length) return;
  uploadError.value = '';
  try {
    const results = await Promise.allSettled(
      Array.from(files).map((file) => imagesApi.upload(file, auth.accessToken!)),
    );
    await fetchIcons();
    const failed = results.find((r): r is PromiseRejectedResult => r.status === 'rejected');
    if (failed) {
      uploadError.value = failed.reason instanceof Error ? failed.reason.message : 'Upload failed';
    }
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed';
  }
  // Reset file input
  (event.target as HTMLInputElement).value = '';
}

const deleteTargetName = ref<string | null>(null);

async function confirmDeleteIcon() {
  const name = deleteTargetName.value;
  if (!name) return;
  deleteTargetName.value = null;
  try {
    await imagesApi.delete(name, auth.accessToken!);
    icons.value = icons.value.filter((i) => i.name !== name);
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Delete failed';
  }
}

onMounted(fetchIcons);
</script>
