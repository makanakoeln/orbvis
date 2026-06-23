import { type Ref, computed, ref, watch } from 'vue'

import { connectionsApi } from '@/api/client'
import type { MapObject, MetricPoint } from '@/types/api'
import type { PerfMetric } from '@/utils/perf'

interface PerformanceHistoryOptions {
  object: () => MapObject | null
  connectionId: () => string | null | undefined
  accessToken: () => string | null | undefined
  mainMetric: Ref<PerfMetric | null>
  showPerformanceTab: () => boolean
}

/**
 * Mini-graph metric history for the drawer's Performance tab. Fetched lazily —
 * only once the Performance tab actually has content (so we don't hit
 * metric-history for hosts with no perf_data) and only for host/service
 * objects. A 4-hour window matches Checkmk's default Perf-O-Meter graph.
 */
export function usePerformanceHistory(options: PerformanceHistoryOptions) {
  const { object, connectionId, accessToken, mainMetric, showPerformanceTab } = options

  const HISTORY_MINUTES = 240
  const historyData = ref<Record<string, MetricPoint[]>>({})
  let _historyReqId = 0

  async function _loadHistory(): Promise<void> {
    historyData.value = {}
    const obj = object()
    const connId = connectionId()
    const token = accessToken()
    if (!connId || !token || !obj?.host_name || (obj.type !== 'host' && obj.type !== 'service'))
      return
    const reqId = ++_historyReqId
    try {
      const res = await connectionsApi.metricHistory(
        connId,
        obj.host_name,
        obj.type === 'service' ? (obj.service_description ?? null) : null,
        HISTORY_MINUTES,
        token
      )
      if (reqId === _historyReqId) historyData.value = res.series ?? {}
    } catch {
      if (reqId === _historyReqId) historyData.value = {}
    }
  }

  // Refetch on selection change, but only when the Performance tab actually has
  // content to show — otherwise we'd hit metric-history for hosts that don't
  // expose perf_data at all.
  watch(
    [
      () => object()?.type,
      () => object()?.host_name,
      () => object()?.service_description,
      connectionId,
      showPerformanceTab
    ],
    ([, , , , show]) => {
      if (show) void _loadHistory()
      else historyData.value = {}
    }
  )

  const mainHistoryKey = computed(() => {
    const main = mainMetric.value?.label
    if (!main) return null
    // metric-history keys come straight from Checkmk's metric IDs (perf_data
    // labels), so a direct match works for normal services.
    return main in historyData.value ? main : null
  })

  const mainThresholds = computed(() => {
    const m = mainMetric.value
    if (!m) return null
    return { warn: m.warn, crit: m.crit }
  })

  return { historyData, mainHistoryKey, mainThresholds, HISTORY_MINUTES }
}
