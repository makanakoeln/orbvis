<template>
  <div class="min-h-screen flex items-center justify-center bg-[var(--bg)] relative overflow-hidden">
    <!-- Background glow -->
    <div class="absolute inset-0 bg-gradient-to-br from-indigo-950/50 via-zinc-950 to-zinc-950 pointer-events-none" />
    <div class="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/8 rounded-full blur-3xl pointer-events-none" />

    <div class="relative w-full max-w-sm mx-4">
      <!-- Logo -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600/15 ring-1 ring-indigo-500/25 mb-4">
          <svg class="w-7 h-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-[var(--text)] tracking-tight">OrbVis</h1>
        <p class="text-sm text-zinc-500 mt-1">Monitoring Visualization</p>
      </div>

      <!-- Card -->
      <div class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-8">
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Username</label>
            <input
              v-model="username"
              type="text"
              autocomplete="username"
              required
              placeholder="admin"
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-[var(--text)] placeholder-zinc-600 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-0 transition-all duration-150"
            />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Password</label>
            <input
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              placeholder="••••••••"
              class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-[var(--text)] placeholder-zinc-600 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150"
            />
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
            {{ authStore.loading ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const username = ref('')
const password = ref('')

async function handleLogin() {
  await authStore.login(username.value, password.value)
}
</script>
