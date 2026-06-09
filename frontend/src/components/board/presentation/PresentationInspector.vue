<template>
  <div class="pi" :class="{ 'pi--tabbed': bindable }" @pointerdown.stop @dblclick.stop>
    <div class="pi__head">
      <div class="pi__tabs">
        <button :class="{ 'pi__tab--on': tab === 'style' }" class="pi__tab" @click="tab = 'style'">
          {{ _t('Style') }}
        </button>
        <button
          v-if="bindable"
          :class="{ 'pi__tab--on': tab === 'data' }"
          class="pi__tab"
          @click="tab = 'data'"
        >
          {{ _t('Data') }}
        </button>
      </div>
      <div class="pi__actions">
        <button class="pi__icon" :title="_t('Duplicate')" @click="$emit('duplicate')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V5a2 2 0 0 1 2-2h10" />
          </svg>
        </button>
        <button class="pi__icon pi__icon--danger" :title="_t('Delete')" @click="$emit('delete')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path
              d="M4 7h16M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2m-9 0v12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V7"
            />
          </svg>
        </button>
      </div>
    </div>

    <!-- STYLE -->
    <div v-if="tab === 'style'" class="pi__row">
      <template v-if="element.kind === 'shape'">
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Fill') }}</span>
          <ColorField :label="_t('Fill')" :value="element.fill" @set="patch({ fill: $event })" />
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Stroke') }}</span>
          <ColorField
            :label="_t('Stroke')"
            :value="element.stroke"
            @set="patch({ stroke: $event })"
          />
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Width') }}</span>
          <input
            class="pi__input pi__input--num"
            type="number"
            min="0"
            :value="element.stroke_width"
            @input="patch({ stroke_width: num($event) })"
          />
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Stroke style') }}</span>
          <select class="pi__sel" :value="element.dash" @change="patch({ dash: val($event) })">
            <option value="solid">{{ _t('Solid') }}</option>
            <option value="dashed">{{ _t('Dashed') }}</option>
            <option value="dotted">{{ _t('Dotted') }}</option>
          </select>
        </div>
        <div v-if="element.shape === 'rect'" class="pi__field">
          <span class="pi__cap">{{ _t('Radius') }}</span>
          <input
            class="pi__input pi__input--num"
            type="number"
            min="0"
            :value="element.corner_radius"
            @input="patch({ corner_radius: num($event) })"
          />
        </div>
      </template>

      <template v-else-if="element.kind === 'text'">
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Size') }}</span>
          <input
            class="pi__input pi__input--num"
            type="number"
            min="4"
            :value="element.font_size"
            @input="patch({ font_size: num($event) })"
          />
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Format') }}</span>
          <div class="pi__group">
            <button
              class="pi__toggle"
              :class="{ 'pi__toggle--on': element.font_weight === 'bold' }"
              :title="_t('Bold')"
              @click="patch({ font_weight: element.font_weight === 'bold' ? 'normal' : 'bold' })"
            >
              B
            </button>
            <button
              class="pi__toggle pi__toggle--i"
              :class="{ 'pi__toggle--on': element.font_style === 'italic' }"
              :title="_t('Italic')"
              @click="patch({ font_style: element.font_style === 'italic' ? 'normal' : 'italic' })"
            >
              I
            </button>
          </div>
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Align') }}</span>
          <select
            class="pi__sel"
            :value="element.text_align"
            @change="patch({ text_align: val($event) })"
          >
            <option value="left">{{ _t('Left') }}</option>
            <option value="center">{{ _t('Center') }}</option>
            <option value="right">{{ _t('Right') }}</option>
          </select>
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Color') }}</span>
          <ColorField :label="_t('Color')" :value="element.color" @set="patch({ color: $event })" />
        </div>
      </template>

      <template v-else-if="element.kind === 'image'">
        <div class="pi__field pi__field--stack pi__field--grow">
          <span class="pi__cap">{{ _t('From image library') }}</span>
          <ImagePicker
            :model-value="storeImageName"
            :placeholder="_t('Choose an image…')"
            @update:model-value="onPickStoreImage"
          />
        </div>
        <div class="pi__field pi__field--grow">
          <span class="pi__cap">{{ _t('…or image URL') }}</span>
          <input
            class="pi__input pi__input--url"
            :value="externalSrc"
            :placeholder="_t('https://…')"
            @change="patch({ src: val($event) || null })"
          />
        </div>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Fit') }}</span>
          <select class="pi__sel" :value="element.fit" @change="patch({ fit: val($event) })">
            <option value="contain">{{ _t('Contain') }}</option>
            <option value="cover">{{ _t('Cover') }}</option>
            <option value="fill">{{ _t('Fill') }}</option>
          </select>
        </div>
      </template>

      <template v-else-if="element.kind === 'data'">
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Display') }}</span>
          <select
            class="pi__sel"
            :value="element.display.mode"
            @change="patch({ display: { ...element.display, mode: val($event) } })"
          >
            <option value="icon">{{ _t('Icon') }}</option>
            <option value="text">{{ _t('Text') }}</option>
            <option value="gadget">{{ _t('Gadget') }}</option>
          </select>
        </div>
        <div
          v-if="element.display.mode === 'icon'"
          class="pi__field pi__field--stack pi__field--grow"
        >
          <span class="pi__cap">{{ _t('Icon') }}</span>
          <ImagePicker
            :model-value="iconImage"
            :placeholder="_t('State dot (default)')"
            @update:model-value="onPickIcon"
          />
        </div>
        <template v-if="element.display.mode === 'gadget'">
          <div class="pi__field">
            <span class="pi__cap">{{ _t('Gadget') }}</span>
            <select
              class="pi__sel"
              :value="element.display.gadget_type ?? 'gauge'"
              @change="patch({ display: { ...element.display, gadget_type: val($event) } })"
            >
              <option value="gauge">{{ _t('Gauge') }}</option>
              <option value="bar">{{ _t('Bar') }}</option>
              <option value="trafficlight">{{ _t('Traffic light') }}</option>
            </select>
          </div>
          <div class="pi__field">
            <span class="pi__cap">{{ _t('Metric') }}</span>
            <input
              class="pi__input pi__input--metric"
              :value="element.display.gadget_metric ?? ''"
              :placeholder="_t('e.g. util')"
              @change="
                patch({ display: { ...element.display, gadget_metric: val($event) || null } })
              "
            />
          </div>
        </template>
        <div class="pi__field">
          <span class="pi__cap">{{ _t('Fill') }}</span>
          <ColorField :label="_t('Fill')" :value="element.fill" @set="patch({ fill: $event })" />
        </div>
      </template>
    </div>

    <!-- DATA BINDING -->
    <div v-else-if="tab === 'data' && bindable" class="pi__col">
      <div class="pi__field pi__field--stack">
        <span class="pi__cap">{{ _t('Host') }}</span>
        <AutocompleteInput
          v-model="hostModel"
          :suggestions="hosts"
          :placeholder="_t('Bind to host…')"
          @change="onHostChange"
        />
      </div>
      <div class="pi__field pi__field--stack">
        <span class="pi__cap">{{ _t('Service (optional)') }}</span>
        <AutocompleteInput
          v-model="serviceModel"
          :suggestions="services"
          :loading="loadingServices"
          :placeholder="_t('Whole host if empty')"
          @change="onServiceChange"
        />
      </div>
      <CmkCheckbox
        :model-value="boundEl?.only_hard_states ?? false"
        :label="_t('Only hard states')"
        @update:model-value="patch({ only_hard_states: $event })"
      />
      <CmkCheckbox
        :model-value="boundEl?.label?.show ?? false"
        :label="_t('Show label')"
        @update:model-value="patch({ label: { ...labelBase, show: $event } })"
      />

      <!-- Connector: dock endpoints to elements + weathermap flow (line/arrow). -->
      <template v-if="isLineShape">
        <div class="pi__connector-sep" />
        <div class="pi__field pi__field--stack">
          <span class="pi__cap">{{ _t('Start endpoint') }}</span>
          <select
            class="pi__sel"
            :value="lineEl?.start_ref ?? ''"
            @change="patch({ start_ref: val($event) || null })"
          >
            <option value="">{{ _t('Free') }}</option>
            <option v-for="t in endpointOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <div class="pi__field pi__field--stack">
          <span class="pi__cap">{{ _t('End endpoint') }}</span>
          <select
            class="pi__sel"
            :value="lineEl?.end_ref ?? ''"
            @change="patch({ end_ref: val($event) || null })"
          >
            <option value="">{{ _t('Free') }}</option>
            <option v-for="t in endpointOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>
        <CmkCheckbox
          :model-value="lineEl?.flow ?? false"
          :label="_t('Animate flow (weathermap)')"
          @update:model-value="patch({ flow: $event })"
        />
        <div v-if="lineEl?.flow" class="pi__field pi__field--stack">
          <span class="pi__cap">{{ _t('Flow metric') }}</span>
          <input
            class="pi__input"
            :value="lineEl?.flow_metric ?? ''"
            :placeholder="_t('e.g. if_in_bps')"
            @change="patch({ flow_metric: val($event) || null })"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { DataElement, ElementLabel, PresentationElement, ShapeElement } from '@/types/api'
