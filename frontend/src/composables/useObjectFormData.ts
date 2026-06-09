import { type Ref, computed, nextTick, onMounted, ref, watch } from 'vue'

import { boardsApi, connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useStatesStore } from '@/stores/states'
import type { BoardObject, MetricGraphGroup, ObjectState } from '@/types/api'
import { parsePerfData } from '@/utils/perf'
import usei18n from '@/vendor/cmk/lib/i18n'

type GraphSource = 'auto' | 'metrics' | 'template'

/** The subset of the modal's reactive form this composable reads and mutates. */
interface ObjectFormDataForm {
  connection_id: string
  host_name: string
  service_description: string
  graph_metric: string[]
  graph_id: string | null
}

interface ObjectFormDataOptions {
  form: ObjectFormDataForm
  object: () => BoardObject
  state: () => ObjectState | undefined
  connectionId: () => string
  /** Wrapper around the "add metric" input; focused after a metric is added.
   *  Owned by the host SFC (the element lives in its template). */
  metricAddEl: Ref<HTMLElement | null>
}

/**
 * Remote data + suggestion model for the object-properties modal: perf-metric
 * IDs (and their human titles), graph templates, board names, host/service/
 * group/aggregation autocomplete, and the per-object connection override list.
 * Loads are keyed off the form's host/service/connection and degrade to empty
 * lists on API error (logged, never thrown). The `form` reactive is shared by
 * reference so metric add/clear and the graph-source toggle mutate it in place.
 */
