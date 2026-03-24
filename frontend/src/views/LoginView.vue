<template>
  <div class="min-h-screen flex items-start justify-center bg-[var(--bg)] relative overflow-hidden pt-[18vh]">
    <!-- Background glow -->
    <div class="absolute inset-0 bg-gradient-to-br from-indigo-950/50 via-zinc-950 to-zinc-950 pointer-events-none" />
    <div class="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/8 rounded-full blur-3xl pointer-events-none" />

    <div class="relative w-full max-w-sm mx-4">
      <!-- Logo -->
      <div class="text-center mb-8">
        <svg class="w-12 h-12 text-indigo-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2 12C5 7 19 7 22 12C19 17 5 17 2 12Z" />
          <circle cx="12" cy="12" r="3.5" stroke-width="1" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.2" d="M9.5 13.5L11 11L12.5 12.5L14 10" />
          <circle cx="14" cy="10" r="0.8" fill="currentColor" stroke="none" />
        </svg>
        <h1 class="text-2xl font-bold text-[var(--text)] tracking-tight">OrbVis</h1>
        <p class="text-sm text-zinc-500 mt-1">{{ t('auth.monitoringVisualization') }}</p>
        <button @click="showChangelog = true" class="text-xs text-zinc-600 hover:text-zinc-400 transition-colors mt-1">
          v{{ appVersion }}
        </button>
      </div>

      <!-- Card -->
      <div class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-8">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div class="space-y-1.5">
            <label for="login-username" class="text-xs font-medium text-zinc-300">{{ t('auth.username') }}</label>
            <input
              id="login-username"
              ref="usernameEl"
              v-model="username"
              type="text"
              autocomplete="username"
              required
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-600 rounded-lg text-[var(--text)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-0 transition-all duration-150"
            />
          </div>
          <div class="space-y-1.5">
            <label for="login-password" class="text-xs font-medium text-zinc-300">{{ t('auth.password') }}</label>
            <div class="relative">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
                class="w-full px-3.5 py-2.5 pr-10 bg-[var(--bg-input)] ring-1 ring-zinc-600 rounded-lg text-[var(--text)] text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute inset-y-0 right-0 flex items-center px-3 text-zinc-500 hover:text-zinc-300 transition-colors"
                :title="showPassword ? t('auth.hidePassword') : t('auth.showPassword')"
              >
                <!-- Eye (show) -->
                <svg v-if="!showPassword" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <!-- Eye-slash (hide) -->
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                </svg>
              </button>
            </div>
          </div>

          <div v-if="authStore.error"
            class="flex items-start gap-2.5 px-3.5 py-3 bg-red-500/8 ring-1 ring-red-500/20 rounded-lg text-red-400 text-sm">
            <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            {{ authStore.error }}
          </div>

          <button
            type="submit"
            :disabled="authStore.loading"
            class="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-all duration-150 shadow-lg shadow-indigo-900/30"
          >
            {{ authStore.loading ? t('auth.signingIn') : t('auth.signIn') }}
          </button>
        </form>
      </div>
    </div>

    <ChangelogModal v-if="showChangelog" @close="showChangelog = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import ChangelogModal from '@/components/ChangelogModal.vue'

const { t } = useI18n()
const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const showPassword = ref(false)
const showChangelog = ref(false)
const appVersion = __APP_VERSION__
const usernameEl = ref<HTMLInputElement | null>(null)

onMounted(() => usernameEl.value?.focus())

async function handleLogin() {
  await authStore.login(username.value, password.value)
}
</script>
