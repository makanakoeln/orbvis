<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div
        class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl p-6 w-[26rem] space-y-4"
      >
        <h3 class="text-base font-bold text-[var(--text)]">{{ t('ack.title') }}</h3>
        <p class="text-xs text-[var(--text-muted)] -mt-2">{{ displayName }}</p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-medium text-[var(--text-muted)] mb-1.5">{{
              t('ack.comment')
            }}</label>
            <input
              ref="commentEl"
              v-model="comment"
              class="w-full px-3 py-2 bg-[var(--default-form-element-bg-color)] ring-1 ring-[var(--border)] rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-[var(--color-corporate-green-50)]"
              :placeholder="t('ack.comment') + '…'"
              @keydown.enter="submit"
              @keydown.esc="$emit('close')"
            />
          </div>
          <label
            class="flex items-center gap-2.5 text-sm text-[var(--text-muted)] cursor-pointer select-none"
          >
            <input
              v-model="sticky"
              type="checkbox"
              class="rounded accent-[var(--color-corporate-green-50)] w-4 h-4"
            />
            {{ t('ack.sticky') }}
          </label>
          <label
            class="flex items-center gap-2.5 text-sm text-[var(--text-muted)] cursor-pointer select-none"
          >
            <input
              v-model="notify"
              type="checkbox"
              class="rounded accent-[var(--color-corporate-green-50)] w-4 h-4"
            />
            {{ t('ack.notify') }}
          </label>
          <label
            class="flex items-center gap-2.5 text-sm text-[var(--text-muted)] cursor-pointer select-none"
          >
            <input
              v-model="persistent"
              type="checkbox"
              class="rounded accent-[var(--color-corporate-green-50)] w-4 h-4"
            />
            {{ t('ack.persistent') }}
          </label>
        </div>

        <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
        <p v-if="success" class="text-xs text-green-400">{{ t('ack.success') }}</p>

        <div class="flex gap-3 justify-end pt-1 border-t border-[var(--border)]">
          <button
            class="px-4 py-2 rounded-lg text-sm text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all"
            @click="$emit('close')"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            :disabled="submitting || !comment.trim()"
            class="px-5 py-2 bg-[var(--color-corporate-green-50)] hover:bg-[var(--color-corporate-green-60)] disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-sm font-semibold text-[var(--button-primary-text-color,#000)] transition-all"
            @click="submit"
          >
            {{ submitting ? t('ack.submitting') : t('ack.submit') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import type { BoardObject } from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';

const { t } = useI18n();

const props = defineProps<{
  object: BoardObject;
  checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();

const comment = ref('');
const sticky = ref(true);
const notify = ref(true);
const persistent = ref(false);
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
      await cmkApi.acknowledgeService(
        props.checkmkUrl,
        props.object.host_name,
        props.object.service_description,
        comment.value,
        sticky.value,
        notify.value,
        persistent.value,
      );
    } else if (props.object.host_name) {
      await cmkApi.acknowledgeHost(
        props.checkmkUrl,
        props.object.host_name,
        comment.value,
        sticky.value,
        notify.value,
        persistent.value,
      );
    }
    success.value = true;
    setTimeout(() => emit('close'), 1200);
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('ack.error');
  } finally {
    submitting.value = false;
  }
}
</script>
