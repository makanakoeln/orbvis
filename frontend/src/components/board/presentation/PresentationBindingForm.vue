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
    <CmkCheckbox
      :model-value="element.only_hard_states ?? false"
      :label="_t('Only hard states')"
      @update:model-value="emit('patch', { only_hard_states: $event })"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { useDataBinding } from '@/composables/useDataBinding'
import { useConnectionsStore } from '@/stores/connections'
import type { DataElement, ShapeElement } from '@/types/api'
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

const hosts = ref<string[]>([])
const services = ref<string[]>([])
const loadingHosts = ref(false)
const loadingServices = ref(false)
const hostModel = ref('')
const serviceModel = ref('')

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

watch(
  () => props.element.id,
  () => {
    hostModel.value = props.element.host_name ?? ''
    serviceModel.value = props.element.service_description ?? ''
    if (hostModel.value) void loadServices(hostModel.value)
  },
  { immediate: true }
)

onMounted(async () => {
  void loadHosts()
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
  emit('patch', { connection_id: v || null, host_name: null, service_description: null })
  hostModel.value = ''
  serviceModel.value = ''
  hosts.value = []
  services.value = []
  void loadHosts()
}

function onHostChange(v: string): void {
  emit('patch', { host_name: v || null, service_description: null })
  serviceModel.value = ''
  void loadServices(v)
}

function onServiceChange(v: string): void {
  emit('patch', { service_description: v || null })
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
