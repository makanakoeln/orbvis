<template>
  <aside class="w-72 bg-zinc-900 border-l border-white/5 flex flex-col shrink-0 overflow-y-auto text-sm">
    <!-- Header -->
    <div class="px-4 py-3.5 border-b border-white/5 flex items-center justify-between shrink-0">
      <div>
        <p class="font-semibold text-zinc-100 text-sm">Edit Mode</p>
        <p class="text-xs text-zinc-500 mt-0.5">Drag objects · click to select</p>
      </div>
      <!-- Grid snap -->
      <div class="flex items-center gap-1.5 text-xs text-zinc-500">
        <span>Grid</span>
        <select :value="snapGrid" @change="$emit('update:snapGrid', +($event.target as HTMLSelectElement).value)"
          class="bg-zinc-800 ring-1 ring-zinc-700 rounded-md px-1.5 py-0.5 text-xs text-zinc-300 focus:outline-none focus:ring-indigo-500">
          <option value="0">off</option>
          <option value="10">10 px</option>
          <option value="20">20 px</option>
          <option value="50">50 px</option>
        </select>
      </div>
    </div>

    <!-- Add Object -->
    <div class="p-4 border-b border-white/5 space-y-2.5 shrink-0">
      <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Add Object</p>

      <select v-model="draft.type" @change="onTypeChange"
        class="w-full px-3 py-2 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
        <option value="">Select type…</option>
        <option value="host">Host</option>
        <option value="service">Service</option>
        <option value="hostgroup">Hostgroup</option>
        <option value="servicegroup">Servicegroup</option>
        <option value="map">Map link</option>
        <option value="line">Line</option>
        <option value="textbox">Textbox</option>
      </select>

      <template v-if="draft.type === 'host'">
        <AutocompleteInput v-model="draft.host_name" :suggestions="addObjects" :loading="loadingAddObjects" placeholder="Hostname" />
      </template>

      <template v-else-if="draft.type === 'service'">
        <AutocompleteInput v-model="draft.host_name" :suggestions="addObjects" :loading="loadingAddObjects" placeholder="Hostname" @change="onHostChange" />
        <AutocompleteInput v-model="draft.service_description" :suggestions="addServices" :loading="loadingAddServices" placeholder="Service description" />
      </template>

      <template v-else-if="draft.type === 'hostgroup' || draft.type === 'servicegroup'">
        <AutocompleteInput v-model="draft.group_name" :suggestions="addObjects" :loading="loadingAddObjects" placeholder="Group name" />
      </template>

      <template v-else-if="draft.type === 'map'">
        <input v-model="draft.map_name" placeholder="Map name" class="field" />
        <input v-model="draft.label_text" placeholder="Label (optional)" class="field" />
      </template>

      <template v-else-if="draft.type === 'line'">
        <AutocompleteInput v-model="draft.host_name" :suggestions="addObjects" :loading="loadingAddObjects" placeholder="Hostname (optional)" @change="onHostChange" />
        <AutocompleteInput v-model="draft.service_description" :suggestions="addServices" :loading="loadingAddServices" placeholder="Service (optional)" />
      </template>

      <template v-else-if="draft.type === 'textbox'">
        <input v-model="draft.label_text" placeholder="Text content" class="field" />
      </template>

      <button v-if="draft.type" @click="$emit('start-placing')"
        class="w-full px-3 py-2 rounded-lg font-semibold text-sm transition-all duration-150"
        :class="placing
          ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30 animate-pulse'
          : 'bg-indigo-600 hover:bg-indigo-500 text-white'">
        {{ placing ? 'Click on map to place…' : 'Place on map' }}
      </button>
    </div>

    <!-- Selected Object Properties -->
    <div v-if="selectedObject" class="flex flex-col divide-y divide-white/5">

      <div class="px-4 pt-4 pb-3 flex items-center gap-2 shrink-0">
        <p class="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Selected</p>
        <span class="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 ring-1 ring-zinc-700 text-zinc-400 font-mono">
          {{ selectedObject.type }}
        </span>
      </div>

      <form @submit.prevent="saveProperties" class="flex flex-col divide-y divide-white/5">

        <!-- Monitoring Object -->
        <section v-if="needsMonitoringObject" class="p-4 space-y-2">
          <p class="section-title">Monitoring Object</p>
          <template v-if="selectedObject.type === 'host' || selectedObject.type === 'service'">
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Hostname</label>
              <AutocompleteInput v-model="editForm.host_name" :suggestions="editObjects" :disabled="true" placeholder="Hostname" />
            </div>
          </template>
          <template v-if="selectedObject.type === 'service'">
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Service</label>
              <AutocompleteInput v-model="editForm.service_description" :suggestions="editServices" :disabled="true" placeholder="Service description" />
            </div>
          </template>
          <template v-if="selectedObject.type === 'hostgroup' || selectedObject.type === 'servicegroup'">
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Group name</label>
              <AutocompleteInput v-model="editForm.group_name" :suggestions="editObjects" :disabled="true" placeholder="Group name" />
            </div>
          </template>
          <template v-if="selectedObject.type === 'map'">
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Target map</label>
              <input v-model="editForm.map_name" class="field" disabled />
            </div>
          </template>
        </section>

        <!-- Textbox Content -->
        <section v-if="selectedObject.type === 'textbox'" class="p-4 space-y-2">
          <p class="section-title">Content</p>
          <textarea v-model="editForm.label_text" rows="3" class="field resize-none" placeholder="Text content…" />
        </section>

        <!-- Line: Monitoring Object -->
        <section v-if="selectedObject.type === 'line'" class="p-4 space-y-2">
          <p class="section-title">Monitoring Object</p>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">Hostname</label>
            <AutocompleteInput v-model="editForm.host_name" :suggestions="editObjects" placeholder="Hostname" @change="onLineHostChange" />
          </div>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">Service</label>
            <AutocompleteInput v-model="editForm.service_description" :suggestions="editServices" placeholder="Service (optional)" />
          </div>
        </section>

        <!-- Line: Config -->
        <section v-if="selectedObject.type === 'line'" class="p-4 space-y-2">
          <p class="section-title">Line</p>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">Style</label>
            <select v-model.number="editForm.line_type" class="field">
              <option :value="null">Default</option>
              <option :value="10">Simple line</option>
              <option :value="11">Arrow →</option>
              <option :value="12">Arrow ←</option>
              <option :value="13">Double arrow ↔</option>
              <option :value="14">Dashed</option>
              <option :value="20">Weathermap (utilization)</option>
            </select>
          </div>
          <div v-if="editForm.line_type === 20" class="space-y-1">
            <label class="text-xs text-zinc-500">Metric</label>
            <AutocompleteInput v-model="editForm.weathermap_metric" :suggestions="metricSuggestions" placeholder="first metric" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Start X</label>
              <input v-model.number="editForm.x" type="number" class="field" />
            </div>
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Y</label>
              <input v-model.number="editForm.y" type="number" class="field" />
            </div>
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">End X</label>
              <input v-model.number="editForm.x2" type="number" class="field" />
            </div>
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Y</label>
              <input v-model.number="editForm.y2" type="number" class="field" />
            </div>
          </div>
          <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
            <input type="checkbox" v-model="editForm.label_show" class="rounded accent-indigo-500" />
            Show label
          </label>
          <div v-if="editForm.label_show" class="space-y-1">
            <label class="text-xs text-zinc-500">Label text</label>
            <input v-model="editForm.label_text" class="field" placeholder="Label on the line" />
          </div>
        </section>

        <!-- Position (non-line) -->
        <section v-if="selectedObject.type !== 'line'" class="p-4 space-y-2">
          <p class="section-title">Position</p>
          <div class="grid grid-cols-3 gap-2">
            <template v-if="props.mapType === 'worldmap'">
              <div class="space-y-1 col-span-1">
                <label class="text-xs text-zinc-500">Lat</label>
                <input v-model.number="editForm.lat" type="number" step="0.0001" class="field" />
              </div>
              <div class="space-y-1 col-span-1">
                <label class="text-xs text-zinc-500">Lng</label>
                <input v-model.number="editForm.lng" type="number" step="0.0001" class="field" />
              </div>
            </template>
            <template v-else>
              <div class="space-y-1 col-span-1">
                <label class="text-xs text-zinc-500">X</label>
                <input v-model.number="editForm.x" type="number" class="field" />
              </div>
              <div class="space-y-1 col-span-1">
                <label class="text-xs text-zinc-500">Y</label>
                <input v-model.number="editForm.y" type="number" class="field" />
              </div>
            </template>
            <div class="space-y-1 col-span-1">
              <label class="text-xs text-zinc-500">Z</label>
              <input v-model.number="editForm.z" type="number" min="1" max="999" class="field" />
            </div>
          </div>
        </section>

        <!-- Label (non-line) -->
        <section v-if="selectedObject.type !== 'line'" class="p-4 space-y-2">
          <p class="section-title">Label</p>
          <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
            <input type="checkbox" v-model="editForm.label_show" class="rounded accent-indigo-500 w-3.5 h-3.5" />
            Show label
          </label>
          <template v-if="editForm.label_show">
            <div v-if="selectedObject.type !== 'textbox'" class="space-y-1">
              <label class="text-xs text-zinc-500">Text</label>
              <input v-model="editForm.label_text" class="field" placeholder="(auto)" />
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div class="space-y-1">
                <label class="text-xs text-zinc-500">Size</label>
                <input v-model.number="editForm.label_size" type="number" min="8" max="72" class="field" />
              </div>
              <div class="space-y-1">
                <label class="text-xs text-zinc-500">Color</label>
                <div class="flex gap-1.5 items-center">
                  <input type="color" v-model="editForm.label_color"
                    class="w-8 h-8 rounded border-0 bg-transparent cursor-pointer p-0.5 shrink-0" />
                  <input v-model="editForm.label_color" class="field min-w-0" placeholder="#ffffff" />
                </div>
              </div>
              <div class="space-y-1">
                <label class="text-xs text-zinc-500">Offset X</label>
                <input v-model.number="editForm.label_x" type="number" class="field" />
              </div>
              <div class="space-y-1">
                <label class="text-xs text-zinc-500">Offset Y</label>
                <input v-model.number="editForm.label_y" type="number" class="field" />
              </div>
              <div class="space-y-1 col-span-2">
                <label class="text-xs text-zinc-500">Background</label>
                <div class="flex gap-1.5 items-center">
                  <input type="color" v-model="editForm.label_background"
                    class="w-8 h-8 rounded border-0 bg-transparent cursor-pointer p-0.5 shrink-0" />
                  <input v-model="editForm.label_background" class="field min-w-0" placeholder="transparent" />
                </div>
              </div>
            </div>
          </template>
        </section>

        <!-- Appearance (non-line, non-textbox) -->
        <section v-if="selectedObject.type !== 'line' && selectedObject.type !== 'textbox'" class="p-4 space-y-2">
          <p class="section-title">Appearance</p>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">View type</label>
            <select v-model="editForm.view_type" class="field">
              <option value="icon">Icon</option>
              <option value="text">Text only</option>
              <option value="gadget">Gadget</option>
            </select>
          </div>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">Size</label>
            <input
              :value="editForm.icon_size ?? ''"
              @input="editForm.icon_size = ($event.target as HTMLInputElement).value === '' ? null : +($event.target as HTMLInputElement).value"
              type="number" min="1" max="512" class="field" placeholder="map default"
            />
          </div>
          <template v-if="editForm.view_type === 'gadget'">
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Gadget type</label>
              <select v-model="editForm.gadget_type" class="field">
                <option value="gauge">Gauge</option>
                <option value="bar">Bar</option>
                <option value="trafficlight">Traffic light</option>
              </select>
            </div>
            <div class="space-y-1">
              <label class="text-xs text-zinc-500">Metric</label>
              <AutocompleteInput v-model="editForm.gadget_metric" :suggestions="metricSuggestions" placeholder="first metric" />
            </div>
          </template>
          <div v-if="editForm.view_type !== 'gadget'" class="space-y-1">
            <label class="text-xs text-zinc-500">Custom icon</label>
            <input v-model="editForm.icon" class="field font-mono" placeholder="filename.png" />
          </div>
        </section>

        <!-- Link -->
        <section class="p-4 space-y-2">
          <p class="section-title">Link</p>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">URL</label>
            <input v-model="editForm.url" class="field font-mono" placeholder="https://…" />
          </div>
          <div class="space-y-1">
            <label class="text-xs text-zinc-500">Target</label>
            <select v-model="editForm.url_target" class="field">
              <option value="_blank">New tab</option>
              <option value="_self">Same tab</option>
              <option value="_top">Top frame</option>
            </select>
          </div>
        </section>

        <!-- Actions -->
        <div class="p-4 space-y-2">
          <div class="text-xs text-zinc-700 font-mono pb-1">ID: {{ selectedObject.id }}</div>
          <div class="flex gap-2">
            <button type="submit" :disabled="saving || !isDirty"
              class="flex-1 px-3 py-2 rounded-lg font-semibold text-sm text-white transition-all"
              :class="isDirty && !saving
                ? 'bg-indigo-600 hover:bg-indigo-500'
                : 'bg-zinc-700 opacity-50 cursor-not-allowed'">
              {{ saving ? 'Saving…' : 'Save' }}
            </button>
            <button type="button" @click="confirmDelete = true"
              class="px-3 py-2 bg-red-500/10 hover:bg-red-500/20 ring-1 ring-red-500/20 hover:ring-red-500/40 rounded-lg font-semibold text-sm text-red-400 transition-all">
              Delete
            </button>
          </div>
          <ConfirmDialog
            v-if="confirmDelete"
            title="Delete object"
            message="This cannot be undone."
            confirm-label="Delete"
            @confirm="confirmDelete = false; $emit('delete-selected')"
            @cancel="confirmDelete = false"
          />
          <p v-if="saveError" class="text-red-400 text-xs">{{ saveError }}</p>
        </div>

      </form>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, reactive, watch } from 'vue'
