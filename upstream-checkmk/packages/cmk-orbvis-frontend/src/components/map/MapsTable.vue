<template>
  <div class="orb-btable">
    <table class="orb-btable__table">
      <thead>
        <tr class="orb-btable__head-row">
          <th v-if="auth.canCreateMaps" class="orb-btable__check-col">
            <CmkCheckbox
              v-if="capabilities.formSpecs"
              :model-value="allSelected"
              @update:model-value="$emit('toggle-select-all', $event)"
            />
            <input
              v-else
              type="checkbox"
              :checked="allSelected"
              @change="$emit('toggle-select-all', ($event.target as HTMLInputElement).checked)"
            />
          </th>
          <th
            v-for="col in visibleColumns"
            :key="col.id"
            class="orb-btable__th"
            :class="[
              col.align === 'right' ? 'orb-btable__th--right' : '',
              col.sortable ? 'orb-btable__th--sortable' : ''
            ]"
            :aria-sort="ariaSortFor(col.id)"
            @click="col.sortable && setSort(col.id)"
          >
            <span class="orb-btable__th-label">
              {{ col.label }}
              <span
                v-if="col.sortable"
                class="orb-btable__sort"
                :class="sortState.col === col.id ? 'orb-btable__sort--active' : ''"
                aria-hidden="true"
              >
                {{ sortState.col === col.id ? (sortState.dir === 'asc' ? '▲' : '▼') : '↕' }}
              </span>
            </span>
          </th>
        </tr>
      </thead>
      <tbody class="orb-btable__body">
        <tr
          v-for="map in sortedMaps"
          :key="map.name"
          class="orb-btable__row"
          :class="selectedMaps.has(map.name) ? 'orb-btable__row--selected' : ''"
        >
          <td v-if="auth.canCreateMaps" class="orb-btable__check-cell" @click.stop>
            <CmkCheckbox
              v-if="capabilities.formSpecs"
              :model-value="selectedMaps.has(map.name)"
              @update:model-value="$emit('toggle-select', map.name)"
            />
            <input
              v-else
              type="checkbox"
              :checked="selectedMaps.has(map.name)"
              @change="$emit('toggle-select', map.name)"
            />
          </td>
          <td class="orb-btable__cell">
            <div class="orb-btable__name-wrap">
              <router-link
                :to="`/maps/${map.name}`"
                class="orb-btable__link"
                :title="map.alias || map.name"
              >
                {{ map.alias || map.name }}
              </router-link>
              <!-- Map-management flags inline with the name (admin-only);
                                 a dedicated mostly-empty column isn't worth it. -->
              <template v-if="auth.isAdmin">
                <span
                  v-if="map.show_in_lists === false"
                  class="orb-btable__flag-badge"
                  :title="_t('Hidden from regular users')"
                >
                  {{ _t('hidden') }}
                </span>
                <span
                  v-if="map.readonly"
                  class="orb-btable__flag-badge"
                  :title="_t('Demo map — cannot be edited')"
                >
                  {{ _t('read-only') }}
                </span>
                <span
                  v-if="map.rotation_interval > 0"
                  class="orb-btable__rotation-badge"
                  :title="_t('Rotates every %{n} seconds', { n: map.rotation_interval })"
                >
                  ↻ {{ map.rotation_interval }}s
                </span>
              </template>
            </div>
          </td>
          <td class="orb-btable__cell">
            <span class="orb-btable__type-badge" :class="typeBadgeClass(map.view.type)">
              {{ mapTypeLabel(map.view.type) }}
            </span>
          </td>
          <td v-if="auth.isAdmin" class="orb-btable__cell">
            <div class="orb-btable__conn">
              <svg
                class="orb-btable__conn-icon"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M5.25 14.25h13.5m-13.5 0a3 3 0 01-3-3m3 3a3 3 0 100 6h13.5a3 3 0 100-6m-16.5-3a3 3 0 013-3h13.5a3 3 0 013 3m-19.5 0a4.5 4.5 0 01.9-2.7L5.737 5.1a3.375 3.375 0 012.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 01.9 2.7m0 0a3 3 0 01-3 3"
                />
              </svg>
              <span class="orb-btable__conn-id" :title="map.connection_id">
                {{ connectionsStore.labelFor(map.connection_id) }}
              </span>
            </div>
          </td>
          <td class="orb-btable__objects-cell">
            <span v-if="isDynamic(map)" class="orb-btable__dynamic">
              {{ _t('dynamic') }}
            </span>
            <span v-else>{{ map.object_count }}</span>
          </td>
          <td v-if="auth.isAdmin || anyEditable" class="orb-btable__actions-cell" @click.stop>
            <div class="orb-btable__actions">
              <button
                v-if="(auth.isAdmin || map.can_edit) && !map.readonly"
                class="orb-btable__action orb-btable__action--settings"
                :title="_t('Map Settings')"
                @click="$emit('open-settings', map)"
              >
                <svg
                  class="orb-btable__action-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                  />
                </svg>
              </button>
              <button
                v-if="auth.canCreateMaps"
                class="orb-btable__action orb-btable__action--clone"
                :title="_t('Clone map')"
                @click="$emit('clone', map)"
              >
                <svg
                  class="orb-btable__action-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
                  />
                </svg>
              </button>
              <button
                v-if="auth.canCreateMaps"
                class="orb-btable__action orb-btable__action--export"
                :title="_t('Export map as JSON')"
                @click="$emit('export', map.name)"
              >
                <svg
                  class="orb-btable__action-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3"
                  />
                </svg>
              </button>
              <button
                v-if="auth.canCreateMaps"
                class="orb-btable__action orb-btable__action--delete"
                :title="deleteMapTitle(map)"
                @click="$emit('delete', map)"
              >
                <svg
                  class="orb-btable__action-icon"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
                  />
                </svg>
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="maps.length === 0">
          <td
            :colspan="visibleColumns.length + (auth.canCreateMaps ? 1 : 0)"
            class="orb-btable__empty"
          >
            {{ _t('No maps match "%{q}"', { q: searchQuery }) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import CmkCheckbox from '@/components/cmk/user-input/CmkCheckbox'

import { useAuthStore } from '@/stores/auth'
import { useCapabilitiesStore } from '@/stores/capabilities'
import { useConnectionsStore } from '@/stores/connections'
import type { MapRead } from '@/types/api'
import usei18n from '@cmk/lib/i18n'

const props = defineProps<{
  maps: MapRead[]
  selectedMaps: Set<string>
  searchQuery: string
  allSelected: boolean
}>()

defineEmits<{
  (e: 'toggle-select', name: string): void
  (e: 'toggle-select-all', checked: boolean): void
  (e: 'open-settings', map: MapRead): void
  (e: 'clone', map: MapRead): void
  (e: 'export', name: string): void
  (e: 'delete', map: MapRead): void
}>()

const { _t } = usei18n()
const auth = useAuthStore()
const capabilities = useCapabilitiesStore()

// Show the connection's display name ("cmk ZWEIFUENF") like the create dialog
// does, not the raw id — falls back to the id until the list is loaded.
const connectionsStore = useConnectionsStore()
if (auth.isAdmin) void connectionsStore.ensureConnections()

type SortCol = 'name' | 'type' | 'connection' | 'objects'

const columns = computed<
  ReadonlyArray<{
    id: SortCol | 'actions'
    label: string
    sortable: boolean
    align?: 'right'
  }>
>(() => [
  { id: 'name', label: _t('Name'), sortable: true },
  { id: 'type', label: _t('Type'), sortable: true },
  { id: 'connection', label: _t('Connection'), sortable: true },
  { id: 'objects', label: _t('Objects'), sortable: true, align: 'right' },
  { id: 'actions', label: _t('Actions'), sortable: false, align: 'right' }
])

// A non-admin may still hold edit rights on individual maps; show the actions
// column for them when at least one listed map is editable.
const anyEditable = computed(() => props.maps.some((b) => b.can_edit === true))

// Connection is admin-oriented; non-admins get a plain read-only list, plus
// the actions column only when they can edit some map.
const visibleColumns = computed(() => {
  if (auth.isAdmin) return columns.value
  const hidden = anyEditable.value ? ['connection'] : ['connection', 'actions']
  return columns.value.filter((c) => !hidden.includes(c.id))
})

const sortState = ref<{ col: SortCol | null; dir: 'asc' | 'desc' }>({
  col: null,
  dir: 'asc'
})

function setSort(col: SortCol | 'actions') {
  if (col === 'actions') return
  if (sortState.value.col === col) {
    sortState.value.dir = sortState.value.dir === 'asc' ? 'desc' : 'asc'
  } else {
    sortState.value.col = col
    sortState.value.dir = 'asc'
  }
}

function ariaSortFor(col: SortCol | 'actions'): 'ascending' | 'descending' | 'none' {
  if (sortState.value.col !== col) return 'none'
  return sortState.value.dir === 'asc' ? 'ascending' : 'descending'
}

function isDynamic(map: MapRead): boolean {
  return Boolean(map.readonly) || ['flow', 'radar', 'worldmap'].includes(map.view.type)
}

function deleteMapTitle(map: MapRead): string {
  return _t('Delete map "%{name}"?', { name: map.alias || map.name })
}

function sortKey(map: MapRead, col: SortCol): string | number {
  switch (col) {
    case 'name':
      return (map.alias || map.name).toLowerCase()
    case 'type':
      return map.view.type
    case 'connection':
      return (map.connection_id || '').toLowerCase()
    case 'objects':
      return isDynamic(map) ? Number.MAX_SAFE_INTEGER : map.object_count
  }
}

const sortedMaps = computed(() => {
  const list = props.maps
  const col = sortState.value.col
  if (!col) return list
  const dir = sortState.value.dir === 'asc' ? 1 : -1
  return [...list].sort((a, b) => {
    const av = sortKey(a, col)
    const bv = sortKey(b, col)
    if (av < bv) return -1 * dir
    if (av > bv) return 1 * dir
    return 0
  })
})

const TYPE_LABELS: Record<string, string> = {
  static: 'Static',
  worldmap: 'Geo Map',
  flow: 'Flow Map',
  radar: 'Radar',
  foldertree: 'Folder Tree',
  presentation: 'Presentation'
}
function mapTypeLabel(type: string) {
  return TYPE_LABELS[type] ?? type
}

function typeBadgeClass(type: string): string {
  switch (type) {
    case 'worldmap':
      return 'orb-btable__type-badge--worldmap'
    case 'radar':
      return 'orb-btable__type-badge--radar'
    case 'flow':
      return 'orb-btable__type-badge--flow'
    case 'static':
      return 'orb-btable__type-badge--static'
    case 'foldertree':
      return 'orb-btable__type-badge--foldertree'
    case 'presentation':
      return 'orb-btable__type-badge--presentation'
    default:
      return 'orb-btable__type-badge--generic'
  }
}
</script>

<style scoped>
.orb-btable {
  overflow: hidden;
  max-width: 1100px;
  margin: 0 auto;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 0 0 1px var(--border);
}

.orb-btable__table {
  width: 100%;
  font-size: var(--font-size-large);
  line-height: 20px;
  border-collapse: separate;
  border-spacing: 0;
}

.orb-btable__head-row {
  border-bottom: 1px solid var(--border);
}

.orb-btable__check-col {
  width: 28px;
  padding: 6px 8px 6px 12px;
  text-align: left;
}

.orb-btable__th {
  padding: 6px 12px;
  font-size: var(--font-size-large);
  line-height: 20px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  text-align: left;
  user-select: none;
}

.orb-btable__th--right {
  text-align: right;
}

.orb-btable__th--sortable {
  cursor: pointer;
}

.orb-btable__th--sortable:hover {
  color: var(--text);
}

.orb-btable__th-label {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-3);
}

.orb-btable__sort {
  font-size: 10px;
  color: color-mix(in srgb, var(--text-muted) 40%, transparent);
}

.orb-btable__sort--active {
  color: var(--color-corporate-green-50);
}

.orb-btable__body tr + tr {
  border-top: 1px solid var(--border);
}

.orb-btable__row {
  transition: background-color 0.15s;
}

.orb-btable__row--selected {
  background: color-mix(in srgb, var(--color-corporate-green-50) 8%, transparent);
}

.orb-btable__row:hover {
  background: var(--bg-hover);
}

.orb-btable__check-cell {
  padding: 6px 8px 6px 12px;
  vertical-align: middle;
}

.orb-btable__cell {
  padding: 6px 12px;
  vertical-align: middle;
}

.orb-btable__name-wrap {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.orb-btable__link {
  font-weight: 600;
  color: var(--text);
  transition: color 0.15s;
}

.orb-btable__link:hover {
  color: var(--color-corporate-green-50);
}

.orb-btable__flag-badge {
  padding: var(--dimension-2) 5px;
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  background: var(--bg-surface);
  border-radius: 6px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--default-border-color) 60%, transparent);
}

