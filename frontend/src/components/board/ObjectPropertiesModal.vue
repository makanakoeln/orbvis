<template>
  <div class="fixed inset-0 z-50" :class="isPopover ? '' : 'flex items-center justify-center'">
    <!-- Backdrop: dark in modal mode, transparent dismiss layer in popover mode -->
    <div class="absolute inset-0 transition-all"
      :class="isPopover ? '' : 'bg-black/60 backdrop-blur-sm'"
      @click="$emit('close')" />
    <!-- Card: centered in modal mode, positioned at click in popover mode -->
    <Transition appear
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      enter-active-class="transition-all duration-150 ease-out">
    <div class="bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl flex flex-col overflow-hidden"
      :class="isPopover ? 'absolute w-[25rem] max-h-[75vh]' : 'relative w-[36rem] max-h-[90vh]'"
      :style="isPopover ? popoverStyle : {}">

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] shrink-0">
        <div class="flex items-center gap-3">
          <span class="text-xs font-bold px-2 py-1 rounded-lg bg-[var(--bg-input)] ring-1 ring-zinc-700 text-zinc-400 uppercase tracking-wider">
            {{ object.type }}
          </span>
          <span class="font-bold text-[var(--text)]">{{ displayName }}</span>
        </div>
        <button @click="$emit('close')"
          class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-[var(--bg-hover)] transition-all">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Scrollable body -->
      <div class="overflow-y-auto flex-1 px-6 py-5 space-y-6">

        <!-- === MONITORING OBJECT === -->
        <section v-if="object.type !== 'textbox' && object.type !== 'line'">
          <p class="section-title">{{ t('boardSettings.monitoringObject') }}</p>
          <div class="space-y-3">
            <template v-if="object.type === 'host' || object.type === 'service'">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.hostname') }}</label>
                <AutocompleteInput v-model="form.host_name" :suggestions="hosts" :loading="loadingHosts" placeholder="hostname" class="flex-1" />
              </div>
            </template>
            <template v-if="object.type === 'service'">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.typeService') }}</label>
                <AutocompleteInput v-model="form.service_description" :suggestions="services" :loading="loadingServices" placeholder="service description" class="flex-1" />
              </div>
            </template>
            <template v-if="object.type === 'hostgroup' || object.type === 'servicegroup'">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.groupName') }}</label>
                <AutocompleteInput v-model="form.group_name" :suggestions="groups" :loading="loadingGroups" placeholder="group name" class="flex-1" />
              </div>
            </template>
            <template v-if="object.type === 'map'">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.targetMap') }}</label>
                <input v-model="form.map_name" class="field flex-1" placeholder="map-name" />
              </div>
            </template>
          </div>
        </section>

        <!-- === TEXTBOX CONTENT === -->
        <section v-if="object.type === 'textbox'">
          <p class="section-title">{{ t('boardSettings.content') }}</p>
          <textarea v-model="form.label.text" rows="3"
            class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all resize-none"
            :placeholder="t('boardSettings.textContent') + '…'" />
        </section>

        <!-- === LINE CONFIG === -->
        <section v-if="object.type === 'line'">
          <p class="section-title">{{ t('boardSettings.monitoringObject') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.hostname') }}</label>
              <AutocompleteInput v-model="form.host_name" :suggestions="hosts" :loading="loadingHosts" placeholder="hostname" class="flex-1" />
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.typeService') }}</label>
              <AutocompleteInput v-model="form.service_description" :suggestions="services" :loading="loadingServices" placeholder="service description (optional)" class="flex-1" />
            </div>
          </div>
        </section>
        <section v-if="object.type === 'line'">
          <p class="section-title">{{ t('boardSettings.lineSection') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.lineStyle') }}</label>
              <select v-model="form.line_style" class="field flex-1">
                <option :value="null">{{ t('boardSettings.lineDefault') }}</option>
                <option value="plain">{{ t('boardSettings.lineSimple') }}</option>
                <option value="arrow_end">{{ t('boardSettings.lineArrowRight') }}</option>
                <option value="arrow_start">{{ t('boardSettings.lineArrowLeft') }}</option>
                <option value="arrow_both">{{ t('boardSettings.lineDoubleArrow') }}</option>
                <option value="dashed">{{ t('boardSettings.lineDashed') }}</option>
                <option value="weathermap">{{ t('boardSettings.lineWeathermap') }}</option>
              </select>
            </div>
            <!-- Weathermap metric -->
            <div v-if="form.line_style === 'weathermap'" class="field-row">
              <label class="field-label">{{ t('boardSettings.metric') }}</label>
              <AutocompleteInput
                v-model="form.weathermap_metric"
                :suggestions="metricSuggestions"
                :placeholder="t('boardSettings.firstMetric')"
                class="flex-1"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.startX') }}</label>
                <NumberInput v-model="form.x" class="flex-1" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.y') }}</label>
                <NumberInput v-model="form.y" class="flex-1" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.endX') }}</label>
                <NumberInput v-model="form.x2" class="flex-1" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.y') }}</label>
                <NumberInput v-model="form.y2" class="flex-1" />
              </div>
            </div>
            <!-- Label -->
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.showLabel') }}</label>
              <input v-model="form.label.show" type="checkbox" class="accent-indigo-500" />
            </div>
            <div v-if="form.label.show" class="field-row">
              <label class="field-label">{{ t('boardSettings.labelText') }}</label>
              <input v-model="form.label.text" class="field flex-1" :placeholder="t('boardSettings.labelOnLine')" />
            </div>
          </div>
        </section>

        <!-- === POSITION === -->
        <section v-if="object.type !== 'line'">
          <p class="section-title">{{ t('boardSettings.position') }}</p>
          <div class="grid grid-cols-[1fr_1fr_5rem] gap-3">
            <template v-if="mapType === 'worldmap'">
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('boardSettings.lat') }}</label>
                <NumberInput v-model="form.lat" step="any" class="flex-1" />
              </div>
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('boardSettings.lng') }}</label>
                <NumberInput v-model="form.lng" step="any" class="flex-1" />
              </div>
            </template>
            <template v-else>
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('boardSettings.x') }}</label>
                <NumberInput v-model="form.x" class="flex-1" />
              </div>
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('boardSettings.y') }}</label>
                <NumberInput v-model="form.y" class="flex-1" />
              </div>
            </template>
            <div class="field-row col-span-1">
              <label class="field-label">{{ t('boardSettings.z') }}</label>
              <NumberInput v-model="form.z" min="1" max="999" class="flex-1" />
            </div>
          </div>
        </section>

        <!-- === LABEL === -->
        <section v-if="object.type !== 'line'">
          <p class="section-title">{{ t('boardSettings.label') }}</p>
          <div class="space-y-3">
            <label class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none">
              <input type="checkbox" v-model="form.label.show" class="rounded accent-indigo-500 w-4 h-4" />
              {{ t('boardSettings.showLabel') }}
            </label>
            <template v-if="form.label.show">
              <div class="field-row" v-if="object.type !== 'textbox'">
                <label class="field-label">{{ t('boardSettings.labelText') }}</label>
                <input v-model="form.label.text" class="field flex-1" placeholder="(auto from object)" />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.size') }}</label>
                  <NumberInput v-model="form.label.size" min="8" max="72" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.color') }}</label>
                  <div class="flex gap-2 flex-1 items-center">
                    <input type="color" v-model="form.label.color"
                      class="w-9 h-9 rounded-lg border-0 bg-transparent cursor-pointer p-0.5" />
                    <input v-model="form.label.color" class="field flex-1" placeholder="#ffffff" />
                  </div>
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.offsetX') }}</label>
                  <NumberInput v-model="form.label.x" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('boardSettings.offsetY') }}</label>
                  <NumberInput v-model="form.label.y" class="flex-1" />
                </div>
                <div class="field-row col-span-2">
                  <label class="field-label">{{ t('boardSettings.background') }}</label>
                  <div class="flex gap-2 flex-1 items-center">
                    <input type="color" v-model="form.label.background"
                      class="w-9 h-9 rounded-lg border-0 bg-transparent cursor-pointer p-0.5" />
                    <input v-model="form.label.background" class="field flex-1" placeholder="transparent" />
                  </div>
                </div>
              </div>
            </template>
          </div>
        </section>

        <!-- === APPEARANCE === -->
        <section v-if="object.type !== 'line' && object.type !== 'textbox'">
          <p class="section-title">{{ t('boardSettings.appearance') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.viewType') }}</label>
              <select v-model="form.display.mode" class="field flex-1">
                <option value="icon">{{ t('boardSettings.viewTypeIcon') }}</option>
                <option value="text">{{ t('boardSettings.viewTypeText') }}</option>
                <option value="gadget">{{ t('boardSettings.viewTypeGadget') }}</option>
              </select>
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.size') }}</label>
              <NumberInput v-model="form.display.image_size" min="1" max="512" placeholder="map default" class="w-24" />
            </div>
            <template v-if="form.display.mode === 'gadget'">
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.gadgetType') }}</label>
                <select v-model="form.display.gadget_type" class="field flex-1">
                  <option value="gauge">{{ t('boardSettings.gadgetGauge') }}</option>
                  <option value="bar">{{ t('boardSettings.gadgetBar') }}</option>
                  <option value="trafficlight">{{ t('boardSettings.gadgetTrafficlight') }}</option>
                </select>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('boardSettings.metric') }}</label>
                <AutocompleteInput
                  v-model="form.display.gadget_metric"
                  :suggestions="metricSuggestions"
                  :placeholder="t('boardSettings.firstMetric')"
                  class="flex-1"
                />
              </div>
            </template>
            <div v-if="form.display.mode !== 'gadget'" class="field-row">
              <label class="field-label">{{ t('boardSettings.customIcon') }}</label>
              <input v-model="form.display.image" class="field flex-1 font-mono" placeholder="filename.png" />
            </div>
          </div>
        </section>

        <!-- === LINK === -->
        <section>
          <button type="button" @click="showLink = !showLink"
            class="flex items-center gap-2 w-full group mb-3">
            <p class="section-title mb-0">{{ t('boardSettings.link') }}</p>
            <span v-if="form.url" class="text-[10px] text-indigo-400 font-mono truncate max-w-[12rem]">{{ form.url }}</span>
            <svg class="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 transition-all ml-auto shrink-0"
              :class="showLink ? '' : '-rotate-90'"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          <div v-if="showLink" class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.url') }}</label>
              <input v-model="form.url" class="field flex-1 font-mono" placeholder="https://…" />
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('boardSettings.target') }}</label>
              <select v-model="form.url_target" class="field flex-1">
                <option value="_blank">{{ t('boardSettings.targetNewTab') }} (_blank)</option>
                <option value="_self">{{ t('boardSettings.targetSameTab') }} (_self)</option>
                <option value="_top">{{ t('boardSettings.targetTopFrame') }} (_top)</option>
              </select>
            </div>
          </div>
        </section>

        <!-- === TEMPLATES === -->
        <section>
          <button type="button" @click="showTemplates = !showTemplates"
            class="flex items-center gap-2 w-full group mb-3">
            <p class="section-title mb-0">{{ t('boardSettings.templates') }}</p>
            <svg class="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 transition-all ml-auto shrink-0"
              :class="showTemplates ? '' : '-rotate-90'"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          <div v-if="showTemplates" class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('board.hoverTemplate') }}</label>
              <input v-model="form.hover_template" class="field flex-1 font-mono" :placeholder="t('board.templatePlaceholder')" />
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('board.contextTemplate') }}</label>
              <input v-model="form.context_template" class="field flex-1 font-mono" :placeholder="t('board.templatePlaceholder')" />
            </div>
            <p class="text-xs text-zinc-600 pl-[6.75rem]">{{ t('board.templateHint') }}</p>
          </div>
        </section>

        <!-- ID (debug) -->
        <div class="text-xs text-zinc-700 font-mono pt-1 border-t border-[var(--border)]">
          ID: {{ object.id }}
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between px-6 py-4 border-t border-[var(--border)] shrink-0">
        <div>
          <button @click="confirmDelete = true"
            class="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 ring-1 ring-red-500/20 hover:ring-red-500/40 rounded-lg text-sm font-semibold text-red-400 transition-all">
            {{ t('common.delete') }}
          </button>
          <ConfirmDialog
            v-if="confirmDelete"
            :title="t('board.deleteObject')"
            :message="t('board.cannotBeUndone')"
            :confirm-label="t('common.delete')"
            @confirm="confirmDelete = false; $emit('delete')"
            @cancel="confirmDelete = false"
          />
        </div>
        <div class="flex gap-3">
          <p v-if="saveError" class="text-red-400 text-xs self-center">{{ saveError }}</p>
          <button @click="$emit('close')"
            class="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-all">{{ t('common.cancel') }}</button>
          <button @click="save" :disabled="saving"
            class="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg text-sm font-semibold text-white transition-all">
            {{ saving ? t('common.saving') : t('common.save') }}
          </button>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { BoardObject, ObjectState } from '@/types/api'
