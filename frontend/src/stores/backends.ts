import { defineStore } from 'pinia'
import { ref } from 'vue'
import { backendsApi } from '@/api/client'
import type { BackendConfig } from '@/types/api'
import { useAuthStore } from './auth'

export const useBackendsStore = defineStore('backends', () => {
  const backends = ref<BackendConfig[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  function token() {
    return useAuthStore().accessToken ?? ''
  }

  async function fetchBackends() {
    loading.value = true
    error.value = null
    try {
      backends.value = await backendsApi.list(token())
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load backends'
    } finally {
      loading.value = false
    }
  }

  async function createBackend(data: BackendConfig) {
    const b = await backendsApi.create(data, token())
    backends.value.push(b)
    return b
  }

  async function updateBackend(id: string, data: Omit<BackendConfig, 'id'>) {
    const b = await backendsApi.update(id, data, token())
    const i = backends.value.findIndex((x) => x.id === id)
    if (i !== -1) backends.value[i] = b
    return b
  }

  async function deleteBackend(id: string) {
    await backendsApi.delete(id, token())
    backends.value = backends.value.filter((x) => x.id !== id)
  }

  return { backends, loading, error, fetchBackends, createBackend, updateBackend, deleteBackend }
})