import type { MapObject } from '@/types/api'
import type { NewObjectDraft } from '@/composables/useMapEditor'
import { backendsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AutocompleteInput from './AutocompleteInput.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const props = defineProps<{
  draft: NewObjectDraft
  placing: boolean
  selectedObject: MapObject | null
  dragPositions: Record<string, { x: number; y: number }>
  backendId: string
  snapGrid: number
  mapType?: string
}>()

const emit = defineEmits<{
  'start-placing': []
  'delete-selected': []
  'preview-properties': [updates: Record<string, unknown>]
  'save-properties': [updates: Record<string, unknown>]
  'update:snapGrid': [value: number]
  'update:dirty': [value: boolean]
}>()

const auth = useAuthStore()

// ---- Autocomplete for "Add Object" ----

const addObjects = ref<string[]>([])
const addServices = ref<string[]>([])
const loadingAddObjects = ref(false)
const loadingAddServices = ref(false)

async function fetchAddObjects(type: string) {
  if (!props.backendId || !type || type === 'line' || type === 'textbox' || type === 'map') {
    addObjects.value = []; return
  }
  loadingAddObjects.value = true
  try {
    addObjects.value = await backendsApi.objects(props.backendId, type, auth.accessToken!)
  } catch { addObjects.value = [] }
  finally { loadingAddObjects.value = false }
}