import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { parsePerfData } from '@/utils/perf'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import AutocompleteInput from './AutocompleteInput.vue'
import NumberInput from '@/components/NumberInput.vue'

const { t } = useI18n()

const props = defineProps<{
  object: BoardObject
  state?: ObjectState
  backendId: string
  mapType?: string
  anchorRect?: { left: number; top: number; right: number; bottom: number } | null
}>()

const emit = defineEmits<{
  close: []
  save: [updates: Record<string, unknown>]
  delete: []
}>()

const auth = useAuthStore()

// Popover vs centered modal
const isPopover = computed(() => !!props.anchorRect)
const popoverStyle = computed(() => {
  const r = props.anchorRect
  if (!r) return {}
  const margin = 12
  const cardW = 400
  const cardMaxH = window.innerHeight * 0.75 // matches max-h-[75vh]

  // Horizontal: prefer right of object, fall back to left
  let left: number
  if (r.right + margin + cardW <= window.innerWidth) {
    left = r.right + margin
  } else {
    left = Math.max(margin, r.left - margin - cardW)
  }

  // Vertical: align top of card with top of object, clamp to viewport
  let top = r.top
  // If the card would overflow the bottom, push it up
  if (top + cardMaxH + margin > window.innerHeight) {
    top = window.innerHeight - cardMaxH - margin
  }
  top = Math.max(margin, top)

  return { left: `${left}px`, top: `${top}px` }
})