.orb-btable__rotation-badge {
  padding: var(--dimension-2) 6px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 20%, transparent);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-warning) 30%, transparent);
}

.orb-btable__type-badge {
  padding: var(--dimension-2) 6px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 6px;
}

.orb-btable__type-badge--worldmap {
  color: var(--color-cyan-80);
  background: color-mix(in srgb, var(--color-cyan-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-cyan-60) 40%, transparent);
}

.dark .orb-btable__type-badge--worldmap {
  color: var(--color-cyan-30);
  background: color-mix(in srgb, var(--color-cyan-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-cyan-50) 30%, transparent);
}

.orb-btable__type-badge--radar {
  color: var(--color-purple-80);
  background: color-mix(in srgb, var(--color-purple-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-purple-60) 40%, transparent);
}

.dark .orb-btable__type-badge--radar {
  color: var(--color-purple-30);
  background: color-mix(in srgb, var(--color-purple-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-purple-50) 30%, transparent);
}

.orb-btable__type-badge--flow {
  color: var(--color-corporate-green-80);
  background: color-mix(in srgb, var(--color-corporate-green-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-70) 40%, transparent);
}

.dark .orb-btable__type-badge--flow {
  color: var(--color-corporate-green-30);
  background: color-mix(in srgb, var(--color-corporate-green-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-corporate-green-50) 30%, transparent);
}

