<template>
  <aside class="pdp" @pointerdown.stop>
    <div class="pdp__head">
      <span class="pdp__title">{{ _t('Data browser') }}</span>
      <button class="pdp__x" :title="_t('Close')" @click="emit('close')">×</button>
    </div>
    <div class="pdp__tabs">
      <CmkToggleButtonGroup :model-value="tab" :options="tabOptions" @update:model-value="setTab" />
    </div>
    <input
      v-model="query"
      class="orb-field pdp__search"
      :placeholder="searchPlaceholder"
      :aria-label="searchPlaceholder"
    />
    <div class="pdp__hint">{{ _t('Drag an entry onto the slide') }}</div>
    <CmkScrollContainer class="pdp__list-wrap">
      <div class="pdp__list">
        <CmkLoading v-if="loading" />
        <div v-else-if="!filteredRows.length" class="pdp__empty">
          {{ query ? _t('Nothing matches your search') : _t('Nothing available') }}
        </div>

        <!-- Hosts with lazily expanded services -->
        <template v-if="tab === 'hosts'">
          <template v-for="row in filteredRows" :key="row.name">
            <div
              class="pdp__row pdp__row--host"
              draggable="true"
              @dragstart="onDragStart($event, { kind: 'host', name: row.name })"
            >
              <button
                class="pdp__chev"
                :class="{ 'pdp__chev--open': expanded.has(row.name) }"
                :title="expanded.has(row.name) ? _t('Collapse') : _t('Show services')"
                @click.stop="toggleHost(row.name)"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </button>
              <span
                v-if="stateDotFor({ kind: 'host', name: row.name })"
                class="pdp__dot"
                :style="{ background: stateDotFor({ kind: 'host', name: row.name }) ?? undefined }"
              />
              <span class="pdp__name" :title="row.name">{{ row.name }}</span>
              <span v-if="onSlide({ kind: 'host', name: row.name })" class="pdp__chip">
                {{ _t('On slide') }}
              </span>
            </div>
            <template v-if="expanded.has(row.name)">
              <CmkLoading v-if="loadingServices.has(row.name)" />
              <div
                v-for="svc in servicesByHost[row.name] ?? []"
                :key="`${row.name}|${svc}`"
                class="pdp__row pdp__row--svc"
                draggable="true"
                @dragstart="onDragStart($event, { kind: 'host', name: row.name, service: svc })"
              >
                <span
                  v-if="stateDotFor({ kind: 'host', name: row.name, service: svc })"
                  class="pdp__dot"
                  :style="{
                    background:
                      stateDotFor({ kind: 'host', name: row.name, service: svc }) ?? undefined
                  }"
                />
                <span class="pdp__name" :title="svc">{{ svc }}</span>
                <span
                  v-if="onSlide({ kind: 'host', name: row.name, service: svc })"
                  class="pdp__chip"
                >
                  {{ _t('On slide') }}
                </span>
              </div>
              <div
                v-if="
                  !loadingServices.has(row.name) && (servicesByHost[row.name] ?? []).length === 0
                "
                class="pdp__empty pdp__empty--svc"
              >
                {{ _t('No services') }}
              </div>
            </template>
          </template>
        </template>

        <!-- Host-/servicegroups and BI aggregations: flat draggable lists -->
        <template v-else>
          <div
            v-for="row in filteredRows"
            :key="`${row.kind}|${row.name}`"
            class="pdp__row pdp__row--host"
            draggable="true"
            @dragstart="onDragStart($event, { kind: row.kind, name: row.name })"
          >
            <span
              v-if="stateDotFor(row)"
              class="pdp__dot"
              :style="{ background: stateDotFor(row) ?? undefined }"
            />
            <span class="pdp__name" :title="row.title">{{ row.title }}</span>
            <span v-if="onSlide(row)" class="pdp__chip">{{ _t('On slide') }}</span>
          </div>
        </template>

        <div v-if="truncated > 0" class="pdp__more">
          {{ _t('+%{n} more — keep typing to narrow results', { n: String(truncated) }) }}
        </div>
      </div>
    </CmkScrollContainer>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import CmkLoading from '@/components/cmk/CmkLoading'
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'
import CmkToggleButtonGroup from '@/components/cmk/CmkToggleButtonGroup'