const fetchedMetrics = ref<string[]>([])

const metricSuggestions = computed(() => {
  if (fetchedMetrics.value.length) return fetchedMetrics.value
  return parsePerfData(props.state?.perf_data ?? '').map(m => m.label)
})

async function fetchMetrics(host: string, service?: string) {
  if (!props.backendId || !host) return
  fetchedMetrics.value = await connectionsApi.perfMetrics(
    props.backendId, host, auth.accessToken!, service || undefined,
  ).catch(() => [])
}

// ---- Form state ----

const form = reactive({
  host_name: '',
  service_description: '',
  group_name: '',
  map_name: '',
  line_style: null as string | null,
  label: {
    show: true,
    text: '',
    x: 0,
    y: 0,
    size: 11,
    color: '#ffffff',
    background: 'transparent',
  },
  display: {
    mode: 'icon' as 'icon' | 'text' | 'gadget',
    image: '',
    image_size: null as number | null,
    gadget_type: 'gauge' as string,
    gadget_metric: '',
  },
  weathermap_metric: '',
  url: '',
  url_target: '_blank',
  hover_template: '',
  context_template: '',
  x: 0,
  y: 0,
  lat: 0,
  lng: 0,
  z: 1,
  x2: 0,
  y2: 0,
})

const saving = ref(false)
const saveError = ref('')
const confirmDelete = ref(false)
const showLink = ref(!!props.object.url)
const showTemplates = ref(!!(props.object.hover_template || props.object.context_template))

