<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-semibold">Maps</h2>
      <button @click="showCreate = true"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium">
        + New Map
      </button>
    </div>

    <div v-if="mapsStore.loading" class="text-gray-400">Loading…</div>
    <table v-else class="w-full text-sm border-collapse">
      <thead>
        <tr class="border-b border-gray-700 text-gray-400 text-left">
          <th class="py-2 pr-4">Name</th>
          <th class="py-2 pr-4">Alias</th>
          <th class="py-2 pr-4">Backend</th>
          <th class="py-2 pr-4">Objects</th>
          <th class="py-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="map in mapsStore.maps" :key="map.name"
          class="border-b border-gray-800 hover:bg-gray-800">
          <td class="py-2 pr-4 font-medium">
            <router-link :to="`/maps/${map.name}`" class="text-blue-400 hover:underline">
              {{ map.name }}
            </router-link>
          </td>
          <td class="py-2 pr-4 text-gray-400">{{ map.alias || '—' }}</td>
          <td class="py-2 pr-4 text-gray-400">{{ map.backend_id }}</td>
          <td class="py-2 pr-4">{{ map.object_count }}</td>
          <td class="py-2">
            <button @click="deleteMap(map.name)" class="text-red-400 hover:text-red-300 text-xs">
              Delete
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Create map dialog -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-96">
        <h3 class="text-lg font-semibold mb-4">Create Map</h3>
        <form @submit.prevent="createMap" class="space-y-3">
          <input v-model="newMap.name" placeholder="Map name (no spaces)" required
            pattern="[a-zA-Z0-9_-]+"
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm" />
          <input v-model="newMap.alias" placeholder="Alias (display name)"
            class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm" />
          <input v-model="newMap.backend_id" placeholder="Backend ID"
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
import { useMapsStore } from '@/stores/maps'

const mapsStore = useMapsStore()
const showCreate = ref(false)
const newMap = ref({ name: '', alias: '', backend_id: 'live_1' })

async function createMap() {
  await mapsStore.createMap(newMap.value.name, newMap.value.alias, newMap.value.backend_id)
  showCreate.value = false
  newMap.value = { name: '', alias: '', backend_id: 'live_1' }
}

async function deleteMap(name: string) {
  if (!confirm(`Delete map "${name}"?`)) return
  await mapsStore.deleteMap(name)
}

onMounted(() => mapsStore.fetchMaps())
</script>
