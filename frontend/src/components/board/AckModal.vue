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
            <CmkInput
              ref="commentEl"
              v-model="comment"
              field-size="FILL"
              :placeholder="t('ack.comment') + '…'"
            />
          </div>
          <CmkCheckbox v-model="sticky" :label="t('ack.sticky')" />
          <CmkCheckbox v-model="notify" :label="t('ack.notify')" />
          <CmkCheckbox v-model="persistent" :label="t('ack.persistent')" />
        </div>

        <p v-if="error" class="text-xs text-red-400">{{ error }}</p>
        <p v-if="success" class="text-xs text-green-400">{{ t('ack.success') }}</p>

        <div class="flex gap-3 justify-end pt-1 border-t border-[var(--border)]">
          <CmkButton variant="secondary" @click="$emit('close')">{{
            t('common.cancel')
          }}</CmkButton>
          <CmkButton variant="primary" :disabled="submitting || !comment.trim()" @click="submit">
            {{ submitting ? t('ack.submitting') : t('ack.submit') }}
          </CmkButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { cmkApi } from '@/api/client';
import type { BoardObject } from '@/types/api';
import { getBoardObjectName } from '@/utils/naming';

const props = defineProps<{
  object: BoardObject;
  checkmkUrl: string;
}>();

const emit = defineEmits<{ close: [] }>();

const { t } = useI18n();
const comment = ref('');
const sticky = ref(true);
const notify = ref(true);
const persistent = ref(false);
const submitting = ref(false);
const error = ref('');
const success = ref(false);
const commentEl = ref<HTMLInputElement | null>(null);

const displayName = computed(() => getBoardObjectName(props.object));

onMounted(() => commentEl.value?.focus());

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
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    submitting.value = false;
  }
}
</script>