export function useObjectFormData(options: ObjectFormDataOptions) {
  const { form, object, state, connectionId, metricAddEl } = options
  const auth = useAuthStore()
  const statesStore = useStatesStore()
  const { _t } = usei18n()

  const fetchedMetrics = ref<string[]>([])
  const graphTemplates = ref<MetricGraphGroup[]>([])
  const boardNames = ref<string[]>([])
  const boardLabels = ref<string[]>([])

  // ---- Metric suggestion model ----

  const metricIdSuggestions = computed((): string[] => {
    if (fetchedMetrics.value.length) return fetchedMetrics.value
    return parsePerfData(state()?.perf_data ?? '').map((m) => m.label)
  })

  // Map metric ID → human-readable title (falls back to the ID itself)
  const metricIdToTitle = computed((): Record<string, string> => {
    return statesStore.metricTitles[object().id] ?? {}
  })

  // Map display title → metric ID (for reverse lookup when user selects a suggestion)
  const metricTitleToId = computed((): Map<string, string> => {
    const m = new Map<string, string>()
    for (const id of metricIdSuggestions.value) {
      m.set(metricIdToTitle.value[id] ?? id, id)
    }
    return m
  })

  // Display titles for autocomplete (unique: prefer title over ID)
  const metricSuggestions = computed((): string[] =>
    metricIdSuggestions.value.map((id) => metricIdToTitle.value[id] ?? id)
  )

  // Autocomplete loads degrade to an empty list when the API errors; log the
  // reason so an empty dropdown is diagnosable instead of looking like "no data".
  function logLoadError(what: string): (e: unknown) => never[] {
    return (e) => {
      console.warn(`[OrbVis] Failed to load ${what}:`, e)
      return []
    }
  }

  async function fetchMetrics(host: string, service?: string) {
    if (!connectionId() || !host) return
    fetchedMetrics.value = await connectionsApi
      .perfMetrics(connectionId(), host, auth.accessToken!, service || undefined)
      .catch(logLoadError('metrics'))
  }

  async function fetchGraphTemplates(host: string, service?: string) {
    if (!connectionId() || !host || object().type !== 'graph') return
    graphTemplates.value = await connectionsApi
      .graphTemplates(connectionId(), host, service ?? null, auth.accessToken!)
      .catch(logLoadError('graph templates'))
  }

  async function fetchBoardNames() {
    if (object().type !== 'map' || !auth.accessToken) return
    const boards = await boardsApi.list(auth.accessToken).catch(logLoadError('board names'))
    boardNames.value = boards.map((b) => b.name)
    boardLabels.value = boards.map((b) => b.alias || b.name)
  }

  // ---- Graph source mode ----

  function deriveGraphSource(obj: BoardObject): GraphSource {
    if (obj.graph_id) return 'template'
    if (obj.graph_metric?.length) return 'metrics'
    return 'auto'
  }

  const graphSource = ref<GraphSource>(deriveGraphSource(object()))

  function setGraphSource(mode: GraphSource) {
    graphSource.value = mode
    if (mode !== 'template') form.graph_id = null
    if (mode !== 'metrics') form.graph_metric = []
  }

  const metricInput = ref('')

  async function addMetric(value: string) {
    const title = value.trim()
    const id = metricTitleToId.value.get(title) ?? title
    if (id && !form.graph_metric.includes(id)) form.graph_metric.push(id)
    metricInput.value = ''
    await nextTick()
    metricAddEl.value?.querySelector('input')?.focus()
  }

  // ---- Host/service/group/aggregation autocomplete ----

  const availableConnections = ref<{ id: string; label: string }[]>([])
  const connectionDropdownOptions = computed(() => ({
    type: 'fixed' as const,
    suggestions: [
      { name: '', title: _t('Inherit from board') },
      ...availableConnections.value.map((c) => ({ name: c.id, title: c.label }))
    ]
  }))
  async function loadConnections(): Promise<void> {
    if (!auth.accessToken) return
    try {
      const all = await connectionsApi.list(auth.accessToken)
      availableConnections.value = all.map((c) => ({ id: c.id, label: c.label || c.id }))
    } catch {
      availableConnections.value = []
    }
  }
  loadConnections()

  // Refetch host/service suggestions whenever the operator switches the
  // per-object connection — otherwise the dropdown stays bound to the board's
  // default backend and the override is invisible until they save+reopen.
  watch(
    () => form.connection_id,
    () => loadAutocomplete()
  )

  const hosts = ref<string[]>([])
  const services = ref<string[]>([])
  const groups = ref<string[]>([])
  const aggregationIds = ref<string[]>([])
  const aggregationLabels = ref<string[]>([])
  const loadingHosts = ref(false)
  const loadingServices = ref(false)
  const loadingGroups = ref(false)
  const loadingAggregations = ref(false)

  async function loadAutocomplete() {
    // Per-object connection override wins; fall back to the board default.
    const cid = form.connection_id || connectionId()
    if (!cid) return
    const type = object().type
    if (type === 'host' || type === 'service' || type === 'line' || type === 'graph') {
      loadingHosts.value = true
      hosts.value = await connectionsApi
        .objects(cid, 'host', auth.accessToken!)
        .catch(logLoadError('hosts'))
      loadingHosts.value = false
      if ((type === 'service' || type === 'line' || type === 'graph') && form.host_name) {
        loadingServices.value = true
        services.value = await connectionsApi
          .objects(cid, 'service', auth.accessToken!, form.host_name)
          .catch(logLoadError('services'))
        loadingServices.value = false
      }
    } else if (type === 'hostgroup') {
      loadingGroups.value = true
      groups.value = await connectionsApi
        .objects(cid, 'hostgroup', auth.accessToken!)
        .catch(logLoadError('host groups'))
      loadingGroups.value = false
    } else if (type === 'servicegroup') {
      loadingGroups.value = true
      groups.value = await connectionsApi
        .objects(cid, 'servicegroup', auth.accessToken!)
        .catch(logLoadError('service groups'))
      loadingGroups.value = false
    } else if (type === 'aggregation') {
      loadingAggregations.value = true
      const aggrs = await connectionsApi
        .aggregations(cid, auth.accessToken!)
        .catch(logLoadError('aggregations'))
      aggregationIds.value = aggrs.map((a) => a.id)
      aggregationLabels.value = aggrs.map((a) => a.title || a.id)
      loadingAggregations.value = false
    }
  }

  loadAutocomplete()

  onMounted(() => {
    if (form.host_name) {
      fetchMetrics(form.host_name, form.service_description || undefined)
      fetchGraphTemplates(form.host_name, form.service_description || undefined)
    }
    if (object().type === 'map') fetchBoardNames()
  })

  watch(
    () => [form.host_name, form.service_description],
    ([host, svc]) => {
      if (host) {
        fetchMetrics(host, svc || undefined)
        fetchGraphTemplates(host, svc || undefined)
      } else {
        fetchedMetrics.value = []
        graphTemplates.value = []
      }
    }
  )

  watch(
    () => form.host_name,
    async (host) => {
      if (
        (object().type === 'service' || object().type === 'line' || object().type === 'graph') &&
        host
      ) {
        loadingServices.value = true
        services.value = await connectionsApi
          .objects(connectionId(), 'service', auth.accessToken!, host)
          .catch(logLoadError('services'))
        loadingServices.value = false
      }
    }
  )

  return {
    fetchedMetrics,
    graphTemplates,
    boardNames,
    boardLabels,
    metricIdToTitle,
    metricTitleToId,
    metricSuggestions,
    graphSource,
    deriveGraphSource,
    setGraphSource,
    metricInput,
    addMetric,
    availableConnections,
    connectionDropdownOptions,
    hosts,
    services,
    groups,
    aggregationIds,
    aggregationLabels,
    loadingHosts,
    loadingServices,
    loadingGroups,
    loadingAggregations
  }
}
