<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-semibold">Users</h2>
      <button
        @click="showCreate = true"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium"
      >+ New User</button>
    </div>

    <div v-if="loading" class="text-gray-400">Loading…</div>
    <table v-else class="w-full text-sm border-collapse">
      <thead>
        <tr class="border-b border-gray-700 text-gray-400 text-left">
          <th class="py-2 pr-4">Name</th>
          <th class="py-2 pr-4">Admin</th>
          <th class="py-2 pr-4">Active</th>
          <th class="py-2 pr-4">Roles</th>
          <th class="py-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="user in users"
          :key="user.user_id"
          class="border-b border-gray-800 hover:bg-gray-800"
        >
          <td class="py-2 pr-4 font-medium">{{ user.name }}</td>
          <td class="py-2 pr-4">
            <span :class="user.is_admin ? 'text-yellow-400' : 'text-gray-500'">
              {{ user.is_admin ? 'Yes' : 'No' }}
            </span>
          </td>
          <td class="py-2 pr-4">
            <span :class="user.is_active ? 'text-green-400' : 'text-red-400'">
              {{ user.is_active ? 'Active' : 'Inactive' }}
            </span>
          </td>
          <td class="py-2 pr-4 text-gray-400">
            {{ user.roles.map(r => r.name).join(', ') || '—' }}
          </td>
          <td class="py-2">
            <button
              v-if="user.user_id !== auth.user?.user_id"
              @click="deleteUser(user.user_id)"
              class="text-red-400 hover:text-red-300 text-xs"
            >Delete</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create dialog -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-96">
        <h3 class="text-lg font-semibold mb-4">Create User</h3>
        <form @submit.prevent="createUser" class="space-y-3">
          <input v-model="newUser.name" placeholder="Username" required
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm" />
          <input v-model="newUser.password" type="password" placeholder="Password" required minlength="6"
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm" />
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="newUser.is_admin" />
            Admin
          </label>
          <div class="flex gap-2 justify-end mt-4">
            <button type="button" @click="showCreate = false"
              class="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
            <button type="submit"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usersApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { UserRead } from '@/types/api'

const auth = useAuthStore()
const users = ref<UserRead[]>([])
const loading = ref(false)
const showCreate = ref(false)
const newUser = ref({ name: '', password: '', is_admin: false })

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
  newUser.value = { name: '', password: '', is_admin: false }
  await fetchUsers()
}

async function deleteUser(id: number) {
  if (!confirm('Delete this user?')) return
  await usersApi.delete(id, auth.accessToken!)
  await fetchUsers()
}

onMounted(fetchUsers)
</script>