// Initialize form from object
watch(() => props.object, (obj) => {
  form.host_name = obj.host_name ?? ''
  form.service_description = obj.service_description ?? ''
  form.group_name = obj.group_name ?? ''
  form.map_name = obj.map_name ?? ''
  form.line_style = obj.line_style ?? null
  form.label.show = obj.label?.show ?? true
  form.label.text = obj.label?.text ?? ''
  form.label.x = obj.label?.x ?? 0
  form.label.y = obj.label?.y ?? 0
  form.label.size = obj.label?.size ?? 11
  form.label.color = obj.label?.color ?? '#ffffff'
  form.label.background = obj.label?.background ?? 'transparent'
  form.display.mode = obj.display?.mode ?? 'icon'
  form.display.image = obj.display?.image ?? ''
  form.display.image_size = obj.display?.image_size ?? null
  form.display.gadget_type = obj.display?.gadget_type ?? 'gauge'
  form.display.gadget_metric = obj.display?.gadget_metric ?? ''
  form.weathermap_metric = obj.weathermap_metric ?? ''
  form.url = obj.url ?? ''
  form.url_target = obj.url_target ?? '_blank'
  form.hover_template = obj.hover_template ?? ''
  form.context_template = obj.context_template ?? ''
  form.x = obj.x ?? 0
  form.y = obj.y ?? 0
  form.lat = obj.lat ?? 0
  form.lng = obj.lng ?? 0
  form.z = obj.z ?? 1
  form.x2 = obj.x2 ?? obj.x + 150
  form.y2 = obj.y2 ?? obj.y
}, { immediate: true })

// ---- Autocomplete ----

const hosts = ref<string[]>([])
const services = ref<string[]>([])
const groups = ref<string[]>([])
const loadingHosts = ref(false)
const loadingServices = ref(false)
const loadingGroups = ref(false)