import { useDataBinding } from '@/composables/useDataBinding'
import type { ObjectState, PresentationElement } from '@/types/api'
import {
  BINDING_DROP_MIME,
  type BindingDropKind,
  type BindingDropPayload
} from '@/utils/presentationBindingDrop'
import { isBindable } from '@/utils/presentationSampleState'
import { stateColor } from '@/utils/stateColors'
import usei18n from '@/vendor/cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  connectionId: string
  elements: PresentationElement[]
  states: Record<string, ObjectState>
}>()

const emit = defineEmits<{ close: [] }>()

const ROW_LIMIT = 200

const binding = useDataBinding(() => props.connectionId)

type Tab = 'hosts' | 'groups' | 'bi'
const tab = ref<Tab>('hosts')
const tabOptions = computed(() => [
  { label: _t('Hosts'), value: 'hosts' },
  { label: _t('Groups'), value: 'groups' },
  { label: 'BI', value: 'bi' }
])
function setTab(v: string): void {
  tab.value = v as Tab
}

interface Row {
  kind: BindingDropKind
  name: string
  title: string
}

const hosts = ref<string[]>([])
const hostgroups = ref<string[]>([])
const servicegroups = ref<string[]>([])
const aggregations = ref<Row[]>([])
const loading = ref(false)
const query = ref('')
const expanded = reactive(new Set<string>())
const loadingServices = reactive(new Set<string>())
const servicesByHost = reactive<Record<string, string[]>>({})

const loadedTabs = new Set<Tab>()

// A connection switch invalidates every loaded tab — reload the visible one,
// the rest refetch lazily on their next visit.
watch(
  () => props.connectionId,
  () => {
    loadedTabs.clear()
    void loadTab(tab.value)
  }
)

async function loadTab(t: Tab): Promise<void> {
  if (loadedTabs.has(t)) return
  loadedTabs.add(t)
  loading.value = true
  if (t === 'hosts') {
    hosts.value = await binding.hosts()
  } else if (t === 'groups') {
    const [hg, sg] = await Promise.all([binding.hostgroups(), binding.servicegroups()])
    hostgroups.value = hg
    servicegroups.value = sg
  } else {
    aggregations.value = (await binding.aggregations()).map((a) => ({
      kind: 'aggregation' as const,
      name: a.id,
      title: a.title || a.id
    }))
  }
  loading.value = false
}

onMounted(() => void loadTab('hosts'))
watch(tab, (t) => void loadTab(t))

const searchPlaceholder = computed(() =>
  tab.value === 'hosts'
    ? _t('Search hosts…')
    : tab.value === 'groups'
      ? _t('Search groups…')
      : _t('Search aggregations…')
)

const allRows = computed<Row[]>(() => {
  if (tab.value === 'hosts') {
    return hosts.value.map((h) => ({ kind: 'host' as const, name: h, title: h }))
  }
  if (tab.value === 'groups') {
    return [
      ...hostgroups.value.map((g) => ({ kind: 'hostgroup' as const, name: g, title: g })),
      ...servicegroups.value.map((g) => ({ kind: 'servicegroup' as const, name: g, title: g }))
    ]
  }
  return aggregations.value
})

const matchingRows = computed(() => {
  const q = query.value.toLowerCase()
  const list = q ? allRows.value.filter((r) => r.title.toLowerCase().includes(q)) : allRows.value
  return [...list].sort((a, b) => a.title.localeCompare(b.title))
})
const filteredRows = computed(() => matchingRows.value.slice(0, ROW_LIMIT))
const truncated = computed(() => Math.max(0, matchingRows.value.length - ROW_LIMIT))

async function toggleHost(host: string): Promise<void> {
  if (expanded.has(host)) {
    expanded.delete(host)
    return
  }
  expanded.add(host)
  if (!servicesByHost[host]) {
    loadingServices.add(host)
    servicesByHost[host] = await binding.services(host)
    loadingServices.delete(host)
  }
}

