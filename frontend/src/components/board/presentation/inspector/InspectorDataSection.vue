<template>
  <section class="ins">
    <h3 class="orb-section-title">{{ _t('Data') }}</h3>
    <PresentationBindingForm
      :element="element"
      :connection-id="connectionId"
      @patch="emit('patch', $event)"
    />

    <template v-if="element.kind === 'data'">
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Display') }}</span>
        <CmkDropdown
          :selected-option="element.display.mode"
          :options="modeOptions"
          :width="'fill'"
          :label="_t('Display')"
          @update:selected-option="patchDisplay({ mode: $event })"
        />
      </div>
      <div v-if="element.display.mode === 'icon'" class="ins__field">
        <span class="orb-cap">{{ _t('Icon') }}</span>
        <ImagePicker
          :model-value="element.display.image ?? ''"
          :placeholder="_t('State dot (default)')"
          @update:model-value="patchDisplay({ image: $event || null })"
        />
      </div>
      <template v-if="element.display.mode === 'gadget'">
        <div class="ins__field">
          <span class="orb-cap">{{ _t('Gadget') }}</span>
          <CmkDropdown
            :selected-option="element.display.gadget_type ?? 'gauge'"
            :options="gadgetOptions"
            :width="'fill'"
            :label="_t('Gadget')"
            @update:selected-option="patchDisplay({ gadget_type: $event })"
          />
        </div>
      </template>
      <!-- Outside the gadget block on purpose: the field self-hides off-gadget,
           but its mount keeps the binding-change metric reset running in every
           display mode. -->
      <PresentationGadgetMetricField
        :element="element"
        :connection-id="connectionId"
        @patch="emit('patch', $event)"
      />
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Fill') }}</span>
        <ColorField
          :label="_t('Fill')"
          :value="element.fill"
          @set="emit('patch', { fill: $event })"
        />
      </div>
    </template>

    <CmkCheckbox
      :model-value="effectiveLabelShow"
      :label="_t('Show label')"
      @update:model-value="emit('patch', { label: { ...labelBase, show: $event } })"
    />
    <template v-if="element.label?.show">
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Label text') }}</span>
        <input
          class="orb-field"
          :value="element.label?.text ?? ''"
          :placeholder="element.service_description || element.host_name || _t('Automatic')"
          @change="onLabelText"
        />
      </div>
      <div class="ins__row">
        <label class="ins__num">
          <span class="orb-cap">{{ _t('Label size') }}</span>
          <NumberInput
            :model-value="element.label?.size ?? 14"
            min="6"
            max="96"
            @update:model-value="
              $event !== null && emit('patch', { label: { ...labelBase, size: $event } })
            "
          />
        </label>
        <div class="ins__field">
          <span class="orb-cap">{{ _t('Label color') }}</span>
          <ColorField
            :label="_t('Label color')"
            :value="element.label?.color"
            @set="emit('patch', { label: { ...labelBase, color: $event } })"
          />
        </div>
      </div>
    </template>

    <template v-if="connectorEl">
      <div class="ins__sep" />
      <div class="ins__field">
        <span class="orb-cap">{{ _t('Start endpoint') }}</span>
        <CmkDropdown
          :selected-option="connectorEl.start_ref ?? ''"
          :options="endpointOptions"
          :width="'fill'"
          :label="_t('Start endpoint')"
          @update:selected-option="emit('patch', { start_ref: $event || null })"
        />
      </div>
      <div class="ins__field">
        <span class="orb-cap">{{ _t('End endpoint') }}</span>
        <CmkDropdown
          :selected-option="connectorEl.end_ref ?? ''"
          :options="endpointOptions"
          :width="'fill'"
          :label="_t('End endpoint')"
          @update:selected-option="emit('patch', { end_ref: $event || null })"
        />
      </div>
      <CmkCheckbox
        :model-value="connectorEl.flow ?? false"
        :label="_t('Animate flow (weathermap)')"
        @update:model-value="emit('patch', { flow: $event })"
      />
      <template v-if="connectorEl.flow">
        <div class="ins__field">
          <span class="orb-cap">{{ _t('Flow metric') }}</span>
          <AutocompleteInput
            v-model="flowMetricModel"
            :suggestions="metrics"
            :loading="loadingMetrics"
            :placeholder="element.host_name ? _t('Pick a metric…') : _t('e.g. if_in_bps')"
            @change="emit('patch', { flow_metric: $event || null })"
          />
        </div>
        <div class="ins__field">
          <span class="orb-cap">{{ _t('Return metric (optional)') }}</span>
          <AutocompleteInput
            v-model="flowMetricBackModel"
            :suggestions="metrics"
            :loading="loadingMetrics"
            :placeholder="_t('Splits the link into a two-way weathermap')"
            @change="emit('patch', { flow_metric_back: $event || null })"
          />
        </div>
      </template>
    </template>

    <div v-if="element.kind === 'shape'" class="ins__slot">
      <CmkSwitch
        :model-value="element.data_slot ?? false"
        @update:model-value="emit('patch', { data_slot: $event })"
      />
      <span
        class="ins__slot-label"
        @click="emit('patch', { data_slot: !(element.data_slot ?? false) })"
      >
        {{ _t('Data slot (fill in connect mode)') }}
      </span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import NumberInput from '@/components/NumberInput.vue'