async function fetchAddServices(host: string) {
  if (!host || !props.backendId) { addServices.value = []; return }
  loadingAddServices.value = true
  try {
    addServices.value = await backendsApi.objects(props.backendId, 'service', auth.accessToken!, host)
  } catch { addServices.value = [] }
  finally { loadingAddServices.value = false }
}

function onTypeChange() {
  // Clear host/service when switching types to prevent cross-type inheritance
  props.draft.host_name = ''
  props.draft.service_description = ''
  addObjects.value = []; addServices.value = []
  const fetchType = props.draft.type === 'service' || props.draft.type === 'line' ? 'host' : props.draft.type
  fetchAddObjects(fetchType)
}

function onHostChange() {
  fetchAddServices(props.draft.host_name)
}

function onLineHostChange() {
  editServices.value = []
  editForm.service_description = ''
  if (editForm.host_name) {
    backendsApi.objects(props.backendId, 'service', auth.accessToken!, editForm.host_name)
      .then(r => { editServices.value = r }).catch(() => {})
    fetchMetrics(editForm.host_name)
  }
}

watch(() => props.draft.host_name, (host) => {
  if (props.draft.type === 'service' && host && addObjects.value.includes(host))
    fetchAddServices(host)
})

// ---- Metric suggestions ----

const fetchedMetrics = ref<string[]>([])
const metricSuggestions = computed(() => fetchedMetrics.value)

