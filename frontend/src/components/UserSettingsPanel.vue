<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="tryClose" />
      <div
        class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl space-y-[12px]"
        style="padding: 16px; width: 300px"
      >
        <!-- Header -->
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-bold text-[var(--text)]">
              {{ isSelf ? t('userSettings.title') : t('admin.editUser', { name: userName }) }}
            </h3>
            <p v-if="isSelf" class="text-sm text-zinc-500" style="margin-top: 2px">
              {{ userName }}
            </p>
          </div>
          <button
            class="p-[4px] rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all"
            @click="tryClose"
          >
            <svg
              style="width: 14px; height: 14px"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Admin settings (non-self editing) -->
        <div v-if="!isSelf && userRead" class="space-y-[8px]">
          <p class="text-sm font-medium text-zinc-400">{{ t('admin.settings') }}</p>

          <div class="flex items-start gap-[8px]">
            <CmkCheckbox v-model="adminIsAdmin" :label="t('admin.administrator')" />
            <p class="text-sm text-zinc-600" style="margin-top: 2px">
              {{ t('admin.administratorHint') }}
            </p>
          </div>

          <CmkCheckbox v-model="adminIsActive" :label="t('admin.active')" />

          <CmkCheckbox v-model="adminMustChange" :label="t('admin.mustChangePassword')" />
        </div>

        <!-- Role assignment (non-self editing) -->
        <div
          v-if="!isSelf && userRead && availableRoles?.length"
          class="border-t border-[var(--border)] pt-[8px] space-y-[6px]"
        >
          <p class="text-sm font-medium text-zinc-400">{{ t('admin.roles') }}</p>
          <div v-for="role in availableRoles" :key="role.role_id">
            <CmkCheckbox
              :model-value="adminRoleIds.includes(role.role_id)"
              :label="role.name"
              @update:model-value="
                (v) => {
                  if (v) adminRoleIds.push(role.role_id);
                  else adminRoleIds = adminRoleIds.filter((id) => id !== role.role_id);
                }
              "
            />
          </div>
        </div>

        <!-- Theme selector (only for self) -->
        <div v-if="isSelf" class="space-y-[6px]">
          <CmkLabel>{{ t('userSettings.theme') }}</CmkLabel>
          <div class="flex gap-[6px]">
            <button
              v-for="opt in themeOptions"
              :key="opt.value"
              class="flex-1 flex items-center justify-center rounded-lg text-xs font-medium transition-all border"
              style="gap: 5px; padding: 6px 8px"
              :class="
                selectedTheme === opt.value
                  ? 'bg-zinc-600 border-zinc-500 text-zinc-100'
                  : 'bg-[var(--default-form-element-bg-color)] border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
              "
              @click="selectTheme(opt.value)"
            >
              <component :is="opt.icon" style="width: 13px; height: 13px" />
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Language selector (only for self, not in SSO mode where CMK controls it) -->
        <div v-if="isSelf && !auth.ssoActive && !auth.isCheckmkDeployment" class="space-y-[6px]">
          <CmkLabel>{{ t('userSettings.language') }}</CmkLabel>
          <div class="flex gap-[6px]">
            <button
              v-for="opt in languageOptions"
              :key="opt.value"
              class="flex-1 flex items-center justify-center rounded-lg text-xs font-medium transition-all border"
              style="padding: 6px 8px"
              :class="
                selectedLanguage === opt.value
                  ? 'bg-zinc-600 border-zinc-500 text-zinc-100'
                  : 'bg-[var(--default-form-element-bg-color)] border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'
              "
              @click="selectedLanguage = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Password change (hidden in SSO+self) -->
        <div
          v-if="showPasswordSection"
          class="space-y-[8px]"
          :class="isSelf ? 'pt-[12px] border-t border-[var(--border)]' : ''"
        >
          <p class="text-sm font-medium text-zinc-400">{{ t('userSettings.changePassword') }}</p>
          <form class="space-y-[8px]" @submit.prevent="savePassword">
            <div class="space-y-[4px]">
              <CmkLabel>{{ t('userSettings.newPassword') }}</CmkLabel>
              <CmkInput
                v-model="password"
                type="password"
                autocomplete="new-password"
                field-size="FILL"
              />
              <p class="text-sm text-zinc-600">{{ t('userSettings.passwordMinLength') }}</p>
            </div>
            <div class="space-y-[4px]">
              <CmkLabel>{{ t('userSettings.confirmPassword') }}</CmkLabel>
              <CmkInput
                v-model="confirm"
                type="password"
                autocomplete="new-password"
                field-size="FILL"
              />
            </div>

            <p v-if="pwError" class="text-red-400 text-sm">{{ pwError }}</p>
            <p v-if="pwSuccess" class="text-green-400 text-sm">
              {{ t('userSettings.passwordChanged') }}
            </p>

            <div v-if="!pwSuccess" class="flex justify-end">
              <button
                type="submit"
                :disabled="pwSaving"
                class="ring-1 ring-[var(--default-border-color)] hover:ring-[var(--default-form-element-border-color)] disabled:opacity-50 rounded-lg text-sm font-medium text-zinc-300 hover:text-[var(--text)] transition-all"
                style="padding: 5px 10px; font-size: 12px"
              >
                {{ pwSaving ? t('common.saving') : t('userSettings.changePasswordBtn') }}
              </button>
            </div>
          </form>
        </div>

        <!-- Tour reset (self only) -->
        <div v-if="isSelf" class="border-t border-[var(--border)] pt-[8px]">
          <p v-if="tourResetDone" class="text-sm text-green-400">
            {{ t('userSettings.tourResetDone') }}
          </p>
          <button
            v-else
            class="text-sm text-zinc-600 hover:text-zinc-400 transition-colors"
            @click="resetTour"
          >
            {{ t('userSettings.resetTour') }}
          </button>
        </div>

        <!-- Save error -->
        <p v-if="saveError || adminError" class="text-red-400 text-sm px-1">
          {{ saveError || adminError }}
        </p>

        <!-- Unsaved changes warning -->
        <div
          v-if="showUnsavedWarning"
          class="flex items-center gap-[6px] bg-amber-500/10 ring-1 ring-amber-500/30 rounded-lg text-amber-400 text-xs"
          style="padding: 6px 10px"
        >
          <svg
            class="shrink-0"
            style="width: 13px; height: 13px"
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
          {{ t('userSettings.unsavedChanges') }}
          <button class="underline hover:text-amber-300" @click="discardAndClose">
            {{ t('common.discard') }}
          </button>
        </div>

        <!-- Footer: Save / Cancel -->
        <div
          v-if="isSelf || (!isSelf && userRead)"
          class="flex gap-[6px] pt-[8px] border-t border-[var(--border)]"
        >
          <CmkButton variant="secondary" class="flex-1" @click="discardAndClose">
            {{ t('common.cancel') }}
          </CmkButton>
          <CmkButton
            variant="primary"
            class="flex-1"
            :disabled="isSelf ? saving || !isDirty : adminSaving"
            @click="isSelf ? save() : saveAdminSettings()"
          >
            {{ (isSelf ? saving : adminSaving) ? t('common.saving') : t('common.save') }}
          </CmkButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import CmkButton from '@cmk/components/CmkButton.vue';
