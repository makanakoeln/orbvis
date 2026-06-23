import { defineStore } from 'pinia'
import { ref } from 'vue'

import { connectionsApi } from '@/api/client'
import type { ConnectionConfig } from '@/types/api'

import { useAuthStore } from './auth'

export const useConnectionsStore = defineStore('connections', () => {
  const connections = ref<ConnectionConfig[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  function token() {
    return useAuthStore().accessToken ?? ''
  }

  async function fetchConnections() {
    loading.value = true
    error.value = null
    try {
      connections.value = await connectionsApi.list(token())
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load connections'
    } finally {
      loading.value = false
    }
  }

  // Lazy load shared by every surface that only needs the list for display —
  // concurrent callers (e.g. HomeView and the maps table in the same render)
  // share one request instead of racing duplicates.
  let _inflight: Promise<void> | null = null
  function ensureConnections(): Promise<void> {
    if (connections.value.length) return Promise.resolve()
    _inflight ??= fetchConnections().finally(() => {
      _inflight = null
    })
    return _inflight
  }

  /** Display name for a connection id ("cmk ZWEIFUENF"), falling back to the
   * raw id until the list is loaded or for unknown/deleted connections. */
  function labelFor(id: string | null | undefined): string {
    if (!id) return ''
    return connections.value.find((c) => c.id === id)?.label || id
  }

  async function createConnection(data: ConnectionConfig) {
    const b = await connectionsApi.create(data, token())
    connections.value.push(b)
    return b
  }

  async function updateConnection(id: string, data: Omit<ConnectionConfig, 'id'>) {
    const b = await connectionsApi.update(id, data, token())
    const i = connections.value.findIndex((x) => x.id === id)
    if (i !== -1) connections.value[i] = b
    return b
  }

  async function deleteConnection(id: string) {
    await connectionsApi.delete(id, token())
    connections.value = connections.value.filter((x) => x.id !== id)
  }

  return {
    connections,
    loading,
    error,
    fetchConnections,
    ensureConnections,
    labelFor,
    createConnection,
    updateConnection,
    deleteConnection
  }
})
