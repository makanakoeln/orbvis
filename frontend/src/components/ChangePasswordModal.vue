<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
      <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 w-80">
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="text-base font-bold text-zinc-100">Change Password</h3>
            <p class="text-xs text-zinc-500 mt-0.5">{{ userName }}</p>
          </div>
          <button @click="$emit('close')"
            class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-all">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form @submit.prevent="save" class="space-y-4">
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">New password</label>
            <input v-model="password" type="password" placeholder="••••••••" required minlength="6" autofocus
              class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
          </div>
          <div class="space-y-1.5">
            <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Confirm password</label>
            <input v-model="confirm" type="password" placeholder="••••••••" required
              class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
          </div>

          <p v-if="error" class="text-red-400 text-xs">{{ error }}</p>
          <p v-if="success" class="text-green-400 text-xs">Password changed successfully.</p>

          <div class="flex gap-3 justify-end pt-2 border-t border-white/5">
            <button type="button" @click="$emit('close')"
              class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all">
              {{ success ? 'Close' : 'Cancel' }}
            </button>
            <button v-if="!success" type="submit" :disabled="saving"
              class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  userId: number
  userName: string
}>()

const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const password = ref('')
const confirm = ref('')
const saving = ref(false)
const error = ref('')
const success = ref(false)

async function save() {
  error.value = ''
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.'
    return
  }
  saving.value = true
  try {
    await usersApi.update(props.userId, { password: password.value }, auth.accessToken!)
    success.value = true
    // Only refresh own user data — changing another user's password doesn't affect current session
    if (props.userId === auth.user?.user_id) await auth.fetchCurrentUser()
    password.value = ''
    confirm.value = ''
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to change password.'
  } finally {
    saving.value = false
  }
}
</script>
