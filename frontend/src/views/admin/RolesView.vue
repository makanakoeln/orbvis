<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-semibold">Roles & Permissions</h2>
      <button @click="showCreate = true"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium">
        + New Role
      </button>
    </div>

    <div v-if="loading" class="text-gray-400">Loading…</div>
    <div v-else class="space-y-4">
      <div v-for="role in roles" :key="role.role_id"
        class="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <div class="flex justify-between items-start">
          <div>
            <div class="font-semibold">{{ role.name }}</div>
            <div class="text-sm text-gray-400 mt-1">
              {{ role.permissions.length }} permission(s)
            </div>
            <div class="flex flex-wrap gap-1 mt-2">
              <span
                v-for="perm in role.permissions"
                :key="perm.perm_id"
                class="text-xs bg-gray-700 rounded px-2 py-0.5 text-gray-300"
              >{{ perm.mod }}/{{ perm.act }}/{{ perm.obj }}</span>
            </div>
          </div>
          <button @click="deleteRole(role.role_id)" class="text-red-400 hover:text-red-300 text-xs">
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Create role dialog -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-80">
        <h3 class="text-lg font-semibold mb-4">Create Role</h3>
        <form @submit.prevent="createRole" class="space-y-3">
          <input v-model="newRoleName" placeholder="Role name" required
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm" />
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
import { rolesApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { RoleRead } from '@/types/api'

const auth = useAuthStore()
const roles = ref<RoleRead[]>([])
const loading = ref(false)
const showCreate = ref(false)
const newRoleName = ref('')

async function fetchRoles() {
  loading.value = true
  try {
    roles.value = await rolesApi.list(auth.accessToken!)
  } finally {
    loading.value = false
  }
}

async function createRole() {
  await rolesApi.create(newRoleName.value, auth.accessToken!)
  showCreate.value = false
  newRoleName.value = ''
  await fetchRoles()
}

async function deleteRole(id: number) {
  if (!confirm('Delete this role?')) return
  await rolesApi.delete(id, auth.accessToken!)
  await fetchRoles()
}

onMounted(fetchRoles)
</script>
