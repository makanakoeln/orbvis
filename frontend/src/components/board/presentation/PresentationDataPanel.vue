<template>
  <aside class="pdp" @pointerdown.stop>
    <div class="pdp__head">
      <span class="pdp__title">{{ _t('Data browser') }}</span>
      <button class="pdp__x" :title="_t('Close')" @click="emit('close')">×</button>
    </div>
    <input
      v-model="query"
      class="orb-field pdp__search"
      :placeholder="_t('Search hosts…')"
      :aria-label="_t('Search hosts…')"
    />
    <div class="pdp__hint">{{ _t('Drag a host or service onto the slide') }}</div>
    <CmkScrollContainer class="pdp__list-wrap">
      <div class="pdp__list">
        <CmkLoading v-if="loadingHosts" />
        <div v-else-if="!filteredHosts.length" class="pdp__empty">
          {{ query ? _t('No hosts match your search') : _t('No hosts available') }}
        </div>
        <template v-for="host in filteredHosts" :key="host">
          <div
            class="pdp__row pdp__row--host"
            draggable="true"
            @dragstart="onDragStart($event, host, null)"
          >
            <button
              class="pdp__chev"
              :class="{ 'pdp__chev--open': expanded.has(host) }"
              :title="expanded.has(host) ? _t('Collapse') : _t('Show services')"
              @click.stop="toggleHost(host)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M9 6l6 6-6 6" />
              </svg>
            </button>
            <span
              v-if="stateDotFor(host, null)"
              class="pdp__dot"
              :style="{ background: stateDotFor(host, null) ?? undefined }"
            />
            <span class="pdp__name" :title="host">{{ host }}</span>
            <span v-if="onSlide(host, null)" class="pdp__chip">{{ _t('On slide') }}</span>
          </div>
          <template v-if="expanded.has(host)">
            <CmkLoading v-if="loadingServices.has(host)" />
            <div
              v-for="svc in servicesByHost[host] ?? []"
              :key="`${host}|${svc}`"
              class="pdp__row pdp__row--svc"
              draggable="true"
              @dragstart="onDragStart($event, host, svc)"
            >
              <span
                v-if="stateDotFor(host, svc)"
                class="pdp__dot"
                :style="{ background: stateDotFor(host, svc) ?? undefined }"
              />
              <span class="pdp__name" :title="svc">{{ svc }}</span>
              <span v-if="onSlide(host, svc)" class="pdp__chip">{{ _t('On slide') }}</span>
            </div>
            <div
              v-if="!loadingServices.has(host) && (servicesByHost[host] ?? []).length === 0"
              class="pdp__empty pdp__empty--svc"
            >
              {{ _t('No services') }}
            </div>
          </template>
        </template>
        <div v-if="truncated > 0" class="pdp__more">
          {{ _t('+%{n} more — keep typing to narrow results', { n: String(truncated) }) }}
        </div>
      </div>
    </CmkScrollContainer>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import CmkLoading from '@/components/cmk/CmkLoading'
import CmkScrollContainer from '@/components/cmk/CmkScrollContainer'

import { useDataBinding } from '@/composables/useDataBinding'
import type { ObjectState, PresentationElement } from '@/types/api'
import { BINDING_DROP_MIME } from '@/utils/presentationBindingDrop'
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

const HOST_LIMIT = 200

const binding = useDataBinding(() => props.connectionId)

const hosts = ref<string[]>([])
const loadingHosts = ref(false)
const query = ref('')
const expanded = reactive(new Set<string>())
const loadingServices = reactive(new Set<string>())
const servicesByHost = reactive<Record<string, string[]>>({})

onMounted(async () => {
  loadingHosts.value = true
  hosts.value = await binding.hosts()
  loadingHosts.value = false
})

const matchingHosts = computed(() => {
  const q = query.value.toLowerCase()
  const list = q ? hosts.value.filter((h) => h.toLowerCase().includes(q)) : hosts.value
  return [...list].sort((a, b) => a.localeCompare(b))
})
const filteredHosts = computed(() => matchingHosts.value.slice(0, HOST_LIMIT))
const truncated = computed(() => Math.max(0, matchingHosts.value.length - HOST_LIMIT))

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
const boundStates = computed(() => {
  const map = new Map<string, string>()
  for (const el of props.elements) {
    if (!isBindable(el) || !el.host_name) continue
    const key = `${el.host_name}|${el.service_description ?? ''}`
    const st = props.states[el.id]?.state
    if (st && !map.has(key)) map.set(key, st)
  }
  return map
})

function onSlide(host: string, service: string | null): boolean {
  return boundStates.value.has(`${host}|${service ?? ''}`)
}

function stateDotFor(host: string, service: string | null): string | null {
  const st = boundStates.value.get(`${host}|${service ?? ''}`)
  return st ? stateColor(st) : null
}

function onDragStart(e: DragEvent, host: string, service: string | null): void {
  if (!e.dataTransfer) return
  e.dataTransfer.setData(BINDING_DROP_MIME, JSON.stringify({ host, service }))
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
