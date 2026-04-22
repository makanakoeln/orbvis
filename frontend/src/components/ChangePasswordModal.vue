<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div
        class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-80"
      >
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="text-base font-bold text-[var(--text)]">
              {{ t('userSettings.changePassword') }}
            </h3>
            <p class="text-xs text-zinc-500 mt-0.5">{{ userName }}</p>
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

        <form class="space-y-4" @submit.prevent="save">
          <div class="space-y-1.5">
            <CmkLabel>{{ t('userSettings.newPassword') }}</CmkLabel>
            <CmkInput v-model="password" type="password" placeholder="••••••••" field-size="FILL" />
          </div>
          <div class="space-y-1.5">
            <CmkLabel>{{ t('userSettings.confirmPassword') }}</CmkLabel>
            <CmkInput v-model="confirm" type="password" placeholder="••••••••" field-size="FILL" />
          </div>

          <p v-if="error" class="text-red-400 text-xs">{{ error }}</p>
          <p v-if="success" class="text-green-400 text-xs">
            {{ t('userSettings.passwordChanged') }}
          </p>

          <div class="flex gap-3 justify-end pt-2 border-t border-[var(--border)]">
            <CmkButton variant="secondary" @click="$emit('close')">
              {{ success ? t('common.close') : t('common.cancel') }}
            </CmkButton>
            <CmkButton v-if="!success" variant="primary" :disabled="saving" @click="save">
              {{ saving ? t('common.saving') : t('common.save') }}
            </CmkButton>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { usersApi } from '@/api/client';
import { useAuthStore } from '@/stores/auth';

const props = defineProps<{
  userId: number;
  userName: string;
}>();

defineEmits<{ close: [] }>();

const { t } = useI18n();
const auth = useAuthStore();
const password = ref('');
const confirm = ref('');
const saving = ref(false);
const error = ref('');
const success = ref(false);

async function save() {
  error.value = '';
  if (password.value !== confirm.value) {
    error.value = t('userSettings.passwordMismatch');
    return;
  }
  saving.value = true;
  try {
    await usersApi.update(props.userId, { password: password.value }, auth.accessToken!);
    success.value = true;
    // Only refresh own user data — changing another user's password doesn't affect current session
    if (props.userId === auth.user?.user_id) await auth.fetchCurrentUser();
    password.value = '';
    confirm.value = '';
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('userSettings.failedToChange');
  } finally {
    saving.value = false;
  }
}
</script>