async function loadAutocomplete() {
  if (!props.backendId) return
  const type = props.object.type
  if (type === 'host' || type === 'service' || type === 'line') {
    loadingHosts.value = true
    hosts.value = await connectionsApi.objects(props.backendId, 'host', auth.accessToken!).catch(() => [])
    loadingHosts.value = false
    if ((type === 'service' || type === 'line') && form.host_name) {
      loadingServices.value = true
      services.value = await connectionsApi.objects(props.backendId, 'service', auth.accessToken!, form.host_name).catch(() => [])
      loadingServices.value = false
    }
  } else if (type === 'hostgroup') {
    loadingGroups.value = true
    groups.value = await connectionsApi.objects(props.backendId, 'hostgroup', auth.accessToken!).catch(() => [])
    loadingGroups.value = false
  } else if (type === 'servicegroup') {
    loadingGroups.value = true
    groups.value = await connectionsApi.objects(props.backendId, 'servicegroup', auth.accessToken!).catch(() => [])
    loadingGroups.value = false
  }
}

loadAutocomplete()

onMounted(() => {
  if (form.host_name) fetchMetrics(form.host_name, form.service_description || undefined)
})

watch(() => [form.host_name, form.service_description], ([host, svc]) => {
  if (host) fetchMetrics(host, svc || undefined)
  else fetchedMetrics.value = []
})

watch(() => form.host_name, async (host) => {
  if ((props.object.type === 'service' || props.object.type === 'line') && host) {
    loadingServices.value = true
    services.value = await connectionsApi.objects(props.backendId, 'service', auth.accessToken!, host).catch(() => [])
    loadingServices.value = false
  }
})

// ---- Display name ----

const displayName = (() => {
  const obj = props.object
  if (obj.label?.text) return obj.label.text
  if (obj.type === 'host') return obj.host_name ?? obj.id
  if (obj.type === 'service') return obj.service_description ? `${obj.host_name}/${obj.service_description}` : obj.id
  if (obj.type === 'map') return obj.map_name ?? obj.id
  if (obj.group_name) return obj.group_name
  return obj.id
})()

// ---- Save ----

async function save() {
  saveError.value = ''
  saving.value = true
  try {
    const updates: Record<string, unknown> = {
      display: {
        mode: form.display.mode,
        image: form.display.image || null,
        image_size: form.display.image_size ?? null,
        gadget_type: form.display.mode === 'gadget' ? form.display.gadget_type : null,
        gadget_metric: form.display.mode === 'gadget' ? (form.display.gadget_metric || null) : null,
      },
      label: {
        show: form.label.show,
        text: form.label.text || null,
        x: form.label.x,
        y: form.label.y,
        size: form.label.size,
        color: form.label.color,
        background: form.label.background,
      },
      line_style: form.line_style,
      url: form.url || null,
      url_target: form.url_target,
      hover_template: form.hover_template || null,
      context_template: form.context_template || null,
      z: form.z,
    }

    if (props.object.type === 'host' || props.object.type === 'service')
      updates.host_name = form.host_name || null
    if (props.object.type === 'service')
      updates.service_description = form.service_description || null
    if (props.object.type === 'hostgroup' || props.object.type === 'servicegroup')
      updates.group_name = form.group_name || null
    if (props.object.type === 'map')
      updates.map_name = form.map_name || null

    if (props.object.type === 'line') {
      updates.x = form.x
      updates.y = form.y
      updates.host_name = form.host_name || null
      updates.service_description = form.service_description || null
      updates.x2 = form.x2
      updates.y2 = form.y2
      if (form.line_style === 'weathermap') updates.weathermap_metric = form.weathermap_metric || null
    } else if (props.mapType === 'worldmap') {
      updates.lat = form.lat
      updates.lng = form.lng
    } else {
      updates.x = form.x
      updates.y = form.y
    }

    emit('save', updates)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : t('boardSettings.saveFailed')
    saving.value = false
  }
}
</script>

<style scoped>
.section-title {
  @apply text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3 leading-none;
}
.field-row {
  @apply flex items-center gap-3;
}
.field-label {
  @apply text-xs text-zinc-500 w-24 shrink-0;
}
.field {
  @apply w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150;
  appearance: textfield;
}
.field::-webkit-outer-spin-button,
.field::-webkit-inner-spin-button {
  -webkit-appearance: none;
}
select.field {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23a1a1aa' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19.5 8.25l-7.5 7.5-7.5-7.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.5rem center;
  background-size: 1rem;
  padding-right: 2rem;
}
</style>
