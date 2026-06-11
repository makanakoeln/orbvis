<template>
  <div class="pbf">
    <div v-if="connectionOptions.suggestions.length > 1" class="pbf__field">
      <span class="orb-cap">{{ _t('Connection') }}</span>
      <CmkDropdown
        :selected-option="element.connection_id ?? DEFAULT_CONNECTION"
        :options="connectionOptions"
        :width="'fill'"
        :label="_t('Connection')"
        @update:selected-option="onConnectionChange"
      />
    </div>

    <div class="pbf__field">
      <span class="orb-cap">{{ _t('Object type') }}</span>
      <CmkDropdown
        :selected-option="bindKind"
        :options="bindKindOptions"
        :width="'fill'"
        :label="_t('Object type')"
        @update:selected-option="onBindKindChange"
      />
    </div>

    <template v-if="bindKind === 'host'">
      <div class="pbf__field">
        <span class="orb-cap">{{ _t('Host') }}</span>
        <AutocompleteInput
          v-model="hostModel"
          :suggestions="hosts"
          :loading="loadingHosts"
          :placeholder="_t('Bind to host…')"
          :empty-text="loadingHosts ? undefined : _t('No hosts available')"
          @change="onHostChange"
        />
      </div>
      <div class="pbf__field">
        <span class="orb-cap">{{ _t('Service (optional)') }}</span>
        <AutocompleteInput
          v-model="serviceModel"
          :suggestions="services"
          :loading="loadingServices"
          :disabled="!hostModel"
          :placeholder="_t('Whole host if empty')"
          @change="onServiceChange"
        />
      </div>
    </template>

    <div v-else-if="bindKind === 'hostgroup' || bindKind === 'servicegroup'" class="pbf__field">
      <span class="orb-cap">{{
        bindKind === 'hostgroup' ? _t('Hostgroup') : _t('Servicegroup')
      }}</span>
      <AutocompleteInput
        v-model="groupModel"
        :suggestions="groups"
        :loading="loadingGroups"
        :placeholder="_t('Pick a group…')"
        :empty-text="loadingGroups ? undefined : _t('No groups available')"
        @change="onGroupChange"
      />
    </div>

    <div v-else class="pbf__field">
      <span class="orb-cap">{{ _t('BI aggregation') }}</span>
      <AutocompleteInput
        v-model="aggregationModel"
        :suggestions="aggregationIds"
        :display-labels="aggregationTitles"
        :loading="loadingAggregations"
        :placeholder="_t('Pick an aggregation…')"
        :empty-text="loadingAggregations ? undefined : _t('No aggregations available')"
        @change="onAggregationChange"
      />
    </div>

    <CmkCheckbox
      v-if="bindKind === 'host' || bindKind === 'aggregation'"
      :model-value="element.only_hard_states ?? false"
      :label="_t('Only hard states')"
      @update:model-value="emit('patch', { only_hard_states: $event })"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { useDataBinding } from '@/composables/useDataBinding'
import { useConnectionsStore } from '@/stores/connections'
import type { AggregationInfo, DataElement, ShapeElement } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

import AutocompleteInput from '../AutocompleteInput.vue'

const { _t } = usei18n()

const props = defineProps<{
  element: DataElement | ShapeElement
  // The board's default connection — used when the element carries none.
  connectionId: string
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

// Sentinel for "inherit the board's connection" (stored as null).
const DEFAULT_CONNECTION = ''

const connectionsStore = useConnectionsStore()
const connectionOptions = ref<{ type: 'fixed'; suggestions: { name: string; title: string }[] }>({
  type: 'fixed',
  suggestions: []
})

function effectiveConnection(): string {
  return props.element.connection_id || props.connectionId
}

const binding = useDataBinding(effectiveConnection)

// ── object type ─────────────────────────────────────────────────────────────
// "host" covers the host + optional service pair; groups and BI aggregations
// carry an explicit object_type so the state service resolves them per type.
type BindKind = 'host' | 'hostgroup' | 'servicegroup' | 'aggregation'

const bindKind = computed<BindKind>(() => {
  const t = props.element.object_type
  if (t === 'hostgroup' || t === 'servicegroup' || t === 'aggregation') return t
  if (props.element.aggregation_id) return 'aggregation'
  return 'host'
})

const bindKindOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'host', title: _t('Host / service') },
    { name: 'hostgroup', title: _t('Hostgroup') },
    { name: 'servicegroup', title: _t('Servicegroup') },
    { name: 'aggregation', title: _t('BI aggregation') }
  ]
}))

