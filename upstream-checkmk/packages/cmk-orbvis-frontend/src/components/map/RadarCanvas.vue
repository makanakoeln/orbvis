<template>
  <div class="orb-radar">
    <div v-if="loading" class="orb-radar__loading">
      <CmkLoading />
    </div>
    <div v-else-if="!sortedStates.length" class="orb-radar__empty">
      <div class="orb-radar__empty-icon">
        <svg
          class="orb-radar__empty-glyph"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.121a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.807-3.808-9.98 0-13.788m13.788 0c3.808 3.807 3.808 9.98 0 13.788M12 12h.008v.008H12V12z"
          />
        </svg>
      </div>
      <p class="orb-radar__empty-title">
        {{ _t('No objects found') }}
      </p>
      <p class="orb-radar__empty-hint">
        <span>{{ _t('Adjust the filter via map settings') }}</span>
        <svg
          class="orb-radar__hint-gear"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="1.5"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </p>
    </div>

    <template v-else>
      <div class="orb-radar__summary">
        <span class="orb-radar__count"
          >{{ totalCount }} objects<template v-if="compactOverflow > 0"
            ><span class="orb-radar__count-note">
              (showing {{ sortedStates.length }})</span
            ></template
          ></span
        >
        <div class="orb-radar__legend">
          <span
            v-for="s in summary"
            :key="s.state"
            class="orb-radar__sum"
            :class="stateTextClass(s.state)"
          >
            <span class="orb-radar__dot" :class="stateDotClass(s.state)" />
            {{ s.count }} {{ s.state }}
          </span>
        </div>
      </div>

      <div
        class="orb-radar__grid"
        :class="compact ? 'orb-radar__grid--compact' : ''"
        :style="
          compact
            ? 'grid-template-columns: repeat(auto-fill, minmax(110px, 1fr))'
            : 'grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))'
        "
      >
        <div
          v-for="state in sortedStates"
          :key="state.object_id"
          class="orb-radar__card"
          :class="[cardClass(state.state), compact ? 'orb-radar__card--compact' : '']"
          @click="onCardClick(state, $event)"
        >
          <div class="orb-radar__card-head">
            <span
              class="orb-radar__name"
              :class="[nameClass(state.state), compact ? 'orb-radar__name--compact' : '']"
            >
              {{ displayName(state) }}
            </span>
            <div v-if="!compact" class="orb-radar__flags">
              <span v-if="state.acknowledged" title="Acknowledged" class="orb-radar__flag">
                <svg
                  class="orb-radar__flag-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </span>
              <span v-if="state.in_downtime" title="In downtime" class="orb-radar__flag">
                <svg
                  class="orb-radar__flag-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </span>
            </div>
          </div>

          <span
            class="orb-radar__badge"
            :class="[badgeClass(state.state), compact ? 'orb-radar__badge--compact' : '']"
          >
            <span class="orb-radar__dot orb-radar__dot--sm" :class="stateDotClass(state.state)" />
            {{ state.state }}
          </span>

          <p
            v-if="state.output && !compact"
            class="orb-radar__output"
            :class="nameClass(state.state)"
          >
            {{ state.output }}
          </p>
        </div>
        <div
          v-if="compactOverflow > 0"
          class="orb-radar__overflow"
          :title="
            _t(
              'Preview shows the worst-state objects only. Open the map to see all %{hidden} additional objects.',
              { hidden: compactOverflow }
            )
          "
        >
          {{ _t('Preview limited — %{hidden} more not shown', { hidden: compactOverflow }) }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import CmkLoading from '@/components/cmk/CmkLoading'

import type { MapObject, ObjectState } from '@/types/api'
import { type FilterField, matchesFilterTerms, parseFilterTerms } from '@/utils/objectFilter'
import { isProblemState } from '@/utils/problemState'
import usei18n from '@cmk/lib/i18n'

const { _t } = usei18n()

const props = defineProps<{
  states: Record<string, ObjectState>
  checkmkUrl?: string | null
  readonly?: boolean
  filterNeedle?: string
  problemsOnly?: boolean
  compact?: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  'object-click': [obj: MapObject, event: MouseEvent]
}>()

function stateToMapObject(state: ObjectState): MapObject {
  if (state.type === 'service' && state.object_id.includes(';')) {
    const [host = '', svc = ''] = state.object_id.split(';', 2)
    return {
      id: state.object_id,
      type: 'service',
      host_name: host,
      service_description: svc,
      x: 0,
      y: 0,
      z: 0,
      url_target: '_blank'
    }
  }
  return {
    id: state.object_id,
    type: 'host',
    host_name: state.object_id,
    x: 0,
    y: 0,
    z: 0,
    url_target: '_blank'
  }
}

function onCardClick(state: ObjectState, event: MouseEvent) {
  if (props.compact) return
  emit('object-click', stateToMapObject(state), event)
}

// State severity for sorting (worst first)
const severity: Record<string, number> = {
  DOWN: 5,
  CRITICAL: 5,
  UNREACHABLE: 4,
  WARNING: 3,
  UNKNOWN: 3,
  PENDING: 1,
  UP: 0,
  OK: 0
}

const COMPACT_LIMIT = 12

const filterTerms = computed(() => parseFilterTerms(props.filterNeedle ?? ''))

function radarFieldValue(s: ObjectState, field: FilterField): string[] {
  const isService = s.type === 'service' && s.object_id.includes(';')
  const [host = '', svc = ''] = isService ? s.object_id.split(';', 2) : [s.object_id, '']
  switch (field) {
    case 'host':
      return s.type === 'host' || isService ? [host, s.alias ?? ''] : []
    case 'service':
      return isService ? [svc] : []
    case 'id':
      return [s.object_id]
    case 'any':
      return [s.object_id, host, svc, s.alias ?? '']
    case 'hostgroup':
    case 'servicegroup':
      return []
  }
}

function stateMatchesFilter(s: ObjectState): boolean {
  return matchesFilterTerms(filterTerms.value, (field) => radarFieldValue(s, field))
}

function passesFilters(s: ObjectState): boolean {
  if (filterTerms.value.length && !stateMatchesFilter(s)) return false
  if (props.problemsOnly && !isProblemState(s.state)) return false
  return true
}

const sortedStates = computed(() => {
  const all = Object.values(props.states).sort(
    (a, b) => (severity[b.state] ?? 0) - (severity[a.state] ?? 0)
  )
  const filtered = all.filter(passesFilters)
  return props.compact ? filtered.slice(0, COMPACT_LIMIT) : filtered
})

const totalCount = computed(() => Object.values(props.states).filter(passesFilters).length)

const compactOverflow = computed(() => {
  if (!props.compact) return 0
  return Math.max(0, totalCount.value - COMPACT_LIMIT)
})

const summary = computed(() => {
  const counts: Record<string, number> = {}
  for (const s of sortedStates.value) {
    counts[s.state] = (counts[s.state] ?? 0) + 1
  }
  return Object.entries(counts)
    .map(([state, count]) => ({ state, count }))
    .sort((a, b) => (severity[b.state] ?? 0) - (severity[a.state] ?? 0))
})

function displayName(state: ObjectState): string {
  if (state.type === 'service' && state.object_id.includes(';')) {
    const [host, svc] = state.object_id.split(';', 2)
    return `${host} · ${svc}`
  }
  return state.object_id
}

function cardClass(state: string): string {
  switch (state) {
    case 'DOWN':
    case 'CRITICAL':
      return 'orb-radar__card--crit'
    case 'UNREACHABLE':
      return 'orb-radar__card--unreach'
    case 'WARNING':
    case 'UNKNOWN':
      return 'orb-radar__card--warn'
    case 'UP':
    case 'OK':
      return 'orb-radar__card--ok'
    default:
      return 'orb-radar__card--neutral'
  }
}

function nameClass(state: string): string {
  switch (state) {
    case 'DOWN':
    case 'CRITICAL':
      return 'orb-radar__ink--crit'
    case 'UNREACHABLE':
      return 'orb-radar__ink--unreach'
    case 'WARNING':
    case 'UNKNOWN':
      return 'orb-radar__ink--warn'
    case 'UP':
    case 'OK':
      return 'orb-radar__ink--ok'
    default:
      return 'orb-radar__ink--muted'
  }
}

function badgeClass(state: string): string {
  switch (state) {
    case 'DOWN':
    case 'CRITICAL':
      return 'orb-radar__badge--crit'
    case 'UNREACHABLE':
      return 'orb-radar__badge--unreach'
    case 'WARNING':
    case 'UNKNOWN':
      return 'orb-radar__badge--warn'
    case 'UP':
    case 'OK':
      return 'orb-radar__badge--ok'
    default:
      return 'orb-radar__badge--neutral'
  }
}

function stateDotClass(state: string): string {
  switch (state) {
    case 'DOWN':
    case 'CRITICAL':
      return 'orb-radar__dot--crit'
    case 'UNREACHABLE':
      return 'orb-radar__dot--unreach'
    case 'WARNING':
    case 'UNKNOWN':
      return 'orb-radar__dot--warn'
    case 'UP':
    case 'OK':
      return 'orb-radar__dot--ok'
    default:
      return 'orb-radar__dot--pending'
  }
}

function stateTextClass(state: string): string {
  switch (state) {
    case 'DOWN':
    case 'CRITICAL':
      return 'orb-radar__sum--crit'
    case 'UNREACHABLE':
      return 'orb-radar__sum--unreach'
    case 'WARNING':
    case 'UNKNOWN':
      return 'orb-radar__sum--warn'
    case 'UP':
    case 'OK':
      return 'orb-radar__sum--ok'
    default:
      return 'orb-radar__sum--muted'
  }
}
</script>

<style scoped>
.orb-radar {
  overflow: auto;
  flex: 1;
  padding: var(--dimension-8);
  background: var(--bg);
}

.orb-radar__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.orb-radar__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.orb-radar__empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: var(--dimension-6);
  background: var(--default-form-element-bg-color);
  border-radius: 16px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-radar__empty-glyph {
  width: 28px;
  height: 28px;
  color: var(--text-muted);
}

.orb-radar__empty-title {
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 500;
  color: var(--text-muted);
}

.orb-radar__empty-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: var(--dimension-3);
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-radar__hint-gear {
  display: inline-block;
  width: 14px;
  height: 14px;
}

.orb-radar__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-6);
  margin-bottom: var(--dimension-7);
}

