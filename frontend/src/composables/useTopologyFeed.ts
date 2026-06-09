import { onMounted, onUnmounted, ref, watch } from 'vue'

import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useStatesStore } from '@/stores/states'
import type { FlowView, TopologyNode } from '@/types/api'

interface TopologyFeedOptions {
  connectionId: () => string
  flowView: () => FlowView | null | undefined
  /** Whether the current service layout needs per-service detail in the fetch. */
  withServices: () => boolean
}

/**
 * Topology data source for the flow board.
 *
 * Primary: the central WebSocket pipeline pushes `topology_update` deltas via
 * statesStore.topology (scoped per auth_user); we mirror them into `nodes`.
 *
 * Fallback: when the WS handshake never opens (reverse proxy without WS
 * support), statesStore flips `wsAvailable` to false and this composable polls
 * `/topology` every 15 s, pausing while the tab is hidden. The poll timer +
 * bootstrap timer + visibilitychange listener are owned and cleaned up here;
 * the host view keeps its own render/zoom/context-menu lifecycle.
 */
export function useTopologyFeed(options: TopologyFeedOptions) {
  const { connectionId, flowView, withServices } = options
  const auth = useAuthStore()
  const statesStore = useStatesStore()

  const nodes = ref<TopologyNode[]>([])
  const loading = ref(true)
  const error = ref('')
  let timer: ReturnType<typeof setInterval> | null = null
  let bootstrapTimer: ReturnType<typeof setTimeout> | null = null

  async function fetchTopology() {
    try {
      const view = flowView()
      nodes.value = await connectionsApi.topology(
        connectionId(),
        auth.accessToken!,
        withServices(),
        {
          root: view?.root ?? null,
          childLayers: view?.child_layers ?? null,
          parentLayers: view?.parent_layers ?? null,
          topAffectedHosts: view?.top_affected_hosts ?? null,
          servicesPerHost: view?.max_services_per_host ?? null
        }
      )
      if (error.value) error.value = ''
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load topology'
    } finally {
      loading.value = false
    }
  }

  watch(
    () => statesStore.topology,
    (topo) => {
      if (!statesStore.wsAvailable) return
      nodes.value = [...topo]
      if (error.value) error.value = ''
      loading.value = false
    },
    { deep: false }
  )

  // Polling-fallback timer (only used when WS is unavailable). Tab-visibility
  // pause keeps idle multi-tab setups from each driving their own round-trip.
  function startPollTimer(): void {
    if (timer || statesStore.wsAvailable) return
    timer = setInterval(fetchTopology, 15000)
  }
  function stopPollTimer(): void {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }
  function onVisibilityChange(): void {
    if (statesStore.wsAvailable) return
    if (document.hidden) {
      stopPollTimer()
    } else {
      fetchTopology()
      startPollTimer()
    }
  }

  watch(
    () => statesStore.wsAvailable,
    (available) => {
      if (!available) {
        fetchTopology()
        if (!document.hidden) startPollTimer()
      } else {
        stopPollTimer()
      }
    }
  )

  onMounted(() => {
    if (statesStore.topology.length > 0) {
      nodes.value = [...statesStore.topology]
      loading.value = false
    } else if (statesStore.wsAvailable) {
      // Wait briefly for the first WS topology_update; if none arrives, fall
      // back to a one-shot REST fetch so the user isn't stuck on a blank board.
      bootstrapTimer = setTimeout(() => {
        if (!statesStore.topologyReady && nodes.value.length === 0) {
          fetchTopology()
        }
      }, 2000)
    } else {
      fetchTopology()
      if (!document.hidden) startPollTimer()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    document.removeEventListener('visibilitychange', onVisibilityChange)
    if (bootstrapTimer) clearTimeout(bootstrapTimer)
    stopPollTimer()
  })

  return { nodes, loading, error, fetchTopology }
}
