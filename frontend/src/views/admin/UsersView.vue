<template>
  <div class="max-w-4xl">
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-[var(--text)] tracking-tight">{{ t('admin.users') }}</h2>
        <p class="text-sm text-zinc-500 mt-1">{{ t('admin.usersSubtitle') }}</p>
      </div>
      <button
        @click="showCreate = true"
        class="flex items-center gap-2 px-4 py-2 ring-1 ring-zinc-700 hover:ring-zinc-500 rounded-lg text-sm font-medium text-zinc-300 hover:text-[var(--text)] transition-all duration-150"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        {{ t('admin.newUser') }}
      </button>
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      {{ t('common.loading') }}
    </div>

    <div v-else class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--border)]">
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.name') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.type') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.status') }}</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.roles') }}</th>
            <th class="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">{{ t('admin.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--border)]">
          <tr
            v-for="user in users"
            :key="user.user_id"
            class="hover:bg-[var(--bg-hover)] transition-colors"
          >
            <td class="px-4 py-3 font-medium text-[var(--text)]">{{ user.name }}</td>
            <td class="px-4 py-3">
              <span v-if="user.is_admin"
                class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20">
                {{ t('admin.admin') }}
              </span>
              <span v-else class="text-xs text-zinc-600">{{ t('admin.user') }}</span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center gap-1.5 text-xs font-medium"
                :class="user.is_active ? 'text-green-400' : 'text-red-400'">
                <span class="w-1.5 h-1.5 rounded-full"
                  :class="user.is_active ? 'bg-green-400' : 'bg-red-400'" />
                {{ user.is_active ? t('admin.active') : t('admin.inactive') }}
              </span>
            </td>
            <td class="px-4 py-3 text-zinc-500 text-xs">
              <template v-if="user.roles.length">
                <span v-for="(r, i) in user.roles" :key="r.role_id"
                  class="inline-block px-1.5 py-0.5 rounded bg-[var(--bg-input)] ring-1 ring-zinc-700 text-zinc-400 mr-1 mb-0.5">
                  {{ r.name }}
                </span>
              </template>
              <span v-else class="text-zinc-700">—</span>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-1">
                <template v-if="user.user_id !== auth.user?.user_id">
                  <button v-if="canEditUsers"
                    @click="editUser = user"
                    class="p-1.5 rounded-md text-zinc-600 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all"
                    :title="t('common.edit')">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
                    </svg>
                  </button>
                  <button
                    @click="deleteUser(user.user_id)"
                    class="p-1.5 rounded-md text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-all"
                    :title="t('common.delete')">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </template>
                <span v-else class="text-xs text-zinc-700 pr-1">—</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create dialog -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showCreate = false" />
        <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/50 rounded-2xl p-6 w-96">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-[var(--text)]">{{ t('admin.createUser') }}</h3>
            <button @click="showCreate = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <form @submit.prevent="createUser" class="space-y-3">

            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('auth.username') }}</label>
              <input v-model="newUser.name" placeholder="john" required autocomplete="off"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{{ t('auth.password') }}</label>
              <input v-model="newUser.password" type="password" required minlength="6" autocomplete="new-password"
                class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
              <p class="text-xs text-zinc-600">{{ t('userSettings.passwordMinLength') }}</p>
            </div>

            <div class="border-t border-[var(--border)] pt-3 space-y-3">

              <label class="flex items-start gap-3 cursor-pointer group select-none">
                <input type="checkbox" v-model="newUser.is_admin" class="rounded accent-indigo-500 w-4 h-4 mt-0.5 shrink-0" />
                <div>
                  <p class="text-sm text-zinc-300 group-hover:text-[var(--text)] transition-colors">{{ t('admin.administrator') }}</p>
                  <p class="text-xs text-zinc-600 mt-0.5">{{ t('admin.administratorHint') }}</p>
                </div>
              </label>

              <label class="flex items-center gap-3 cursor-pointer select-none">
                <input type="checkbox" v-model="newUser.must_change_password" class="rounded accent-indigo-500 w-4 h-4 shrink-0" />
                <p class="text-sm text-zinc-400">{{ t('admin.mustChangePassword') }}</p>
              </label>

            </div>

            <p v-if="createError" class="text-xs text-red-400">{{ createError }}</p>
            <div class="flex gap-3 justify-end pt-2 border-t border-[var(--border)]">
              <button type="button" @click="showCreate = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">{{ t('common.cancel') }}</button>
              <button type="submit" :disabled="creating"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
                {{ creating ? t('common.saving') : t('common.create') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <UserSettingsPanel
      v-if="editUser"
      :user-id="editUser.user_id"
      :user-name="editUser.name"
      :is-self="false"
      @close="editUser = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { UserRead } from '@/types/api'
import UserSettingsPanel from '@/components/UserSettingsPanel.vue'

const { t } = useI18n()
const auth = useAuthStore()
const users = ref<UserRead[]>([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const newUser = ref({ name: '', password: '', is_admin: false, must_change_password: false })
const editUser = ref<UserRead | null>(null)
const canEditUsers = computed(() =>
  auth.user?.permissions?.some(p => p.mod === 'user' && p.act === 'edit' && p.obj === '*') ?? false
)

async function fetchUsers() {
  loading.value = true
  try {
    users.value = await usersApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function createUser() {
  creating.value = true
  createError.value = ''
  try {
    await usersApi.create(newUser.value, auth.accessToken!)
    showCreate.value = false
    newUser.value = { name: '', password: '', is_admin: false, must_change_password: false }
    await fetchUsers()
  } catch (e: unknown) {
    createError.value = e instanceof Error ? e.message : t('admin.saveFailed')
  } finally {
    creating.value = false
  }
}

async function deleteUser(id: number) {
  if (!confirm(t('admin.deleteUser'))) return
  await usersApi.delete(id, auth.accessToken!)
  await fetchUsers()
}

onMounted(fetchUsers)
</script>