import { imageRefName } from '@/utils/presentationElements'
import usei18n from '@/vendor/cmk/lib/i18n'

import AutocompleteInput from '../AutocompleteInput.vue'
import ImagePicker from '../ImagePicker.vue'
import ColorField from './ColorField.vue'

const { _t } = usei18n()
const auth = useAuthStore()

const props = defineProps<{
  element: PresentationElement
  connectionId: string
  targets?: { id: string; name: string }[]
}>()

const emit = defineEmits<{ patch: [Record<string, unknown>]; delete: []; duplicate: [] }>()

const tab = ref<'style' | 'data'>('style')

// Data elements and shapes can bind to monitoring; both expose host/service +
// label fields, so the Data tab and its helpers treat them uniformly.
const boundEl = computed<DataElement | ShapeElement | null>(() =>
  props.element.kind === 'data' || props.element.kind === 'shape' ? props.element : null
)
const bindable = computed(() => boundEl.value !== null)

// Line/arrow shapes can become connectors (dock endpoints + weathermap flow).
const lineEl = computed<ShapeElement | null>(() =>
  props.element.kind === 'shape' &&
  (props.element.shape === 'line' || props.element.shape === 'arrow')
    ? props.element
    : null
)
const isLineShape = computed(() => lineEl.value !== null)
const endpointOptions = computed(() =>
  (props.targets ?? []).filter((t) => t.id !== props.element.id)
)

