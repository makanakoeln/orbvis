<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-900">
    <div class="w-full max-w-sm bg-gray-800 rounded-lg shadow-xl p-8">
      <h1 class="text-2xl font-bold text-center mb-6">NagVis 2</h1>
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1">Username</label>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            required
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1">Password</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            required
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        <div v-if="authStore.error" class="text-red-400 text-sm text-center">
          {{ authStore.error }}
        </div>
        <button
          type="submit"
          :disabled="authStore.loading"
          class="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white font-semibold rounded-md transition-colors"
        >
          {{ authStore.loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
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