.orb-radar__count {
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--text-muted);
}

.orb-radar__count-note {
  font-style: italic;
}

.orb-radar__legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-5);
}

.orb-radar__sum {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: 500;
}

.orb-radar__sum--crit {
  color: var(--color-light-red-40);
}

.orb-radar__sum--unreach {
  color: var(--color-orange-40);
}

.orb-radar__sum--warn {
  color: var(--color-warning);
}

.orb-radar__sum--ok {
  color: var(--color-corporate-green-50);
}

.orb-radar__sum--muted {
  color: var(--text-muted);
}

.orb-radar__dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
}

.orb-radar__dot--sm {
  width: var(--dimension-3);
  height: var(--dimension-3);
}

.orb-radar__dot--crit {
  background: var(--color-light-red-40);
}

.orb-radar__dot--unreach {
  background: var(--color-orange-40);
}

.orb-radar__dot--warn {
  background: var(--color-warning);
}

.orb-radar__dot--ok {
  background: var(--color-corporate-green-50);
}

.orb-radar__dot--pending {
  background: var(--color-pending);
}

.orb-radar__grid {
  display: grid;
  gap: 10px;
}

.orb-radar__grid--compact {
  gap: var(--dimension-3);
}

.orb-radar__card {
  --radar-card-ring: var(--border);
  --radar-card-shadow: rgb(0 0 0 / 10%);

  padding: 14px;
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--radar-card-ring);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.orb-radar__card:not(.orb-radar__card--compact):hover {
  transform: translateY(-2px);
  box-shadow:
    0 0 0 1px var(--radar-card-ring),
    0 10px 15px -3px var(--radar-card-shadow),
    0 4px 6px -4px var(--radar-card-shadow);
}