// Pick the tab that matches the operator's next step on each selection (the
// instance is reused across selections, so we set it explicitly): an unbound
// data element opens on Data (bind it first); everything else defaults to Style.
watch(
  () => [props.element.kind, props.element.id],
  () => {
    const el = props.element
    if (el.kind === 'data' && !el.host_name) tab.value = 'data'
    else tab.value = 'style'
  },
  { immediate: true }
)

function patch(p: Record<string, unknown>): void {
  emit('patch', p)
}
function num(e: Event): number {
  return Number((e.target as HTMLInputElement).value)
}
function val(e: Event): string {
  return (e.target as HTMLInputElement | HTMLSelectElement).value
}

// Image src is either an image-store filename (a bare name) or an arbitrary
// external URL. Split the two so the library picker only reflects store images
// and the URL field only shows external ones — selecting in one clears the other.
const storeImageName = computed(() =>
  props.element.kind === 'image' ? imageRefName(props.element.src) : ''
)
const externalSrc = computed(() => {
  if (props.element.kind !== 'image') return ''
  const src = props.element.src ?? ''
  return imageRefName(src) ? '' : src
})
// Persist the bare store filename (not a resolved URL) so the board stays
// portable across sites; the renderer resolves it via resolveImageRef.
function onPickStoreImage(name: string): void {
  patch({ src: name || null })
}

// Custom icon for a data element in "icon" display mode — a bare store filename
// (resolved by the renderer); empty falls back to the state-coloured dot.
const iconImage = computed(() =>
  props.element.kind === 'data' ? (props.element.display.image ?? '') : ''
)
function onPickIcon(name: string): void {
  if (props.element.kind !== 'data') return
  patch({ display: { ...props.element.display, image: name || null } })
}

