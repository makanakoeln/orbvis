import { type Ref, ref, watch } from 'vue'

import { metricsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { MetricUnitMap } from '@/types/api'

// Shared across all subscribers: registered units change only when the
// service's metric set changes (rediscovery), so one fetch per
// (connection, host, service) serves every gadget/label/drawer for the
// session; a changed label set (parsed from fresh perf_data) refetches.
interface CacheEntry {
  labelsKey: string
  promise: Promise<MetricUnitMap>
}

const _cache = new Map<string, CacheEntry>()

/** Stable fingerprint of the metric set in a perf_data string — quote
 * variants of the same label must not register as a change. */
function labelsKeyOf(perfData: string): string {
  const labels = (perfData.match(/(?:'[^']+'|[^\s]+)=/g) ?? []).map((m) =>
    m.slice(0, -1).replace(/^'|'$/g, '')
  )
  return labels.sort().join('\u0000')
}

/**
 * The CMK metric-registry display units for a bound host/service — keyed by
 * raw perfdata label. Resolves to {} for unbound elements, non-Livestatus
 * connections and services whose metrics aren't registered; consumers fall
 * back to client-side heuristics via renderMetricValue.
 */
export function useMetricUnits(opts: {
  connectionId: () => string | null | undefined
  hostName: () => string | null | undefined
  serviceDescription: () => string | null | undefined
  perfData: () => string | null | undefined
  enabled: () => boolean
}): Ref<MetricUnitMap> {
  const authStore = useAuthStore()
  const result = ref<MetricUnitMap>({})
  // Monotonic epoch: a slow response for an older binding must not overwrite
  // the value of a newer one.
  let seq = 0

  async function fetchNow(): Promise<void> {
    const conn = opts.connectionId()
    const host = opts.hostName()
    const service = opts.serviceDescription()
    const token = authStore.accessToken
    if (!opts.enabled() || !conn || !host || !service || !token) {
      seq++
      result.value = {}
      return
    }
    const epoch = ++seq
    const labelsKey = labelsKeyOf(opts.perfData() ?? '')
    // No perf_data yet (PENDING service) — don't burn a livestatus query on
    // an empty metric set; the first real tick changes labelsKey and fetches.
    if (!labelsKey) {
      result.value = {}
      return
    }
    // NUL-joined: hosts and services legitimately contain spaces.
    const key = [conn, host, service].join('\u0000')
    let entry = _cache.get(key)
    if (!entry || entry.labelsKey !== labelsKey) {
      const promise = metricsApi.getUnits(conn, host, service, token).catch(() => {
        // Don't pin a transient failure (deploy restart, token refresh gap)
        // for the session — drop the entry so the next tick retries.
        if (_cache.get(key) === entry) _cache.delete(key)
        return {}
      })
      entry = { labelsKey, promise }
      _cache.set(key, entry)
    }
    const value = await entry.promise
    if (epoch === seq) result.value = value
  }

  watch(
    [
      opts.enabled,
      opts.connectionId,
      opts.hostName,
      opts.serviceDescription,
      opts.perfData,
      // Token hydration/rotation must re-trigger a fetch that bailed without one.
      () => authStore.accessToken
    ],
    () => void fetchNow(),
    { immediate: true }
  )

  return result
}
