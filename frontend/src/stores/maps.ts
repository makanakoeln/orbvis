import { defineStore } from 'pinia'
import { ref } from 'vue'
import { mapsApi } from '@/api/client'
import type { MapConfig, MapRead } from '@/types/api'
import { useAuthStore } from './auth'

export const useMapsStore = defineStore('maps', () => {
  const maps = ref<MapRead[]>([])
  const currentMap = ref<MapConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function token(): string {
    return useAuthStore().accessToken ?? ''
  }

  async function fetchMaps() {
    loading.value = true
    error.value = null
    try {
      maps.value = await mapsApi.list(token())
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load maps'
    } finally {
      loading.value = false
    }
  }

  async function fetchMap(name: string) {
    loading.value = true
    error.value = null
    currentMap.value = null  // clear stale data immediately
    try {
      currentMap.value = await mapsApi.get(name, token())
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load map'
    } finally {
      loading.value = false
    }
  }

  async function createMap(name: string, alias: string, backendId = 'live_1', mapType = 'static') {
    const cfg = await mapsApi.create({ name, alias, backend_id: backendId, map_type: mapType }, token())
    await fetchMaps()
    return cfg
  }

  async function deleteMap(name: string) {
    await mapsApi.delete(name, token())
    await fetchMaps()
  }

  return { maps, currentMap, loading, error, fetchMaps, fetchMap, createMap, deleteMap }
})
