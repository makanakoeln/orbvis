<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')" />
    <div class="relative bg-[var(--bg-surface)] ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-2xl w-[36rem] max-h-[90vh] flex flex-col">

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
          <p class="section-title">{{ t('mapSettings.monitoringObject') }}</p>
          <div class="space-y-3">
            <template v-if="object.type === 'host' || object.type === 'service'">
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.hostname') }}</label>
                <AutocompleteInput v-model="form.host_name" :suggestions="hosts" :loading="loadingHosts" :disabled="true" placeholder="hostname" class="flex-1" />
              </div>
            </template>
            <template v-if="object.type === 'service'">
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.typeService') }}</label>
                <AutocompleteInput v-model="form.service_description" :suggestions="services" :loading="loadingServices" :disabled="true" placeholder="service description" class="flex-1" />
              </div>
            </template>
            <template v-if="object.type === 'hostgroup' || object.type === 'servicegroup'">
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.groupName') }}</label>
                <AutocompleteInput v-model="form.group_name" :suggestions="groups" :loading="loadingGroups" :disabled="true" placeholder="group name" class="flex-1" />
              </div>
            </template>
            <template v-if="object.type === 'map'">
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.targetMap') }}</label>
                <input v-model="form.map_name" :disabled="true" class="field flex-1 disabled:opacity-50 disabled:cursor-not-allowed" placeholder="map-name" />
              </div>
            </template>
          </div>
        </section>

        <!-- === TEXTBOX CONTENT === -->
        <section v-if="object.type === 'textbox'">
          <p class="section-title">{{ t('mapSettings.content') }}</p>
          <textarea v-model="form.label_text" rows="3"
            class="w-full px-3.5 py-2.5 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all resize-none"
            :placeholder="t('mapSettings.textContent') + '…'" />
        </section>

        <!-- === LINE CONFIG === -->
        <section v-if="object.type === 'line'">
          <p class="section-title">{{ t('mapSettings.monitoringObject') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.hostname') }}</label>
              <AutocompleteInput v-model="form.host_name" :suggestions="hosts" :loading="loadingHosts" :disabled="true" placeholder="hostname" class="flex-1" />
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.typeService') }}</label>
              <AutocompleteInput v-model="form.service_description" :suggestions="services" :loading="loadingServices" :disabled="true" placeholder="service description (optional)" class="flex-1" />
            </div>
          </div>
        </section>
        <section v-if="object.type === 'line'">
          <p class="section-title">{{ t('mapSettings.lineSection') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.lineStyle') }}</label>
              <select v-model.number="form.line_type" class="field flex-1">
                <option :value="null">{{ t('mapSettings.lineDefault') }}</option>
                <option :value="10">{{ t('mapSettings.lineSimple') }}</option>
                <option :value="11">{{ t('mapSettings.lineArrowRight') }}</option>
                <option :value="12">{{ t('mapSettings.lineArrowLeft') }}</option>
                <option :value="13">{{ t('mapSettings.lineDoubleArrow') }}</option>
                <option :value="14">{{ t('mapSettings.lineDashed') }}</option>
                <option :value="20">{{ t('mapSettings.lineWeathermap') }}</option>
              </select>
            </div>
            <!-- Weathermap metric -->
            <div v-if="form.line_type === 20" class="field-row">
              <label class="field-label">{{ t('mapSettings.metric') }}</label>
              <AutocompleteInput
                v-model="form.weathermap_metric"
                :suggestions="metricSuggestions"
                :placeholder="t('mapSettings.firstMetric')"
                class="flex-1"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.startX') }}</label>
                <NumberInput v-model="form.x" class="flex-1" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.y') }}</label>
                <NumberInput v-model="form.y" class="flex-1" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.endX') }}</label>
                <NumberInput v-model="form.x2" class="flex-1" />
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.y') }}</label>
                <NumberInput v-model="form.y2" class="flex-1" />
              </div>
            </div>
            <!-- Label -->
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.showLabel') }}</label>
              <input v-model="form.label_show" type="checkbox" class="accent-indigo-500" />
            </div>
            <div v-if="form.label_show" class="field-row">
              <label class="field-label">{{ t('mapSettings.labelText') }}</label>
              <input v-model="form.label_text" class="field flex-1" :placeholder="t('mapSettings.labelOnLine')" />
            </div>
          </div>
        </section>

        <!-- === POSITION === -->
        <section v-if="object.type !== 'line'">
          <p class="section-title">{{ t('mapSettings.position') }}</p>
          <div class="grid grid-cols-[1fr_1fr_5rem] gap-3">
            <template v-if="mapType === 'worldmap'">
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('mapSettings.lat') }}</label>
                <NumberInput v-model="form.lat" step="any" class="flex-1" />
              </div>
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('mapSettings.lng') }}</label>
                <NumberInput v-model="form.lng" step="any" class="flex-1" />
              </div>
            </template>
            <template v-else>
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('mapSettings.x') }}</label>
                <NumberInput v-model="form.x" class="flex-1" />
              </div>
              <div class="field-row col-span-1">
                <label class="field-label">{{ t('mapSettings.y') }}</label>
                <NumberInput v-model="form.y" class="flex-1" />
              </div>
            </template>
            <div class="field-row col-span-1">
              <label class="field-label">{{ t('mapSettings.z') }}</label>
              <NumberInput v-model="form.z" min="1" max="999" class="flex-1" />
            </div>
          </div>
        </section>

        <!-- === LABEL === -->
        <section v-if="object.type !== 'line'">
          <p class="section-title">{{ t('mapSettings.label') }}</p>
          <div class="space-y-3">
            <label class="flex items-center gap-2.5 text-sm text-zinc-400 cursor-pointer select-none">
              <input type="checkbox" v-model="form.label_show" class="rounded accent-indigo-500 w-4 h-4" />
              {{ t('mapSettings.showLabel') }}
            </label>
            <template v-if="form.label_show">
              <div class="field-row" v-if="object.type !== 'textbox'">
                <label class="field-label">{{ t('mapSettings.labelText') }}</label>
                <input v-model="form.label_text" class="field flex-1" placeholder="(auto from object)" />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="field-row">
                  <label class="field-label">{{ t('mapSettings.size') }}</label>
                  <NumberInput v-model="form.label_size" min="8" max="72" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('mapSettings.color') }}</label>
                  <div class="flex gap-2 flex-1 items-center">
                    <input type="color" v-model="form.label_color"
                      class="w-9 h-9 rounded-lg border-0 bg-transparent cursor-pointer p-0.5" />
                    <input v-model="form.label_color" class="field flex-1" placeholder="#ffffff" />
                  </div>
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('mapSettings.offsetX') }}</label>
                  <NumberInput v-model="form.label_x" class="flex-1" />
                </div>
                <div class="field-row">
                  <label class="field-label">{{ t('mapSettings.offsetY') }}</label>
                  <NumberInput v-model="form.label_y" class="flex-1" />
                </div>
                <div class="field-row col-span-2">
                  <label class="field-label">{{ t('mapSettings.background') }}</label>
                  <div class="flex gap-2 flex-1 items-center">
                    <input type="color" v-model="form.label_background"
                      class="w-9 h-9 rounded-lg border-0 bg-transparent cursor-pointer p-0.5" />
                    <input v-model="form.label_background" class="field flex-1" placeholder="transparent" />
                  </div>
                </div>
              </div>
            </template>
          </div>
        </section>

        <!-- === APPEARANCE === -->
        <section v-if="object.type !== 'line' && object.type !== 'textbox'">
          <p class="section-title">{{ t('mapSettings.appearance') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.viewType') }}</label>
              <select v-model="form.view_type" class="field flex-1">
                <option value="icon">{{ t('mapSettings.viewTypeIcon') }}</option>
                <option value="text">{{ t('mapSettings.viewTypeText') }}</option>
                <option value="gadget">{{ t('mapSettings.viewTypeGadget') }}</option>
              </select>
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.size') }}</label>
              <NumberInput v-model="form.icon_size" min="1" max="512" placeholder="map default" class="w-24" />
            </div>
            <template v-if="form.view_type === 'gadget'">
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.gadgetType') }}</label>
                <select v-model="form.gadget_type" class="field flex-1">
                  <option value="gauge">{{ t('mapSettings.gadgetGauge') }}</option>
                  <option value="bar">{{ t('mapSettings.gadgetBar') }}</option>
                  <option value="trafficlight">{{ t('mapSettings.gadgetTrafficlight') }}</option>
                </select>
              </div>
              <div class="field-row">
                <label class="field-label">{{ t('mapSettings.metric') }}</label>
                <AutocompleteInput
                  v-model="form.gadget_metric"
                  :suggestions="metricSuggestions"
                  :placeholder="t('mapSettings.firstMetric')"
                  class="flex-1"
                />
              </div>
            </template>
            <div v-if="form.view_type !== 'gadget'" class="field-row">
              <label class="field-label">{{ t('mapSettings.customIcon') }}</label>
              <input v-model="form.icon" class="field flex-1 font-mono" placeholder="filename.png" />
            </div>
          </div>
        </section>

        <!-- === LINK === -->
        <section>
          <p class="section-title">{{ t('mapSettings.link') }}</p>
          <div class="space-y-3">
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.url') }}</label>
              <input v-model="form.url" class="field flex-1 font-mono" placeholder="https://…" />
            </div>
            <div class="field-row">
              <label class="field-label">{{ t('mapSettings.target') }}</label>
              <select v-model="form.url_target" class="field flex-1">
                <option value="_blank">{{ t('mapSettings.targetNewTab') }} (_blank)</option>
                <option value="_self">{{ t('mapSettings.targetSameTab') }} (_self)</option>
                <option value="_top">{{ t('mapSettings.targetTopFrame') }} (_top)</option>
              </select>
            </div>
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
            :title="t('map.deleteObject')"
            :message="t('map.cannotBeUndone')"
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
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MapObject, ObjectState } from '@/types/api'
import { backendsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { parsePerfData } from '@/utils/perf'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import AutocompleteInput from './AutocompleteInput.vue'
import NumberInput from '@/components/NumberInput.vue'

const { t } = useI18n()

const props = defineProps<{
  object: MapObject
  state?: ObjectState
  backendId: string
  mapType?: string
}>()

const emit = defineEmits<{
  close: []
  save: [updates: Record<string, unknown>]
  delete: []
}>()

const auth = useAuthStore()

const fetchedMetrics = ref<string[]>([])

const metricSuggestions = computed(() => {
  if (fetchedMetrics.value.length) return fetchedMetrics.value
  return parsePerfData(props.state?.perf_data ?? '').map(m => m.label)
})

async function fetchMetrics(host: string, service?: string) {
  if (!props.backendId || !host) return
  fetchedMetrics.value = await backendsApi.perfMetrics(
    props.backendId, host, auth.accessToken!, service || undefined,
  ).catch(() => [])
}

// ---- Form state ----

const form = reactive({
  host_name: '',
  service_description: '',
  group_name: '',
  map_name: '',
  icon: '',
  line_type: null as number | null,
  view_type: 'icon',
  label_show: true,
  label_text: '',
  label_x: 0,
  label_y: 0,
  label_size: 11,
  label_color: '#ffffff',
  label_background: 'transparent',
  gadget_type: 'gauge',
  gadget_metric: '',
  icon_size: null as number | null,
  weathermap_metric: '',
  url: '',
  url_target: '_blank',
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

// Initialize form from object
watch(() => props.object, (obj) => {
  form.host_name = obj.host_name ?? ''
  form.service_description = obj.service_description ?? ''
  form.group_name = obj.group_name ?? ''
  form.map_name = obj.map_name ?? ''
  form.icon = obj.icon ?? ''
  form.line_type = obj.line_type ?? null
  form.view_type = obj.view_type ?? 'icon'
  form.label_show = obj.label_show ?? true
  form.label_text = obj.label_text ?? ''
  form.label_x = obj.label_x ?? 0
  form.label_y = obj.label_y ?? 0
  form.label_size = obj.label_size ?? 11
  form.label_color = obj.label_color ?? '#ffffff'
  form.label_background = obj.label_background ?? 'transparent'
  form.gadget_type = obj.gadget_type ?? 'gauge'
  form.gadget_metric = obj.gadget_metric ?? ''
  form.icon_size = obj.icon_size ?? null
  form.url = obj.url ?? ''
  form.url_target = obj.url_target ?? '_blank'
  form.x = obj.x ?? 0
  form.y = obj.y ?? 0
  form.lat = obj.lat ?? 0
  form.lng = obj.lng ?? 0
  form.z = obj.z ?? 1
  form.x2 = (obj.extra?.x2 as number) ?? obj.x + 150
  form.y2 = (obj.extra?.y2 as number) ?? obj.y
  form.weathermap_metric = (obj.extra?.weathermap_metric as string) ?? ''
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
    hosts.value = await backendsApi.objects(props.backendId, 'host', auth.accessToken!).catch(() => [])
    loadingHosts.value = false
    if ((type === 'service' || type === 'line') && form.host_name) {
      loadingServices.value = true
      services.value = await backendsApi.objects(props.backendId, 'service', auth.accessToken!, form.host_name).catch(() => [])
      loadingServices.value = false
    }
  } else if (type === 'hostgroup') {
    loadingGroups.value = true
    groups.value = await backendsApi.objects(props.backendId, 'hostgroup', auth.accessToken!).catch(() => [])
    loadingGroups.value = false
  } else if (type === 'servicegroup') {
    loadingGroups.value = true
    groups.value = await backendsApi.objects(props.backendId, 'servicegroup', auth.accessToken!).catch(() => [])
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
    services.value = await backendsApi.objects(props.backendId, 'service', auth.accessToken!, host).catch(() => [])
    loadingServices.value = false
  }
})

// ---- Display name ----

const displayName = (() => {
  const obj = props.object
  if (obj.label_text) return obj.label_text
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
      view_type: form.view_type,
      gadget_type: form.view_type === 'gadget' ? form.gadget_type : null,
      gadget_metric: form.view_type === 'gadget' ? (form.gadget_metric || null) : null,
      icon_size: form.icon_size ?? null,
      icon: form.icon || null,
      line_type: form.line_type,
      label_show: form.label_show,
      label_text: form.label_text || null,
      label_x: form.label_x,
      label_y: form.label_y,
      label_size: form.label_size,
      label_color: form.label_color,
      label_background: form.label_background,
      url: form.url || null,
      url_target: form.url_target,
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
      updates.extra = {
        x2: form.x2,
        y2: form.y2,
        ...(form.line_type === 20 ? { weathermap_metric: form.weathermap_metric || null } : {}),
      }
    } else if (props.mapType === 'worldmap') {
      updates.lat = form.lat
      updates.lng = form.lng
    } else {
      updates.x = form.x
      updates.y = form.y
    }

    emit('save', updates)
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : t('mapSettings.saveFailed')
    saving.value = false
  }
}
</script>

<style scoped>
.section-title {
  @apply text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-3;
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