// Live state is only known for objects already bound on the slide (states
// arrive keyed by element id) — show a worst-state dot for exactly those, and
// an "On slide" chip so the operator sees what's already wired up.
function bindingKey(kind: BindingDropKind, name: string, service?: string | null): string {
  return `${kind}|${name}|${service ?? ''}`
}

const boundStates = computed(() => {
  const map = new Map<string, string>()
  for (const el of props.elements) {
    if (!isBindable(el)) continue
    let key: string | null = null
    if (el.aggregation_id) key = bindingKey('aggregation', el.aggregation_id)
    else if (el.group_name && el.object_type === 'hostgroup')
      key = bindingKey('hostgroup', el.group_name)
    else if (el.group_name && el.object_type === 'servicegroup') {
      key = bindingKey('servicegroup', el.group_name)
    } else if (el.host_name) key = bindingKey('host', el.host_name, el.service_description)
    if (!key) continue
    const st = props.states[el.id]?.state
    if (st && !map.has(key)) map.set(key, st)
  }
  return map
})

function onSlide(p: { kind: BindingDropKind; name: string; service?: string | null }): boolean {
  return boundStates.value.has(bindingKey(p.kind, p.name, p.service))
}

function stateDotFor(p: {
  kind: BindingDropKind
  name: string
  service?: string | null
}): string | null {
  const st = boundStates.value.get(bindingKey(p.kind, p.name, p.service))
  return st ? stateColor(st) : null
}

function onDragStart(e: DragEvent, payload: BindingDropPayload): void {
  if (!e.dataTransfer) return
  e.dataTransfer.setData(BINDING_DROP_MIME, JSON.stringify(payload))
  e.dataTransfer.effectAllowed = 'copy'
}
</script>

<style scoped>
.pdp {
  display: flex;
  flex-direction: column;
  width: 260px;
  flex-shrink: 0;
  background: var(--bg-surface, #1b1f2a);
  border-right: 1px solid var(--border, rgb(255 255 255 / 8%));
  color: var(--text, #e5e7eb);
  z-index: 5;
}

.pdp__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border, rgb(255 255 255 / 8%));
  min-height: 44px;
  box-sizing: border-box;
}

.pdp__title {
  font-weight: 600;
  font-size: var(--font-size-large);
}

.pdp__x {
  border: none;
  background: transparent;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
}

.pdp__tabs {
  padding: 10px 12px 0;
}

.pdp__search {
  margin: 10px 12px 0;
  width: calc(100% - 24px);
}

.pdp__hint {
  padding: 6px 12px 8px;
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}

.pdp__list-wrap {
  flex: 1;
  min-height: 0;
}

.pdp__list {
  display: flex;
  flex-direction: column;
  padding-bottom: 8px;
}

.pdp__row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  cursor: grab;
}

.pdp__row:hover {
  background: var(--bg-hover, rgb(255 255 255 / 6%));
}

.pdp__row--svc {
  padding-left: 34px;
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}

.pdp__row--svc:hover {
  color: var(--text);
}

.pdp__chev {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: transform 0.12s ease;
}

.pdp__chev svg {
  width: 10px;
  height: 10px;
}

.pdp__chev--open {
  transform: rotate(90deg);
}

.pdp__dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 9999px;
}

.pdp__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pdp__chip {
  flex-shrink: 0;
  padding: 1px 6px;
  border: 1px solid var(--color-corporate-green-50);
  border-radius: 9999px;
  font-size: 10px;
  color: var(--color-corporate-green-50);
}

.pdp__empty {
  padding: 10px 12px;
  font-size: var(--font-size-normal);
  color: var(--text-muted);
}

.pdp__empty--svc {
  padding-left: 34px;
}

.pdp__more {
  padding: 8px 12px;
  font-size: var(--font-size-normal);
  font-style: italic;
  color: var(--text-muted);
  border-top: 1px solid var(--border, rgb(255 255 255 / 8%));
}
</style>