import CmkLabel from '@cmk/components/CmkLabel.vue';
import CmkCheckbox from '@cmk/components/user-input/CmkCheckbox.vue';
import CmkInput from '@cmk/components/user-input/CmkInput.vue';
import { computed, h, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { usersApi } from '@/api/client';
import { applyTheme } from '@/composables/useTheme';
import { i18n } from '@/i18n';
import { useAuthStore } from '@/stores/auth';
import type { RoleRead, UserRead } from '@/types/api';

const { t } = useI18n();

const props = defineProps<{
  userId: number;
  userName: string;
  isSelf: boolean;
  userRead?: UserRead;
  availableRoles?: RoleRead[];
}>();

const emit = defineEmits<{ close: [] }>();

const auth = useAuthStore();

// ---- Admin settings (non-self) ----

const adminIsAdmin = ref(props.userRead?.is_admin ?? false);
const adminIsActive = ref(props.userRead?.is_active ?? true);
const adminMustChange = ref(props.userRead?.must_change_password ?? false);
const adminRoleIds = ref<number[]>(props.userRead?.roles.map((r) => r.role_id) ?? []);
const adminSaving = ref(false);
const adminError = ref('');

async function saveAdminSettings() {
  adminSaving.value = true;
  adminError.value = '';
  try {
    await usersApi.update(
      props.userId,
      {
        is_admin: adminIsAdmin.value,
        is_active: adminIsActive.value,
        must_change_password: adminMustChange.value,
      },
      auth.accessToken!,
    );
    const currentIds = props.userRead?.roles.map((r) => r.role_id) ?? [];
    const toAdd = adminRoleIds.value.filter((id) => !currentIds.includes(id));
    const toRemove = currentIds.filter((id) => !adminRoleIds.value.includes(id));
    await Promise.all([
      ...toAdd.map((rid) => usersApi.assignRole(props.userId, rid, auth.accessToken!)),
      ...toRemove.map((rid) => usersApi.removeRole(props.userId, rid, auth.accessToken!)),
    ]);
    emit('close');
  } catch (e: unknown) {
    adminError.value = e instanceof Error ? e.message : 'Save failed.';
  } finally {
    adminSaving.value = false;
  }
}

// ---- Theme ----

const savedTheme = ref(auth.user?.theme ?? 'system');
const selectedTheme = ref(auth.user?.theme ?? 'system');

// ---- Language ----

const savedLanguage = ref(auth.user?.language ?? 'en');
const selectedLanguage = ref(auth.user?.language ?? 'en');

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'de', label: 'Deutsch' },
];

