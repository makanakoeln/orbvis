import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ObjectState, WebSocketStateUpdate } from '@/types/api'
import { mapsApi } from '@/api/client'

// Base path without trailing slash, e.g. '/heute/orbvis' or ''
const _base = import.meta.env.BASE_URL.replace(/\/$/, '')

export const useStatesStore = defineStore('states', () => {
  const states = ref<Record<string, ObjectState>>({})  // keyed by object_id
  const connected = ref(false)
  const lastUpdate = ref<number | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let currentMap: string | null = null
  let currentToken: string | undefined = undefined
  // true once we determined WebSocket doesn't work and switched to polling
  let pollingMode = false

  async function connectToMap(mapName: string, token?: string) {
    if (currentMap === mapName && (ws?.readyState === WebSocket.OPEN || pollTimer)) return
    disconnect()
    currentMap = mapName
    currentToken = token
    await _fetchStates()
    if (!pollingMode) _connect()
    else _startPolling()
  }

  async function _fetchStates() {
    if (!currentMap || !currentToken) return
    try {
      const data = await mapsApi.getStates(currentMap, currentToken)
      const newStates: Record<string, ObjectState> = {}
      for (const s of data.states) newStates[s.object_id] = s
      for (const id of Object.keys(states.value)) {
        if (!newStates[id]) delete states.value[id]
      }
      Object.assign(states.value, newStates)
      lastUpdate.value = Date.now() / 1000
      connected.value = data.backend_ok
    } catch {
      // Backend unreachable or auth error – show as offline
      connected.value = false
    }
  }

  function _startPolling() {
    if (pollTimer) return
    pollTimer = setInterval(_fetchStates, 15_000)
  }

  function _connect() {
    if (!currentMap || !currentToken) return
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    // Token is passed as a query parameter – the Authorization header is unavailable
    // after the WebSocket upgrade handshake.
    const url = `${protocol}://${window.location.host}${_base}/api/v1/ws/maps/${currentMap}?token=${encodeURIComponent(currentToken)}`
    ws = new WebSocket(url)
    let opened = false

    ws.onopen = () => {
      opened = true
      // Do NOT set connected=true here. The first state_update message sets
      // connected via msg.states.backend_ok, which correctly reflects whether the
      // monitoring backend is reachable – not just whether the WS handshake succeeded.
      // Setting true here would override a backend_ok=false from the pre-connect
      // _fetchStates() call and show "Live" when the monitoring backend is actually down.
    }

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketStateUpdate = JSON.parse(event.data)
        if (msg.type === 'state_update') {
          const newStates: Record<string, ObjectState> = {}
          for (const s of msg.states.states) newStates[s.object_id] = s
          for (const id of Object.keys(states.value)) {
            if (!newStates[id]) delete states.value[id]
          }
          Object.assign(states.value, newStates)
          lastUpdate.value = msg.states.generated_at
          connected.value = msg.states.backend_ok
        }
      } catch { /* ignore parse errors */ }
    }

    ws.onclose = () => {
      if (!opened) {
        // Never opened: WebSocket not available (e.g. reverse proxy without WS support).
        // Switch permanently to HTTP polling for this session.
        pollingMode = true
        ws = null
        _startPolling()
        return
      }
      // Was open but dropped – try reconnect
      connected.value = false
      reconnectTimer = setTimeout(_connect, 5000)
    }

    ws.onerror = () => { ws?.close() }
  }

  function disconnect() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    if (ws) { ws.onclose = null; ws.close(); ws = null }
    connected.value = false
    states.value = {}
    currentMap = null
    currentToken = undefined
  }

  function getState(objectId: string): ObjectState | undefined {
    return states.value[objectId]
  }

  return { states, connected, lastUpdate, connectToMap, disconnect, getState }
})
