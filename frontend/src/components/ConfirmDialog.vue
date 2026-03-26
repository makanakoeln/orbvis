<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[60] flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('cancel')" />
      <div
        class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-80"
      >
        <!-- Icon -->
        <div class="flex items-center gap-3 mb-3">
          <div
            class="w-9 h-9 rounded-full bg-red-500/15 ring-1 ring-red-500/25 flex items-center justify-center shrink-0"
          >
            <svg
              class="w-4.5 h-4.5 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>
          <div>
            <p class="font-semibold text-[var(--text)] text-sm">{{ title }}</p>
            <p v-if="message" class="text-xs text-zinc-500 mt-0.5">{{ message }}</p>
          </div>
        </div>

        <div class="flex gap-2 justify-end mt-5">
          <button
            class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
            @click="$emit('cancel')"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            class="px-4 py-2 rounded-lg text-sm font-semibold bg-red-600 hover:bg-red-500 text-white transition-all"
            @click="$emit('confirm')"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

defineProps<{
  title: string;
  message?: string;
  confirmLabel?: string;
}>();

defineEmits<{ confirm: []; cancel: [] }>();

const { t } = useI18n();
</script>
