import { type Ref, ref, watch } from 'vue'

import { metricsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { PerfometerResult } from '@/types/api'

// Shared across all subscribers: one request per (connection, host, service)
// and perf_data snapshot. A wall with a dozen gadgets bound to the same
// service fires a single fetch per state tick instead of twelve, and an
// unchanged perf_data re-uses the settled promise without any I/O.
interface CacheEntry {
  perf: string
  promise: Promise<PerfometerResult | null>
}

const _cache = new Map<string, CacheEntry>()

/**
 * Fetches the CMK perfometer for a bound host/service and keeps it fresh as
 * the perf_data changes. The perfometer carries what raw perf_data often
 * lacks: a percentage computed from the plugin's focus_range (so gauges can
 * fill even when the metric has no ``max``) and a properly formatted value
 * label ("RAM used 8.32 GiB"). Resolves to null for unbound elements,
 * non-Livestatus connections and services without a perfometer definition.
 */
export function usePerfometer(opts: {
  connectionId: () => string | null | undefined
  hostName: () => string | null | undefined
  serviceDescription: () => string | null | undefined
  perfData: () => string | null | undefined
  enabled: () => boolean
}): Ref<PerfometerResult | null> {
  const authStore = useAuthStore()
  const result = ref<PerfometerResult | null>(null)
  // Monotonic epoch: a slow response for an older binding/tick must not
  // overwrite the value of a newer one (last-write-wins races).
  let seq = 0

  async function fetchNow(): Promise<void> {
    const conn = opts.connectionId()
    const host = opts.hostName()
    const service = opts.serviceDescription()
    const token = authStore.accessToken
    if (!opts.enabled() || !conn || !host || !service || !token) {
      seq++
      result.value = null
      return
    }
    const epoch = ++seq
    // NUL-joined: hosts and services legitimately contain spaces.
    const key = [conn, host, service].join('\u0000')
    const perf = opts.perfData() ?? ''
    let entry = _cache.get(key)
    if (!entry || entry.perf !== perf) {
      entry = {
        perf,
        promise: metricsApi.getPerfometer(conn, host, service, token).catch(() => null)
      }
      _cache.set(key, entry)
    }
    const value = await entry.promise
    if (epoch === seq) result.value = value
  }

  watch(
    [opts.enabled, opts.connectionId, opts.hostName, opts.serviceDescription, opts.perfData],
    () => void fetchNow(),
    { immediate: true }
  )

  return result
}

/** Split a bidirectional perfometer label ("In 244 bit/s / Out 131 bit/s")
 * into its two direction halves; a simple label lands in the first half. */
export function splitPerfometerLabel(
  label: string | null | undefined
): [string | null, string | null] {
  if (!label) return [null, null]
  const parts = label.split(' / ')
  if (parts.length === 2) return [parts[0]?.trim() || null, parts[1]?.trim() || null]
  return [label, null]
}
