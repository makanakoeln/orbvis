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
        <CmkToggleButtonGroup
          :model-value="element.display.mode"
          :options="modeOptions"
          @update:model-value="patchDisplay({ mode: $event })"
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
          <CmkToggleButtonGroup
            :model-value="element.display.gadget_type ?? 'gauge'"
            :options="gadgetOptions"
            @update:model-value="patchDisplay({ gadget_type: $event })"
          />
        </div>
        <div class="ins__field">
          <span class="orb-cap">{{ _t('Metric') }}</span>
          <AutocompleteInput
            v-model="metricModel"
            :suggestions="metrics"
            :loading="loadingMetrics"
            :placeholder="element.host_name ? _t('Pick a metric…') : _t('Bind a host first')"
            @change="patchDisplay({ gadget_metric: $event || null })"
          />
        </div>
      </template>
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
      :model-value="element.label?.show ?? false"
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
      <div v-if="connectorEl.flow" class="ins__field">
        <span class="orb-cap">{{ _t('Flow metric') }}</span>
        <AutocompleteInput
          v-model="flowMetricModel"
          :suggestions="metrics"
          :loading="loadingMetrics"
          :placeholder="element.host_name ? _t('Pick a metric…') : _t('e.g. if_in_bps')"
          @change="emit('patch', { flow_metric: $event || null })"
        />
      </div>
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
import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup'
import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { useDataBinding } from '@/composables/useDataBinding'
import type { DataElement, ElementLabel, ShapeElement } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

import AutocompleteInput from '../../AutocompleteInput.vue'
import ImagePicker from '../../ImagePicker.vue'
import ColorField from '../ColorField.vue'
import PresentationBindingForm from '../PresentationBindingForm.vue'

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

const modeOptions = computed(() => [
  { label: _t('Icon'), value: 'icon' },
  { label: _t('Text'), value: 'text' },
  { label: _t('Gadget'), value: 'gadget' }
])

const gadgetOptions = computed(() => [
  { label: _t('Gauge'), value: 'gauge' },
  { label: _t('Bar'), value: 'bar' },
  { label: _t('Light'), value: 'trafficlight' }
])

function patchDisplay(p: Record<string, unknown>): void {
  if (props.element.kind !== 'data') return
  emit('patch', { display: { ...props.element.display, ...p } })
}

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

// ── metric suggestions for the bound host/service ───────────────────────────
const binding = useDataBinding(() => props.element.connection_id || props.connectionId)
const metrics = ref<string[]>([])
const loadingMetrics = ref(false)
const metricModel = ref('')
const flowMetricModel = ref('')

watch(
  () => [props.element.id, props.element.host_name, props.element.service_description],
  async () => {
    metricModel.value =
      (props.element.kind === 'data' ? props.element.display.gadget_metric : null) ?? ''
    flowMetricModel.value = (connectorEl.value?.flow_metric ?? '') as string
    const host = props.element.host_name
    if (!host) {
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