const labelBase = computed<ElementLabel>(() => {
  const base = boundEl.value?.label ?? null
  return (
    base ?? {
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

// ---- data binding autocomplete ----
const hosts = ref<string[]>([])
const services = ref<string[]>([])
const loadingServices = ref(false)
const hostModel = ref('')
const serviceModel = ref('')

watch(
  () => props.element.id,
  () => {
    hostModel.value = boundEl.value?.host_name ?? ''
    serviceModel.value = boundEl.value?.service_description ?? ''
  },
  { immediate: true }
)

watch(tab, async (t) => {
  if (t === 'data' && hosts.value.length === 0) await fetchHosts()
})

async function fetchHosts(): Promise<void> {
  if (!props.connectionId || !auth.accessToken) return
  try {
    hosts.value = await connectionsApi.objects(props.connectionId, 'host', auth.accessToken)
  } catch {
    hosts.value = []
  }
}

async function fetchServices(host: string): Promise<void> {
  if (!host || !props.connectionId || !auth.accessToken) {
    services.value = []
    return
  }
  loadingServices.value = true
  try {
    services.value = await connectionsApi.objects(
      props.connectionId,
      'service',
      auth.accessToken,
      host
    )
  } catch {
    services.value = []
  } finally {
    loadingServices.value = false
  }
}

function onHostChange(v: string): void {
  patch({ host_name: v || null, service_description: null })
  serviceModel.value = ''
  void fetchServices(v)
}
function onServiceChange(v: string): void {
  patch({ service_description: v || null })
}
</script>

<style scoped>
.pi {
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  background: var(--bg-surface, #1b1f2a);
  border: 1px solid var(--border, rgb(255 255 255 / 8%));
  box-shadow: 0 10px 30px rgb(0 0 0 / 35%);
  color: var(--text, #e5e7eb);
  overflow: hidden;
  animation: pi-in 0.12s ease-out;
}

/* Data elements carry Style + Data tabs; a fixed width keeps the card from
   resizing (and the anchored popover from jumping) when switching tabs. */
.pi--tabbed {
  width: 264px;
}

@keyframes pi-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .pi {
    animation: none;
  }
}

.pi__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 6px;
  border-bottom: 1px solid var(--border, rgb(255 255 255 / 8%));
}

.pi__tabs,
.pi__actions {
  display: flex;
  gap: 2px;
}

.pi__tab {
  border: none;
  background: transparent;
  color: var(--text-muted, #8b93a7);
  padding: 4px 10px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
}

.pi__tab:hover {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.pi__tab--on {
  background: color-mix(in srgb, var(--accent, #15d1a0) 18%, transparent);
  color: var(--text, #e5e7eb);
}

.pi__row {
  display: flex;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  padding: 8px 10px 10px;
}

.pi__col {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: 10px;
  width: 100%;
  box-sizing: border-box;
}

.pi__connector-sep {
  height: 1px;
  margin: 2px 0;
  background: var(--border, rgb(255 255 255 / 12%));
}

.pi__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pi__field--grow {
  flex: 1;
}

.pi__field--stack {
  width: 100%;
}

.pi__cap {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1;
  color: var(--text-muted, #8b93a7);
}

.pi__input,
.pi__sel {
  height: 28px;
  box-sizing: border-box;
  border: 1px solid var(--default-form-element-border-color, var(--border, rgb(255 255 255 / 14%)));
  border-radius: 5px;
  background-color: var(--bg-input, rgb(255 255 255 / 4%));
  color: var(--text, #e5e7eb);
  padding: 0 8px;
  font-size: 12px;
  transition:
    border-color 0.12s ease,
    box-shadow 0.12s ease;
}

.pi__sel {
  appearance: none;
  padding-right: 22px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%23888' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}

.pi__input:focus,
.pi__sel:focus {
  outline: none;
  border-color: var(--accent, #15d1a0);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent, #15d1a0) 22%, transparent);
}

.pi__input--num {
  width: 60px;
}

.pi__input--metric {
  width: 112px;
}

.pi__input--url {
  width: 100%;
  min-width: 200px;
}

.pi__group {
  display: flex;
  gap: 4px;
}

.pi__toggle {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border, rgb(255 255 255 / 14%));
  border-radius: 5px;
  background: transparent;
  color: var(--text, #e5e7eb);
  cursor: pointer;
  font-weight: 700;
}

.pi__toggle:hover {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.pi__toggle--i {
  font-style: italic;
}

.pi__toggle--on {
  background: color-mix(in srgb, var(--accent, #15d1a0) 20%, transparent);
  border-color: var(--accent, #15d1a0);
}

.pi__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-muted, #8b93a7);
  cursor: pointer;
  transition:
    background 0.12s ease,
    color 0.12s ease;
}

.pi__icon svg {
  width: 16px;
  height: 16px;
}

.pi__icon:hover {
  background: var(--bg-hover, rgb(255 255 255 / 8%));
  color: var(--text, #e5e7eb);
}

.pi__icon--danger:hover {
  background: color-mix(in srgb, var(--error, #e9546b) 20%, transparent);
}
</style>