async function fetchMetrics(host: string, service?: string) {
  if (!props.backendId || !host) { fetchedMetrics.value = []; return }
  fetchedMetrics.value = await backendsApi.perfMetrics(
    props.backendId, host, auth.accessToken!, service || undefined,
  ).catch(() => [])
}

// ---- Edit form for selected object ----

const editForm = reactive({
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

const editObjects = ref<string[]>([])
const editServices = ref<string[]>([])
const saving = ref(false)
const saveError = ref('')
const confirmDelete = ref(false)

// Track last populated object ID to avoid re-populating when preview updates the store reference
const lastPopulatedId = ref<string | null>(null)
const isDirty = ref(false)
let _populating = false

watch(isDirty, (val) => emit('update:dirty', val))

watch(() => props.selectedObject, (obj) => {
  if (obj && obj.id === lastPopulatedId.value) {
    // Same object: silently sync position if it changed (e.g. after drag)
    const posChanged = obj.x !== editForm.x || obj.y !== editForm.y
      || (obj.lat != null && obj.lat !== editForm.lat)
      || (obj.lng != null && obj.lng !== editForm.lng)
      || (obj.type === 'line' && (
        (obj.extra?.x2 as number | undefined) !== editForm.x2 ||
        (obj.extra?.y2 as number | undefined) !== editForm.y2
      ))
    if (posChanged) {
      _populating = true
      editForm.x = obj.x ?? 0
      editForm.y = obj.y ?? 0
      editForm.lat = obj.lat ?? 0
      editForm.lng = obj.lng ?? 0
      if (obj.type === 'line') {
        editForm.x2 = (obj.extra?.x2 as number) ?? obj.x + 150
        editForm.y2 = (obj.extra?.y2 as number) ?? obj.y
      }
      Promise.resolve().then(() => { _populating = false })
    }
    return
  }

  isDirty.value = false
  lastPopulatedId.value = obj?.id ?? null
  confirmDelete.value = false
  fetchedMetrics.value = []
  editObjects.value = []
  editServices.value = []

  if (!obj) return

  _populating = true

  editForm.host_name = obj.host_name ?? ''
  editForm.service_description = obj.service_description ?? ''
  editForm.group_name = obj.group_name ?? ''
  editForm.map_name = obj.map_name ?? ''
  editForm.icon = obj.icon ?? ''
  editForm.line_type = obj.line_type ?? null
  editForm.view_type = obj.view_type ?? 'icon'
  editForm.label_show = obj.label_show ?? true
  editForm.label_text = obj.label_text ?? ''
  editForm.label_x = obj.label_x ?? 0
  editForm.label_y = obj.label_y ?? 0
  editForm.label_size = obj.label_size ?? 11
  editForm.label_color = obj.label_color ?? '#ffffff'
  editForm.label_background = obj.label_background ?? 'transparent'
  editForm.gadget_type = obj.gadget_type ?? 'gauge'
  editForm.gadget_metric = obj.gadget_metric ?? ''
  editForm.icon_size = obj.icon_size ?? null
  editForm.url = obj.url ?? ''
  editForm.url_target = obj.url_target ?? '_blank'
  editForm.x = obj.x ?? 0
  editForm.y = obj.y ?? 0
  editForm.lat = obj.lat ?? 0
  editForm.lng = obj.lng ?? 0
  editForm.z = obj.z ?? 1
  editForm.x2 = (obj.extra?.x2 as number) ?? obj.x + 150
  editForm.y2 = (obj.extra?.y2 as number) ?? obj.y
  editForm.weathermap_metric = (obj.extra?.weathermap_metric as string) ?? ''

  // Fetch autocomplete and metrics
  const objType = obj.type === 'service' ? 'host' : obj.type
  backendsApi.objects(props.backendId, objType, auth.accessToken!).then(r => { editObjects.value = r }).catch(() => {})
  if ((obj.type === 'service' || obj.type === 'line') && obj.host_name) {
    backendsApi.objects(props.backendId, 'service', auth.accessToken!, obj.host_name).then(r => { editServices.value = r }).catch(() => {})
  }
  if (obj.host_name) fetchMetrics(obj.host_name, obj.service_description || undefined)

  // Reset _populating after Vue has flushed the queued editForm watcher
  Promise.resolve().then(() => { _populating = false })
}, { immediate: true })

// Emit live preview on every form change; track dirty state
watch(editForm, () => {
  if (!props.selectedObject) return
  if (!_populating) isDirty.value = true
  emit('preview-properties', buildUpdates())
}, { deep: true })

const needsMonitoringObject = computed(() => {
  const t = props.selectedObject?.type
  return t && !['textbox', 'line'].includes(t)
})

function buildUpdates(): Record<string, unknown> {
  const obj = props.selectedObject!
  const updates: Record<string, unknown> = {
    view_type: editForm.view_type,
    gadget_type: editForm.view_type === 'gadget' ? editForm.gadget_type : null,
    gadget_metric: editForm.view_type === 'gadget' ? (editForm.gadget_metric || null) : null,
    icon_size: editForm.icon_size ?? null,
    icon: editForm.icon || null,
    line_type: editForm.line_type,
    label_show: editForm.label_show,
    label_text: editForm.label_text || null,
    label_x: editForm.label_x,
    label_y: editForm.label_y,
    label_size: editForm.label_size,
    label_color: editForm.label_color,
    label_background: editForm.label_background,
    url: editForm.url || null,
    url_target: editForm.url_target,
    z: editForm.z,
  }
  if (obj.type === 'host' || obj.type === 'service')
    updates.host_name = editForm.host_name || null
  if (obj.type === 'service')
    updates.service_description = editForm.service_description || null
  if (obj.type === 'hostgroup' || obj.type === 'servicegroup')
    updates.group_name = editForm.group_name || null
  if (obj.type === 'map')
    updates.map_name = editForm.map_name || null

  if (obj.type === 'line') {
    updates.x = editForm.x
    updates.y = editForm.y
    updates.host_name = editForm.host_name || null
    updates.service_description = editForm.service_description || null
    updates.extra = {
      x2: editForm.x2,
      y2: editForm.y2,
      ...(editForm.line_type === 20 ? { weathermap_metric: editForm.weathermap_metric || null } : {}),
    }
  } else if (props.mapType === 'worldmap') {
    updates.lat = editForm.lat
    updates.lng = editForm.lng
  } else {
    updates.x = editForm.x
    updates.y = editForm.y
  }
  return updates
}

async function saveProperties() {
  saveError.value = ''
  saving.value = true
  try {
    emit('save-properties', buildUpdates())
    isDirty.value = false
  } catch (e: unknown) {
    saveError.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.section-title {
  @apply text-[10px] font-bold text-zinc-500 uppercase tracking-widest;
}
.field {
  @apply w-full px-3 py-2 bg-zinc-800 ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150;
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