function onBindKindChange(v: string | null): void {
  const kind = (v ?? 'host') as BindKind
  if (kind === bindKind.value) return
  // Switching the type clears the whole binding — stale fields from another
  // type must not linger in the element.
  emit('patch', {
    object_type: kind === 'host' ? null : kind,
    host_name: null,
    service_description: null,
    group_name: null,
    aggregation_id: null
  })
}

// ── per-type suggestion sources ─────────────────────────────────────────────
const hosts = ref<string[]>([])
const services = ref<string[]>([])
const groups = ref<string[]>([])
const aggregationInfos = ref<AggregationInfo[]>([])
const loadingHosts = ref(false)
const loadingServices = ref(false)
const loadingGroups = ref(false)
const loadingAggregations = ref(false)
const hostModel = ref('')
const serviceModel = ref('')
const groupModel = ref('')
const aggregationModel = ref('')

const aggregationIds = computed(() => aggregationInfos.value.map((a) => a.id))
const aggregationTitles = computed(() => aggregationInfos.value.map((a) => a.title || a.id))

async function loadHosts(): Promise<void> {
  loadingHosts.value = true
  hosts.value = await binding.hosts()
  loadingHosts.value = false
}

async function loadServices(host: string): Promise<void> {
  if (!host) {
    services.value = []
    return
  }
  loadingServices.value = true
  services.value = await binding.services(host)
  loadingServices.value = false
}

async function loadSourcesFor(kind: BindKind): Promise<void> {
  if (kind === 'host') {
    void loadHosts()
  } else if (kind === 'hostgroup' || kind === 'servicegroup') {
    loadingGroups.value = true
    groups.value = await (kind === 'hostgroup' ? binding.hostgroups() : binding.servicegroups())
    loadingGroups.value = false
  } else {
    loadingAggregations.value = true
    aggregationInfos.value = await binding.aggregations()
    loadingAggregations.value = false
  }
}

// Track the whole binding (not just the element id): a drag&drop bind or a
// type switch repatches the very element that is already selected, and the
// inputs must follow. Selecting in the autocomplete round-trips to the same
// value, so this never fights the user's typing.
watch(
  () => [
    props.element.id,
    bindKind.value,
    props.element.host_name,
    props.element.service_description,
    props.element.group_name,
    props.element.aggregation_id
  ],
  (next, prev) => {
    hostModel.value = props.element.host_name ?? ''
    serviceModel.value = props.element.service_description ?? ''
    groupModel.value = props.element.group_name ?? ''
    aggregationModel.value = props.element.aggregation_id ?? ''
    const idChanged = next[0] !== prev?.[0]
    const kindChanged = next[1] !== prev?.[1]
    if (idChanged || kindChanged) void loadSourcesFor(bindKind.value)
    if (bindKind.value === 'host') {
      if (!hostModel.value) services.value = []
      else if (idChanged || next[2] !== prev?.[2]) void loadServices(hostModel.value)
    }
  },
  { immediate: true }
)

onMounted(async () => {
  if (connectionsStore.connections.length === 0) await connectionsStore.fetchConnections()
  connectionOptions.value = {
    type: 'fixed',
    suggestions: [
      { name: DEFAULT_CONNECTION, title: _t('Board default') },
      ...connectionsStore.connections.map((c) => ({ name: c.id, title: c.label || c.id }))
    ]
  }
})

function onConnectionChange(v: string | null): void {
  emit('patch', {
    connection_id: v || null,
    host_name: null,
    service_description: null,
    group_name: null,
    aggregation_id: null
  })
  hosts.value = []
  services.value = []
  groups.value = []
  aggregationInfos.value = []
  void loadSourcesFor(bindKind.value)
}

// The watch above re-syncs the models and reloads sources from the patched
// element — these handlers only commit the change.
function onHostChange(v: string): void {
  emit('patch', { host_name: v || null, service_description: null })
}

function onServiceChange(v: string): void {
  emit('patch', { service_description: v || null })
}

function onGroupChange(v: string): void {
  emit('patch', { group_name: v || null })
}

function onAggregationChange(v: string): void {
  // Carry the human-readable title onto the element name — labels and the
  // layers panel would otherwise show the raw aggregation id.
  const title = aggregationInfos.value.find((a) => a.id === v)?.title
  emit('patch', { aggregation_id: v || null, ...(title ? { name: title } : {}) })
}
</script>

<style scoped>
.pbf {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pbf__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