import CmkDropdown from '@/components/cmk/CmkDropdown/CmkDropdown'
import CmkSwitch from '@/components/cmk/CmkSwitch'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { useDataBinding } from '@/composables/useDataBinding'
import type { DataElement, ElementLabel, ShapeElement } from '@/types/api'
import { connectorLabelVisible } from '@/utils/connectorFlow'
import usei18n from '@/vendor/cmk/lib/i18n'

import AutocompleteInput from '../../AutocompleteInput.vue'
import ImagePicker from '../../ImagePicker.vue'
import ColorField from '../ColorField.vue'
import PresentationBindingForm from '../PresentationBindingForm.vue'
import PresentationGadgetMetricField from '../PresentationGadgetMetricField.vue'

const { _t } = usei18n()

const props = defineProps<{
  element: DataElement | ShapeElement
  connectionId: string
  targets: { id: string; name: string }[]
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>] }>()

const connectorEl = computed<ShapeElement | null>(() =>
  props.element.kind === 'shape' &&
  (props.element.shape === 'line' || props.element.shape === 'arrow')
    ? props.element
    : null
)

const endpointOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: '', title: _t('Free') },
    ...props.targets
      .filter((t) => t.id !== props.element.id)
      .map((t) => ({ name: t.id, title: t.name }))
  ]
}))

const modeOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'icon', title: _t('Icon') },
    { name: 'text', title: _t('Text') },
    { name: 'gadget', title: _t('Gadget') }
  ]
}))

const gadgetOptions = computed(() => ({
  type: 'fixed' as const,
  suggestions: [
    { name: 'gauge', title: _t('Gauge') },
    { name: 'bar', title: _t('Bar') },
    { name: 'trafficlight', title: _t('Light') },
    { name: 'value', title: _t('Value') }
  ]
}))

function patchDisplay(p: Record<string, unknown>): void {
  if (props.element.kind !== 'data') return
  emit('patch', { display: { ...props.element.display, ...p } })
}

// A connector's value pill defaults to visible (label === null), a box
// shape's state label to hidden — the checkbox mirrors the effective state.
const effectiveLabelShow = computed(() =>
  connectorEl.value
    ? connectorLabelVisible(connectorEl.value)
    : (props.element.label?.show ?? false)
)

const labelBase = computed<ElementLabel>(() => {
  return (
    props.element.label ?? {
      show: true,
      text: null,
      size: 14,
      color: null,
      background: null,
      weight: 'bold',
      align: 'center'
    }
  )
})

function onLabelText(e: Event): void {
  const text = (e.target as HTMLInputElement).value
  emit('patch', { label: { ...labelBase.value, text: text || null } })
}

// ── metric suggestions for a connector's flow animation ─────────────────────
// Data-element gadget metrics live in PresentationGadgetMetricField; only the
// connector flow/return pickers are sourced here.
const binding = useDataBinding(() => props.element.connection_id || props.connectionId)
const metrics = ref<string[]>([])
const loadingMetrics = ref(false)
const flowMetricModel = ref('')
const flowMetricBackModel = ref('')

// When the bound object identity (host/service) changes on the SAME element,
// the previously picked metric belongs to a different object and is almost
// always invalid — reset it so the operator re-picks from the fresh list.
// Connection and object-type switches null the host/service too, so this one
// watcher covers every binding change.
watch(
  () => [props.element.id, props.element.host_name, props.element.service_description] as const,
  async (curr, prev) => {
    const bindingChanged =
      prev !== undefined && prev[0] === curr[0] && (prev[1] !== curr[1] || prev[2] !== curr[2])

    if (bindingChanged) {
      if (connectorEl.value?.flow_metric || connectorEl.value?.flow_metric_back) {
        emit('patch', { flow_metric: null, flow_metric_back: null })
      }
      flowMetricModel.value = ''
      flowMetricBackModel.value = ''
    } else {
      flowMetricModel.value = (connectorEl.value?.flow_metric ?? '') as string
      flowMetricBackModel.value = (connectorEl.value?.flow_metric_back ?? '') as string
    }

    // Only connectors consume this list (flow/return pickers) — a data element's
    // gadget metric is sourced by PresentationGadgetMetricField, so don't fetch.
    const host = props.element.host_name
    if (!host || !connectorEl.value) {
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
.ins {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ins__row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.ins__field,
.ins__num {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.ins__sep {
  height: 1px;
  margin: 2px 0;
  background: var(--default-form-element-border-color);
}

.ins__note {
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}

.ins__slot {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ins__slot-label {
  font-size: var(--font-size-normal);
  color: var(--text);
  cursor: pointer;
}
</style>
