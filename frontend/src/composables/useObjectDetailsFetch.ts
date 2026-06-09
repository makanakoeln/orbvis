import { ref, watch } from 'vue'

import { connectionsApi, metricsApi } from '@/api/client'
import type { BoardObject, ObjectDetails, PerfometerResult } from '@/types/api'

interface ObjectDetailsFetchOptions {
  object: () => BoardObject | null
  connectionId: () => string | null | undefined
  accessToken: () => string | null | undefined
}

/**
 * On-demand fetch of an object's rich details (long_output, comments,
 * downtimes, topology, metric titles) plus the CMK perfometer result, kept off
 * the streamed ObjectState because they're large and rarely change. Refetched
 * whenever the selected host/service/connection changes; only services get a
 * perfometer. Returns the `details`/`perfometer` refs for downstream consumers.
 */
export function useObjectDetailsFetch(options: ObjectDetailsFetchOptions) {
  const { object, connectionId, accessToken } = options

  const details = ref<ObjectDetails | null>(null)
  const perfometer = ref<PerfometerResult | null>(null)

  // Source the watch on primitive keys (not the reactive object) so it fires
  // only when selection actually changes — state-stream updates that re-create
  // the prop reference would otherwise cause refetches on every tick.
  watch(
    [
      () => object()?.type,
      () => object()?.host_name,
      () => object()?.service_description,
      connectionId
    ],
    async ([objType, host, service, connId]) => {
      details.value = null
      perfometer.value = null
      const token = accessToken()
      if (!connId || !token || !host) return
      if (objType !== 'host' && objType !== 'service') return
      if (objType === 'service' && !service) return
      const reqService = objType === 'service' ? (service ?? null) : null
      try {
        const [detailsRes, perfRes] = await Promise.all([
          connectionsApi.objectDetails(connId, objType, host, reqService, token),
          objType === 'service' && reqService
            ? metricsApi.getPerfometer(connId, host, reqService, token)
            : Promise.resolve(null)
        ])
        // Stale-response guard: between the await and now the user may have
        // clicked another object. Match all three identity fields so a host
        // response doesn't land on a same-named service or vice versa.
        // Note: service_description may be undefined on host BoardObjects
        // (Flow Board synthesises hosts without it) — normalise to null
        // before comparing so the guard doesn't reject legitimate hosts.
        const currentService = object()?.service_description ?? null
        if (
          object()?.type === objType &&
          object()?.host_name === host &&
          currentService === reqService
        ) {
          details.value = detailsRes
          perfometer.value = perfRes
        }
      } catch {
        details.value = null
        perfometer.value = null
      }
    },
    { immediate: true }
  )

  return { details, perfometer }
}
