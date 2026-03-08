<template>
  <div>
    <div class="flex justify-between items-center mb-8">
      <div>
        <h2 class="text-xl font-bold text-zinc-100 tracking-tight">Users</h2>
        <p class="text-sm text-zinc-500 mt-1">Manage user accounts and permissions</p>
      </div>
      <button
        @click="showCreate = true"
        class="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all duration-150 shadow-lg shadow-indigo-900/20"
      >
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New User
      </button>
    </div>

    <div v-if="loading" class="flex items-center gap-2 text-zinc-500 text-sm py-8 justify-center">
      <svg class="animate-spin w-4 h-4 text-indigo-400" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      Loading…
    </div>

    <div v-else class="bg-zinc-900 ring-1 ring-white/5 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-white/5">
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Name</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Role</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
            <th class="px-4 py-3 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Roles</th>
            <th class="px-4 py-3 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-zinc-800">
          <tr
            v-for="user in users"
            :key="user.user_id"
            class="hover:bg-zinc-800/40 transition-colors"
          >
            <td class="px-4 py-3 font-medium text-zinc-100">{{ user.name }}</td>
            <td class="px-4 py-3">
              <span v-if="user.is_admin"
                class="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20">
                Admin
              </span>
              <span v-else class="text-xs text-zinc-600">User</span>
            </td>
            <td class="px-4 py-3">
              <span class="inline-flex items-center gap-1.5 text-xs font-medium"
                :class="user.is_active ? 'text-green-400' : 'text-red-400'">
                <span class="w-1.5 h-1.5 rounded-full"
                  :class="user.is_active ? 'bg-green-400' : 'bg-red-400'" />
                {{ user.is_active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="px-4 py-3 text-zinc-500 text-xs">
              <template v-if="user.roles.length">
                <span v-for="(r, i) in user.roles" :key="r.role_id"
                  class="inline-block px-1.5 py-0.5 rounded bg-zinc-800 ring-1 ring-zinc-700 text-zinc-400 mr-1 mb-0.5">
                  {{ r.name }}
                </span>
              </template>
              <span v-else class="text-zinc-700">—</span>
            </td>
            <td class="px-4 py-3 text-right">
              <div class="flex items-center justify-end gap-3">
                <button @click="editPw = user"
                  class="text-xs text-zinc-500 hover:text-indigo-400 transition-colors">
                  Change password
                </button>
                <button
                  v-if="user.user_id !== auth.user?.user_id"
                  @click="deleteUser(user.user_id)"
                  class="text-xs text-zinc-600 hover:text-red-400 transition-colors"
                >Delete</button>
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
        <div class="relative bg-zinc-900 ring-1 ring-white/10 shadow-2xl shadow-black/50 rounded-2xl p-6 w-96">
          <div class="flex items-center justify-between mb-5">
            <h3 class="text-base font-bold text-zinc-100">Create User</h3>
            <button @click="showCreate = false"
              class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-all">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <form @submit.prevent="createUser" class="space-y-4">
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Username</label>
              <input v-model="newUser.name" placeholder="john" required
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Password</label>
              <input v-model="newUser.password" type="password" placeholder="••••••••" required minlength="6"
                class="w-full px-3.5 py-2.5 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all" />
            </div>
            <label class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none">
              <input type="checkbox" v-model="newUser.is_admin" class="rounded accent-indigo-500 w-4 h-4" />
              <span>Administrator</span>
            </label>
            <label class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none">
              <input type="checkbox" v-model="newUser.must_change_password" class="rounded accent-indigo-500 w-4 h-4" />
              <span>Must change password on next login</span>
            </label>
            <div class="flex gap-3 justify-end pt-2 border-t border-white/5">
              <button type="button" @click="showCreate = false"
                class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition-all">Cancel</button>
              <button type="submit"
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-semibold text-white transition-all">Create</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <ChangePasswordModal
      v-if="editPw"
      :user-id="editPw.user_id"
      :user-name="editPw.name"
      @close="editPw = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { UserRead } from '@/types/api'
import ChangePasswordModal from '@/components/ChangePasswordModal.vue'

const auth = useAuthStore()
const users = ref<UserRead[]>([])
const loading = ref(false)
const showCreate = ref(false)
const newUser = ref({ name: '', password: '', is_admin: false, must_change_password: false })
const editPw = ref<UserRead | null>(null)

async function fetchUsers() {
  loading.value = true
  try {
    users.value = await usersApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function createUser() {
  await usersApi.create(newUser.value, auth.accessToken!)
  showCreate.value = false
  newUser.value = { name: '', password: '', is_admin: false, must_change_password: false }
  await fetchUsers()
}

async function deleteUser(id: number) {
  if (!confirm('Delete this user?')) return
  await usersApi.delete(id, auth.accessToken!)
  await fetchUsers()
}

onMounted(fetchUsers)
</script>
