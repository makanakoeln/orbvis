<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="tryClose" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-80 space-y-5">

        <!-- Header -->
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('userSettings.title') }}</h3>
            <p class="text-xs text-zinc-500 mt-0.5">{{ userName }}</p>
          </div>
          <button @click="tryClose"
            class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Theme selector (only for self) -->
        <div v-if="isSelf" class="space-y-2">
          <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('userSettings.theme') }}</label>
          <div class="flex gap-2">
            <button
              v-for="opt in themeOptions"
              :key="opt.value"
              @click="selectTheme(opt.value)"
              class="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all border"
              :class="selectedTheme === opt.value
                ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-300'
                : 'bg-[var(--bg-input)] border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'"
            >
              <component :is="opt.icon" class="w-3.5 h-3.5" />
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Language selector (only for self, not in SSO mode where CMK controls it) -->
        <div v-if="isSelf && !auth.ssoActive" class="space-y-2">
          <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('userSettings.language') }}</label>
          <div class="flex gap-2">
            <button
              v-for="opt in languageOptions"
              :key="opt.value"
              @click="selectedLanguage = opt.value"
              class="flex-1 flex items-center justify-center px-3 py-2 rounded-lg text-xs font-medium transition-all border"
              :class="selectedLanguage === opt.value
                ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-300'
                : 'bg-[var(--bg-input)] border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Password change (hidden in SSO+self) -->
        <div v-if="showPasswordSection" class="space-y-3 pt-4 border-t border-[var(--border)]">
          <p class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('userSettings.changePassword') }}</p>
          <form @submit.prevent="savePassword" class="space-y-3">
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('userSettings.newPassword') }}</label>
              <input v-model="password" type="password" autocomplete="new-password" required minlength="6"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              <p class="text-xs text-zinc-600">{{ t('userSettings.passwordMinLength') }}</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('userSettings.confirmPassword') }}</label>
              <input v-model="confirm" type="password" autocomplete="new-password" required
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <p v-if="pwError" class="text-red-400 text-xs">{{ pwError }}</p>
            <p v-if="pwSuccess" class="text-green-400 text-xs">{{ t('userSettings.passwordChanged') }}</p>

            <div v-if="!pwSuccess" class="flex justify-end">
              <button type="submit" :disabled="pwSaving"
                class="px-4 py-2 ring-1 ring-zinc-700 hover:ring-zinc-500 disabled:opacity-50 rounded-lg text-sm font-medium text-zinc-300 hover:text-[var(--text)] transition-all">
                {{ pwSaving ? t('common.saving') : t('userSettings.changePasswordBtn') }}
              </button>
            </div>
          </form>
        </div>

        <!-- Save error -->
        <p v-if="saveError" class="text-red-400 text-xs px-1">{{ saveError }}</p>

        <!-- Unsaved changes warning -->
        <div v-if="showUnsavedWarning" class="flex items-center gap-2 px-3 py-2 bg-amber-500/10 ring-1 ring-amber-500/30 rounded-lg text-amber-400 text-xs">
          <svg class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
          {{ t('userSettings.unsavedChanges') }}
          <button @click="discardAndClose" class="underline hover:text-amber-300">{{ t('common.discard') }}</button>
        </div>

        <!-- Footer: Save / Cancel -->
        <div v-if="isSelf" class="flex gap-2 pt-1 border-t border-[var(--border)]">
          <button @click="discardAndClose"
            class="flex-1 px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">
            {{ t('common.cancel') }}
          </button>
          <button @click="save" :disabled="saving || !isDirty"
            class="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-lg text-sm font-semibold text-white transition-all">
            {{ saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { applyTheme } from '@/composables/useTheme'
import { i18n } from '@/main'

const { t } = useI18n()

const props = defineProps<{
  userId: number
  userName: string
  isSelf: boolean
}>()

const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()

// ---- Theme ----

const savedTheme = ref(auth.user?.theme ?? 'system')
const selectedTheme = ref(auth.user?.theme ?? 'system')

// ---- Language ----

const savedLanguage = ref(auth.user?.language ?? 'en')
const selectedLanguage = ref(auth.user?.language ?? 'en')

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'de', label: 'Deutsch' },
]

const isDirty = computed(() =>
  selectedTheme.value !== savedTheme.value ||
  selectedLanguage.value !== savedLanguage.value
)
const showUnsavedWarning = ref(false)
const saving = ref(false)
const saveError = ref('')

const SunIcon = () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' },
  [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z' })]
)
const MoonIcon = () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' },
  [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z' })]
)
const SystemIcon = () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' },
  [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' })]
)

const themeOptions = computed(() => [
  { value: 'dark', label: t('userSettings.themeDark'), icon: MoonIcon },
  { value: 'light', label: t('userSettings.themeLight'), icon: SunIcon },
  { value: 'system', label: t('userSettings.themeAuto'), icon: SystemIcon },
])

function selectTheme(theme: string) {
  selectedTheme.value = theme
  showUnsavedWarning.value = false
  // Preview immediately in DOM without persisting
  if (props.isSelf) applyTheme(theme, auth.ssoActive, auth.user?.cmk_theme)
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    await usersApi.update(props.userId, { theme: selectedTheme.value, language: selectedLanguage.value }, auth.accessToken!)
    savedTheme.value = selectedTheme.value
    savedLanguage.value = selectedLanguage.value
    if (props.isSelf) {
      i18n.global.locale.value = selectedLanguage.value as 'en' | 'de'
      await auth.fetchCurrentUser()
    }
    showUnsavedWarning.value = false
    emit('close')
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'Save failed.'
  } finally {
    saving.value = false
  }
}

function tryClose() {
  if (isDirty.value) {
    showUnsavedWarning.value = true
  } else {
    emit('close')
  }
}

function discardAndClose() {
  // Revert theme preview to saved value
  if (props.isSelf) applyTheme(savedTheme.value, auth.ssoActive, auth.user?.cmk_theme)
  selectedTheme.value = savedTheme.value
  selectedLanguage.value = savedLanguage.value
  emit('close')
}

// ---- Password ----

const showPasswordSection = computed(() => !(props.isSelf && auth.ssoActive))

const password = ref('')
const confirm = ref('')
const pwSaving = ref(false)
const pwError = ref('')
const pwSuccess = ref(false)

async function savePassword() {
  pwError.value = ''
  if (password.value !== confirm.value) {
    pwError.value = t('userSettings.passwordMismatch')
    return
  }
  pwSaving.value = true
  try {
    await usersApi.update(props.userId, { password: password.value }, auth.accessToken!)
    pwSuccess.value = true
    if (props.isSelf) await auth.fetchCurrentUser()
    password.value = ''
    confirm.value = ''
  } catch (e: unknown) {
    pwError.value = e instanceof Error ? e.message : t('userSettings.failedToChange')
  } finally {
    pwSaving.value = false
  }
}
</script>
