<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-80 space-y-5">

        <!-- Header -->
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-bold text-[var(--text)]">User Settings</h3>
            <p class="text-xs text-zinc-500 mt-0.5">{{ userName }}</p>
          </div>
          <button @click="$emit('close')"
            class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Theme selector (only for self) -->
        <div v-if="isSelf" class="space-y-2">
          <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Theme</label>
          <div class="flex gap-2">
            <button
              v-for="opt in themeOptions"
              :key="opt.value"
              @click="setTheme(opt.value)"
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

        <!-- Password change (hidden in SSO+self) -->
        <div v-if="showPasswordSection" class="space-y-3 pt-1 border-t border-[var(--border)]">
          <p class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Change Password</p>
          <form @submit.prevent="savePassword" class="space-y-3">
            <input v-model="password" type="password" placeholder="New password" required minlength="6"
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            <input v-model="confirm" type="password" placeholder="Confirm password" required
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />

            <p v-if="pwError" class="text-red-400 text-xs">{{ pwError }}</p>
            <p v-if="pwSuccess" class="text-green-400 text-xs">Password changed successfully.</p>

            <button v-if="!pwSuccess" type="submit" :disabled="pwSaving"
              class="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
              {{ pwSaving ? 'Saving…' : 'Change Password' }}
            </button>
          </form>
        </div>

        <!-- Logout (only for self and not in SSO mode – SSO shows it in the navbar) -->
        <div v-if="isSelf && !auth.ssoActive" class="pt-1 border-t border-[var(--border)]">
          <button @click="auth.logout()"
            class="w-full px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all text-left">
            Logout
          </button>
        </div>

      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { applyTheme } from '@/composables/useTheme'

const props = defineProps<{
  userId: number
  userName: string
  isSelf: boolean
}>()

defineEmits<{ close: [] }>()

const auth = useAuthStore()

// ---- Theme ----

const selectedTheme = ref(auth.user?.theme ?? 'system')

const SunIcon = () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' },
  [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z' })]
)
const MoonIcon = () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' },
  [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z' })]
)
const SystemIcon = () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '2' },
  [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' })]
)

const themeOptions = [
  { value: 'dark', label: 'Dark', icon: MoonIcon },
  { value: 'light', label: 'Light', icon: SunIcon },
  { value: 'system', label: 'Auto', icon: SystemIcon },
]

async function setTheme(theme: string) {
  selectedTheme.value = theme
  // Apply immediately to DOM — don't wait for the store watcher
  if (props.isSelf) applyTheme(theme, auth.ssoActive, auth.user?.cmk_theme)
  await usersApi.update(props.userId, { theme }, auth.accessToken!)
  if (props.isSelf) await auth.fetchCurrentUser()
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
    pwError.value = 'Passwords do not match.'
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
    pwError.value = e instanceof Error ? e.message : 'Failed to change password.'
  } finally {
    pwSaving.value = false
  }
}
</script>
