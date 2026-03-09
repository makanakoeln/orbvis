<template>
  <div class="min-h-screen bg-[var(--bg)] flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <div class="text-center mb-8">
        <div class="w-12 h-12 rounded-2xl bg-amber-500/15 ring-1 ring-amber-500/25 flex items-center justify-center mx-auto mb-4">
          <svg class="w-6 h-6 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
          </svg>
        </div>
        <h1 class="text-xl font-bold text-[var(--text)]">{{ t('changePassword.title') }}</h1>
        <p class="text-sm text-zinc-500 mt-1.5">{{ t('changePassword.subtitle') }}</p>
      </div>

      <div class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-2xl p-6 shadow-2xl shadow-black/50">
        <form @submit.prevent="save" class="space-y-4">
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('changePassword.newPassword') }}</label>
            <input v-model="password" type="password" placeholder="••••••••" required minlength="6" autofocus
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('changePassword.confirmPassword') }}</label>
            <input v-model="confirm" type="password" placeholder="••••••••" required
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
          </div>

          <p v-if="error" class="text-red-400 text-xs">{{ error }}</p>

          <button type="submit" :disabled="saving"
            class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
            {{ saving ? t('common.saving') : t('changePassword.setNewPassword') }}
          </button>
        </form>
      </div>

      <p class="text-center text-xs text-zinc-600 mt-4">
        {{ t('changePassword.loggedInAs') }} <span class="text-zinc-500">{{ auth.user?.name }}</span> ·
        <button @click="auth.logout" class="hover:text-zinc-400 transition-colors">{{ t('auth.logout') }}</button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/client'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const password = ref('')
const confirm = ref('')
const saving = ref(false)
const error = ref('')

async function save() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = t('changePassword.passwordMismatch')
    return
  }
  saving.value = true
  try {
    await usersApi.update(auth.user!.user_id, { password: password.value }, auth.accessToken!)
    await auth.fetchCurrentUser()
    router.push({ name: 'home' })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : t('changePassword.failedToChange')
  } finally {
    saving.value = false
  }
}
</script>
