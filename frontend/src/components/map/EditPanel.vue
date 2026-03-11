<template>
  <div class="flex flex-col min-h-0 text-sm">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-white/8 flex items-center gap-2 shrink-0">
      <svg class="w-4 h-4 text-indigo-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      <div class="flex-1 min-w-0">
        <div class="font-semibold text-[var(--text)] text-sm">{{ t('mapSettings.addObject') }}</div>
        <div class="text-[10px] text-zinc-500 mt-0.5">{{ t('mapSettings.dragObjects') }}</div>
      </div>
    </div>

    <!-- Add Object form -->
    <div class="p-4 space-y-2.5">
      <select v-model="draft.type" @change="onTypeChange"
        class="w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all">
        <option value="">{{ t('mapSettings.selectType') }}</option>
        <option value="host">{{ t('mapSettings.typeHost') }}</option>
        <option value="service">{{ t('mapSettings.typeService') }}</option>
        <option value="hostgroup">{{ t('mapSettings.typeHostgroup') }}</option>
        <option value="servicegroup">{{ t('mapSettings.typeServicegroup') }}</option>
        <option value="map">{{ t('mapSettings.typeMap') }}</option>
        <option value="line">{{ t('mapSettings.typeLine') }}</option>
        <option value="textbox">{{ t('mapSettings.typeTextbox') }}</option>
        <option value="shape">{{ t('mapSettings.typeShape') }}</option>
      </select>

      <template v-if="draft.type === 'host'">
        <AutocompleteInput v-model="draft.host_name" :suggestions="addObjects" :loading="loadingAddObjects" :placeholder="t('mapSettings.hostname')" />
      </template>

      <template v-else-if="draft.type === 'service'">
        <AutocompleteInput v-model="draft.host_name" :suggestions="addObjects" :loading="loadingAddObjects" :placeholder="t('mapSettings.hostname')" @change="onHostChange" />
        <AutocompleteInput v-model="draft.service_description" :suggestions="addServices" :loading="loadingAddServices" :placeholder="t('mapSettings.serviceDescription')" />
      </template>

      <template v-else-if="draft.type === 'hostgroup' || draft.type === 'servicegroup'">
        <AutocompleteInput v-model="draft.group_name" :suggestions="addObjects" :loading="loadingAddObjects" :placeholder="t('mapSettings.groupName')" />
      </template>

      <template v-else-if="draft.type === 'map'">
        <input v-model="draft.map_name" :placeholder="t('mapSettings.mapName')" class="field" />
        <input v-model="draft.label_text" :placeholder="t('mapSettings.labelOptional')" class="field" />
      </template>

      <template v-else-if="draft.type === 'line'">
        <AutocompleteInput v-model="draft.host_name" :suggestions="addObjects" :loading="loadingAddObjects" :placeholder="t('mapSettings.hostname') + ' (optional)'" @change="onHostChange" />
        <AutocompleteInput v-model="draft.service_description" :suggestions="addServices" :loading="loadingAddServices" :placeholder="t('mapSettings.serviceOptional')" />
      </template>

      <template v-else-if="draft.type === 'textbox'">
        <input v-model="draft.label_text" :placeholder="t('mapSettings.textContent')" class="field" />
      </template>

      <template v-else-if="draft.type === 'shape'">
        <IconPicker v-model="draft.icon" />
        <input v-model="draft.label_text" :placeholder="t('mapSettings.labelOptional')" class="field" />
      </template>

      <!-- Grid snap -->
      <div class="flex items-center justify-between gap-2 pt-0.5">
        <label class="text-xs text-zinc-500 select-none">{{ t('mapSettings.grid') }}</label>
        <select :value="snapGrid" @change="$emit('update:snapGrid', +($event.target as HTMLSelectElement).value)"
          class="bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-md px-2 py-1.5 text-xs text-zinc-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all cursor-pointer">
          <option value="0">{{ t('mapSettings.gridOff') }}</option>
          <option value="10">10 px</option>
          <option value="20">20 px</option>
          <option value="50">50 px</option>
        </select>
      </div>

      <button v-if="draft.type" @click="$emit('start-placing')"
        class="w-full px-3 py-2 rounded-lg font-semibold text-sm transition-all duration-150"
        :class="placing
          ? 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30 animate-pulse'
          : 'bg-indigo-600 hover:bg-indigo-500 text-white'">
        {{ placing ? t('mapSettings.clickToPlace') : t('mapSettings.placeOnMap') }}
      </button>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { NewObjectDraft } from '@/composables/useMapEditor'
import { backendsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import AutocompleteInput from './AutocompleteInput.vue'
import IconPicker from './IconPicker.vue'

const { t } = useI18n()

const props = defineProps<{
  draft: NewObjectDraft
  placing: boolean
  backendId: string
  snapGrid: number
}>()

defineEmits<{
  'start-placing': []
  'update:snapGrid': [value: number]
  'close-edit-mode': []
}>()

const auth = useAuthStore()

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
  props.draft.host_name = ''
  props.draft.service_description = ''
  addObjects.value = []; addServices.value = []
  const fetchType = props.draft.type === 'service' || props.draft.type === 'line' ? 'host' : props.draft.type
  fetchAddObjects(fetchType)
}

function onHostChange() {
  fetchAddServices(props.draft.host_name)
}

watch(() => props.draft.host_name, (host) => {
  if (props.draft.type === 'service' && host && addObjects.value.includes(host))
    fetchAddServices(host)
})
</script>

<style scoped>
.field {
  @apply w-full px-3 py-2 bg-[var(--bg-input)] ring-1 ring-zinc-700 rounded-lg text-sm text-[var(--text)] placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-150;
}
</style>
