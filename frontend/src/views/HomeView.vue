<template>
  <div class="min-h-screen bg-gray-900">
    <nav class="bg-gray-800 border-b border-gray-700 px-6 py-3 flex justify-between items-center">
      <h1 class="text-xl font-bold">NagVis 2</h1>
      <div class="flex items-center gap-4">
        <router-link
          v-if="auth.isAdmin"
          to="/admin/users"
          class="text-sm text-gray-300 hover:text-white"
        >Admin</router-link>
        <span class="text-sm text-gray-400">{{ auth.user?.name }}</span>
        <button
          @click="auth.logout"
          class="text-sm text-gray-400 hover:text-white"
        >Logout</button>
      </div>
    </nav>

    <main class="max-w-4xl mx-auto py-10 px-6">
      <h2 class="text-2xl font-semibold mb-6">Maps</h2>

      <div v-if="mapsStore.loading" class="text-gray-400">Loading maps…</div>
      <div v-else-if="mapsStore.error" class="text-red-400">{{ mapsStore.error }}</div>
      <div v-else-if="mapsStore.maps.length === 0" class="text-gray-500">
        No maps configured yet.
        <router-link v-if="auth.isAdmin" to="/admin/maps" class="text-blue-400 underline ml-1">
          Create one
        </router-link>
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <router-link
          v-for="map in mapsStore.maps"
          :key="map.name"
          :to="`/maps/${map.name}`"
          class="block bg-gray-800 hover:bg-gray-700 rounded-lg p-4 border border-gray-700 transition-colors"
        >
          <div class="font-semibold">{{ map.alias || map.name }}</div>
          <div class="text-sm text-gray-400 mt-1">
            {{ map.object_count }} objects · backend: {{ map.backend_id }}
          </div>
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useMapsStore } from '@/stores/maps'

const auth = useAuthStore()
const mapsStore = useMapsStore()

onMounted(() => mapsStore.fetchMaps())
</script>
