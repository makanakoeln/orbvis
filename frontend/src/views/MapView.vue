<template>
  <div class="min-h-screen bg-gray-900 flex flex-col">
    <!-- Navbar -->
    <nav class="bg-gray-800 border-b border-gray-700 px-6 py-3 flex justify-between items-center shrink-0">
      <div class="flex items-center gap-3">
        <router-link to="/" class="text-gray-400 hover:text-white text-sm">← Maps</router-link>
        <span class="text-gray-600">/</span>
        <span class="font-semibold">{{ mapConfig?.globals.alias || route.params.name }}</span>
      </div>
      <div class="flex items-center gap-3 text-sm">
        <span
          :class="statesStore.connected ? 'text-green-400' : 'text-red-400'"
          class="flex items-center gap-1"
        >
          <span class="w-2 h-2 rounded-full inline-block"
            :class="statesStore.connected ? 'bg-green-400' : 'bg-red-400'"
          ></span>
          {{ statesStore.connected ? 'Live' : 'Disconnected' }}
        </span>
        <button @click="auth.logout" class="text-gray-400 hover:text-white">Logout</button>
      </div>
    </nav>

    <!-- Map canvas -->
    <div class="flex-1 relative overflow-hidden">
      <div v-if="mapsStore.loading" class="absolute inset-0 flex items-center justify-center text-gray-400">
        Loading map…
      </div>
      <MapCanvas
        v-else-if="mapConfig"
        :config="mapConfig"
        :states="statesStore.states"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useMapsStore } from '@/stores/maps'
import { useStatesStore } from '@/stores/states'
import MapCanvas from '@/components/map/MapCanvas.vue'

const route = useRoute()
const auth = useAuthStore()
const mapsStore = useMapsStore()
const statesStore = useStatesStore()

const mapName = computed(() => route.params.name as string)
const mapConfig = computed(() => mapsStore.currentMap)

onMounted(async () => {
  await mapsStore.fetchMap(mapName.value)
  statesStore.connectToMap(mapName.value)
})

onUnmounted(() => {
  statesStore.disconnect()
})
</script>