.orb-btable__type-badge--static {
  color: var(--color-mid-grey-70);
  background: color-mix(in srgb, var(--color-mid-grey-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-mid-grey-50) 40%, transparent);
}

.dark .orb-btable__type-badge--static {
  color: var(--color-mid-grey-30);
  background: color-mix(in srgb, var(--color-mid-grey-40) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-mid-grey-40) 30%, transparent);
}

.orb-btable__type-badge--foldertree {
  color: var(--color-yellow-80);
  background: color-mix(in srgb, var(--color-yellow-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-yellow-60) 40%, transparent);
}

.dark .orb-btable__type-badge--foldertree {
  color: var(--color-yellow-30);
  background: color-mix(in srgb, var(--color-yellow-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-yellow-50) 30%, transparent);
}

.orb-btable__type-badge--presentation {
  color: var(--color-pink-80);
  background: color-mix(in srgb, var(--color-pink-50) 15%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-pink-60) 40%, transparent);
}

.dark .orb-btable__type-badge--presentation {
  color: var(--color-pink-30);
  background: color-mix(in srgb, var(--color-pink-50) 20%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-pink-50) 30%, transparent);
}

.orb-btable__type-badge--generic {
  color: var(--text);
  background: var(--bg-surface);
  box-shadow: 0 0 0 1px var(--default-border-color);
}

