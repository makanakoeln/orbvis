<template>
  <!-- Mounted for every data element (not just gadget mode) so the
       binding-change reset below always runs; the picker itself is only
       relevant once the element actually renders as a gadget. -->
  <template v-if="element.display.mode === 'gadget'">
    <div v-if="!isGroupBinding" class="ins__field">
      <span class="orb-cap">{{ _t('Metric') }}</span>
      <AutocompleteInput
        v-model="metricModel"
        :suggestions="metrics.map((m) => m.name)"
        :display-labels="metrics.map((m) => m.title)"
        :loading="loadingMetrics"
        :placeholder="element.host_name ? _t('Pick a metric…') : _t('Bind a host first')"
        @change="emit('patch', { display: { ...element.display, gadget_metric: $event || null } })"
      />
    </div>
    <span v-else class="ins__note">
      {{
        _t(
          'Groups and BI aggregations carry no metrics — gauge and bar show a state light instead.'
        )
      }}
    </span>
  </template>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useDataBinding } from '@/composables/useDataBinding'
import type { DataElement, MetricChoice } from '@/types/api'
import { isMetriclessBinding } from '@/utils/presentationSampleState'
import usei18n from '@/vendor/cmk/lib/i18n'

import AutocompleteInput from '../AutocompleteInput.vue'

const { _t } = usei18n()

const props = defineProps<{
  element: DataElement
  connectionId: string
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

// Group/BI bindings have a state but no perf metrics — the picker would only
// mislead ("Bind a host first" on an already-bound element).
const isGroupBinding = computed(() => isMetriclessBinding(props.element))

const binding = useDataBinding(() => props.element.connection_id || props.connectionId)
const metrics = ref<MetricChoice[]>([])
const loadingMetrics = ref(false)
const metricModel = ref('')

// When the bound object identity (host/service) changes on the SAME element, the
// previously picked metric belongs to a different object and is almost always
// invalid — reset it so the operator re-picks from the fresh list. Connection
// and object-type switches null the host/service too, so this one watcher covers
// every binding change.
watch(
  () => [props.element.id, props.element.host_name, props.element.service_description] as const,
  async (curr, prev) => {
    const bindingChanged =
      prev !== undefined && prev[0] === curr[0] && (prev[1] !== curr[1] || prev[2] !== curr[2])

    if (bindingChanged) {
      if (props.element.display.gadget_metric) {
        emit('patch', { display: { ...props.element.display, gadget_metric: null } })
      }
      metricModel.value = ''
    } else {
      metricModel.value = props.element.display.gadget_metric ?? ''
    }

    // Suggestions only matter while the picker is visible — skip the fetch for
    // icon/text-mode elements that merely mount this for the reset above.
    const host = props.element.host_name
    if (!host || props.element.display.mode !== 'gadget') {
      metrics.value = []
      return
    }
    loadingMetrics.value = true
    metrics.value = await binding.metrics(host, props.element.service_description)
    loadingMetrics.value = false
  },
  { immediate: true }
)
</script>

<style scoped>
.ins__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.ins__note {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}
</style>
