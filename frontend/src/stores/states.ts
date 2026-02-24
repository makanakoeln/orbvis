import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ObjectState, WebSocketStateUpdate } from '@/types/api'

export const useStatesStore = defineStore('states', () => {
  const states = ref<Record<string, ObjectState>>({})  // keyed by object_id
  const connected = ref(false)
  const lastUpdate = ref<number | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let currentMap: string | null = null

  function connectToMap(mapName: string) {
    if (currentMap === mapName && ws && ws.readyState === WebSocket.OPEN) return
    disconnect()
    currentMap = mapName
    _connect()
  }

  function _connect() {
    if (!currentMap) return
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/api/v1/ws/maps/${currentMap}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketStateUpdate = JSON.parse(event.data)
        if (msg.type === 'state_update') {
          const newStates: Record<string, ObjectState> = {}
          for (const s of msg.states.states) {
            newStates[s.object_id] = s
          }
          states.value = newStates
          lastUpdate.value = msg.states.generated_at
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onclose = () => {
      connected.value = false
      // Auto-reconnect after 5 seconds
      reconnectTimer = setTimeout(_connect, 5000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onclose = null  // prevent auto-reconnect
      ws.close()
      ws = null
    }
    connected.value = false
    states.value = {}
    currentMap = null
  }

  function getState(objectId: string): ObjectState | undefined {
    return states.value[objectId]
  }

  return { states, connected, lastUpdate, connectToMap, disconnect, getState }
})