.orb-btable__conn {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.orb-btable__conn-icon {
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  color: var(--text-muted);
}

.orb-btable__conn-id {
  overflow: hidden;
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  color: var(--text-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.orb-btable__objects-cell {
  padding: 6px 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
  text-align: right;
  vertical-align: middle;
}

.orb-btable__dynamic {
  font-style: italic;
}

.orb-btable__actions-cell {
  padding: 6px 12px;
  text-align: right;
  vertical-align: middle;
}

.orb-btable__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--dimension-2);
}

.orb-btable__action {
  padding: var(--dimension-3);
  color: var(--text-muted);
  border-radius: 4px;
  transition: all 0.15s;
}

.orb-btable__action--settings:hover {
  color: var(--color-corporate-green-50);
  background: color-mix(in srgb, var(--color-corporate-green-50) 10%, transparent);
}

.orb-btable__action--clone:hover {
  color: var(--color-yellow-50);
  background: color-mix(in srgb, var(--color-warning) 10%, transparent);
}

.orb-btable__action--export:hover {
  color: var(--text);
  background: var(--color-white-0);
}

.orb-btable__action--delete:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 10%, transparent);
}

.orb-btable__action-icon {
  width: 14px;
  height: 14px;
}

.orb-btable__empty {
  padding: 40px 0;
  color: var(--text-muted);
  text-align: center;
}
</style>