const isDirty = computed(
  () => selectedTheme.value !== savedTheme.value || selectedLanguage.value !== savedLanguage.value,
);
const showUnsavedWarning = ref(false);
const saving = ref(false);
const saveError = ref('');

const SunIcon = () =>
  h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      d: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z',
    }),
  ]);
const MoonIcon = () =>
  h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      d: 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z',
    }),
  ]);
const SystemIcon = () =>
  h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', {
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      d: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
    }),
  ]);

const themeOptions = computed(() => [
  { value: 'dark', label: t('userSettings.themeDark'), icon: MoonIcon },
  { value: 'light', label: t('userSettings.themeLight'), icon: SunIcon },
  { value: 'system', label: t('userSettings.themeAuto'), icon: SystemIcon },
]);

function selectTheme(theme: string) {
  selectedTheme.value = theme;
  showUnsavedWarning.value = false;
  // Preview immediately in DOM without persisting
  if (props.isSelf) applyTheme(theme, auth.ssoActive, auth.user?.cmk_theme);
}

async function save() {
  saving.value = true;
  saveError.value = '';
  try {
    await usersApi.update(
      props.userId,
      { theme: selectedTheme.value, language: selectedLanguage.value },
      auth.accessToken!,
    );
    savedTheme.value = selectedTheme.value;
    savedLanguage.value = selectedLanguage.value;
    if (props.isSelf) {
      i18n.global.locale.value = selectedLanguage.value as 'en' | 'de';
      await auth.fetchCurrentUser();
    }
    showUnsavedWarning.value = false;
    emit('close');
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'Save failed.';
  } finally {
    saving.value = false;
  }
}

function tryClose() {
  if (props.isSelf && isDirty.value) {
    showUnsavedWarning.value = true;
  } else {
    emit('close');
  }
}

function discardAndClose() {
  // Revert theme preview to saved value
  if (props.isSelf) applyTheme(savedTheme.value, auth.ssoActive, auth.user?.cmk_theme);
  selectedTheme.value = savedTheme.value;
  selectedLanguage.value = savedLanguage.value;
  emit('close');
}

// ---- Tour reset ----

const tourResetDone = ref(false);

function resetTour() {
  localStorage.removeItem(`orbvis_onboarded_${props.userId}`);
  localStorage.removeItem(`orbvis_board_toured_${props.userId}`);
  tourResetDone.value = true;
}

// ---- Password ----

const showPasswordSection = computed(
  () => !(props.isSelf && (auth.ssoActive || auth.isCheckmkDeployment)),
);

const password = ref('');
const confirm = ref('');
const pwSaving = ref(false);
const pwError = ref('');
const pwSuccess = ref(false);

async function savePassword() {
  pwError.value = '';
  if (password.value !== confirm.value) {
    pwError.value = t('userSettings.passwordMismatch');
    return;
  }
  pwSaving.value = true;
  try {
    await usersApi.update(props.userId, { password: password.value }, auth.accessToken!);
    pwSuccess.value = true;
    if (props.isSelf) await auth.fetchCurrentUser();
    password.value = '';
    confirm.value = '';
  } catch (e: unknown) {
    pwError.value = e instanceof Error ? e.message : t('userSettings.failedToChange');
  } finally {
    pwSaving.value = false;
  }
}
</script>
