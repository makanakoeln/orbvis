<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('admin.icons') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('admin.iconsSubtitle') }}</p>
      </div>
      <label class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20 cursor-pointer">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
        {{ t('admin.uploadIcon') }}
        <input type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp" multiple class="hidden" @change="uploadIcons" />
      </label>
    </div>

    <!-- Upload feedback -->
    <div v-if="uploadError" class="mb-4 px-4 py-3 rounded-lg bg-red-500/10 ring-1 ring-red-500/20 text-red-400 text-sm flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
      {{ uploadError }}
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else-if="!icons.length" class="text-center py-16 text-zinc-600 text-sm">
      <svg class="w-10 h-10 mx-auto mb-3 text-zinc-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
      </svg>
      {{ t('admin.noIcons') }}
    </div>

    <div v-else class="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-3">
      <div
        v-for="icon in icons"
        :key="icon.name"
        class="group relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl p-3 flex flex-col items-center gap-2 hover:ring-zinc-600 transition-all"
      >
        <img :src="icon.url" :alt="icon.name"
          class="w-12 h-12 object-contain"
          :class="icon.name.endsWith('.svg') ? 'svg-icon' : ''" />
        <p class="text-[10px] text-zinc-500 font-mono text-center truncate w-full" :title="icon.name">{{ icon.name }}</p>
        <button
          class="absolute top-1.5 right-1.5 w-5 h-5 rounded bg-red-500/0 hover:bg-red-500/20 text-zinc-700 hover:text-red-400 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
          :title="t('common.delete')"
          @click="deleteIcon(icon.name)"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { iconsApi } from '@/api/client'
import type { IconEntry } from '@/types/api'

const { t } = useI18n()
const auth = useAuthStore()

const icons = ref<IconEntry[]>([])
const loading = ref(false)
const uploadError = ref('')

async function fetchIcons() {
  loading.value = true
  try {
    icons.value = await iconsApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function uploadIcons(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (!files?.length) return
  uploadError.value = ''
  try {
    for (const file of Array.from(files)) {
      await iconsApi.upload(file, auth.accessToken!)
    }
    await fetchIcons()
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Upload failed'
  }
  // Reset file input
  (event.target as HTMLInputElement).value = ''
}

async function deleteIcon(name: string) {
  if (!confirm(t('admin.deleteIcon', { name }))) return
  try {
    await iconsApi.delete(name, auth.accessToken!)
    icons.value = icons.value.filter(i => i.name !== name)
  } catch (e: unknown) {
    uploadError.value = e instanceof Error ? e.message : 'Delete failed'
  }
}

onMounted(fetchIcons)
</script>