.orb-radar__card--compact {
  padding: var(--dimension-4);
}

.orb-radar__card--crit {
  --radar-card-ring: color-mix(in srgb, var(--color-light-red-50) 20%, transparent);
  --radar-card-shadow: color-mix(in srgb, var(--color-light-red-90) 20%, transparent);

  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
}

.orb-radar__card--unreach {
  --radar-card-ring: color-mix(in srgb, var(--color-orange-50) 20%, transparent);
  --radar-card-shadow: color-mix(in srgb, var(--color-orange-90) 20%, transparent);

  background: color-mix(in srgb, var(--color-orange-50) 8%, transparent);
}

.orb-radar__card--warn {
  --radar-card-ring: color-mix(in srgb, var(--color-warning) 20%, transparent);
  --radar-card-shadow: color-mix(in srgb, var(--color-yellow-90) 20%, transparent);

  background: color-mix(in srgb, var(--color-warning) 8%, transparent);
}

.orb-radar__card--ok {
  --radar-card-ring: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
  --radar-card-shadow: color-mix(in srgb, var(--color-corporate-green-90) 20%, transparent);

  background: color-mix(in srgb, var(--color-corporate-green-50) 8%, transparent);
}

.orb-radar__card--neutral {
  background: var(--default-form-element-bg-color);
}

.orb-radar__card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--dimension-4);
  margin-bottom: var(--dimension-4);
}

.orb-radar__name {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: var(--font-size-normal);
  line-height: 1.25;
  font-weight: 600;
  word-break: break-all;
}

.orb-radar__name--compact {
  font-size: 10px;
}

.orb-radar__ink--crit {
  color: var(--color-light-red-40);
}

.orb-radar__ink--unreach {
  color: var(--color-orange-30);
}

.orb-radar__ink--warn {
  color: var(--color-warning);
}

.orb-radar__ink--ok {
  color: var(--color-corporate-green-50);
}

.orb-radar__ink--muted {
  color: var(--text-muted);
}

.orb-radar__flags {
  display: flex;
  flex-shrink: 0;
  gap: var(--dimension-3);
  margin-top: var(--dimension-2);
}

.orb-radar__flag {
  color: var(--text-muted);
  opacity: 0.7;
}

.orb-radar__flag-icon {
  width: var(--dimension-5);
  height: var(--dimension-5);
}

.orb-radar__badge {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) 6px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border-radius: 6px;
}

.orb-radar__badge--compact {
  font-size: 9px;
}

.orb-radar__badge--crit {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 15%, transparent);
}

.orb-radar__badge--unreach {
  color: var(--color-orange-40);
  background: color-mix(in srgb, var(--color-orange-50) 15%, transparent);
}

.orb-radar__badge--warn {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 15%, transparent);
}

.orb-radar__badge--ok {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
}

.orb-radar__badge--neutral {
  color: var(--text-muted);
  background: var(--bg-hover);
}

.orb-radar__output {
  overflow: hidden;
  display: -webkit-box;
  margin-top: var(--dimension-4);
  font-size: 11px;
  line-height: 1.375;
  opacity: 0.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.orb-radar__overflow {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--text-muted);
}
</style>
