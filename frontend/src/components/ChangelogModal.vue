<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="$emit('close')">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
    <div
      class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-2xl shadow-2xl shadow-black/50 w-full max-w-2xl max-h-[80vh] flex flex-col"
    >
      <!-- Header -->
      <div
        class="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] shrink-0"
      >
        <div>
          <h2 class="text-base font-semibold text-[var(--text)]">Changelog</h2>
          <p class="text-xs text-zinc-500 mt-0.5">OrbVis v{{ appVersion }}</p>
        </div>
        <button
          class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
          @click="$emit('close')"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto px-6 py-5">
        <div v-if="loading" class="flex items-center justify-center py-12 text-zinc-500 text-sm">
          Loading…
        </div>
        <div v-else-if="error" class="text-red-400 text-sm">{{ error }}</div>
        <pre v-else class="text-xs text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">{{
          content
        }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

defineEmits<{ close: [] }>();

const appVersion = __APP_VERSION__;
const content = ref('');
const loading = ref(true);
const error = ref('');

onMounted(async () => {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}api/changelog`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    content.value = await res.text();
  } catch (e) {
    error.value = String(e);
  } finally {
    loading.value = false;
  }
});
</script>
