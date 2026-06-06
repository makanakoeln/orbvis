<template>
  <div class="ft-board">
    <!-- Reserved top toolbar (not a floating overlay): the treemap fills 100%
             of the stage and the list is a full-width scroller, so floating
             controls would always cover data. Summary left, tools right. -->
    <div v-if="!preview && !kiosk" class="ft-toolbar">
      <span v-if="root" class="ft-summary">
        <span
          >{{ filterActive ? _t('showing') + ' ' : '' }}{{ summary.hosts }} {{ _t('hosts') }}</span
        >
        <span v-if="summaryPills.length && summaryOk > 0" class="ft-summary-ok"
          >· {{ summaryOk }} OK</span
        >
        <template v-if="summaryPills.length">
          <span
            v-for="p in summaryPills"
            :key="p.state"
            class="ft-summary-pill"
            :style="{ background: p.bg, color: p.fg }"
            >{{ p.count }} {{ p.state }}</span
          >
        </template>
        <span v-else class="ft-summary-ok">· {{ _t('all OK') }}</span>
        <span v-if="searchTruncated" class="ft-summary-trunc">{{
          _t('more matches exist — refine your search')
        }}</span>
      </span>
      <span class="ft-spacer" />
      <BoardSearch
        v-model="filterText"
        inline
        :placeholder="_t('Search folders, hosts, services…')"
        :exclude-prefixes="['hg', 'sg', 'id']"
      >
        <template #trailing>
          <ProblemsOnlyToggle
            v-model="problemsOnly"
            :title="_t('Show only folders/hosts with problems')"
          />
        </template>
      </BoardSearch>
      <button type="button" class="ft-tool" @click="activeExpandAll">
        {{ _t('Expand all') }}
      </button>
      <button type="button" class="ft-tool" @click="activeCollapseAll">
        {{ _t('Collapse all') }}
      </button>
      <div class="ft-segment" role="tablist">
        <button
          type="button"
          class="ft-seg"
          :class="{ 'ft-seg--active': mode === 'map' }"
          role="tab"
          :aria-selected="mode === 'map'"
          @click="setMode('map')"
        >
          {{ _t('Map') }}
        </button>
        <button
          type="button"
          class="ft-seg"
          :class="{ 'ft-seg--active': mode === 'list' }"
          role="tab"
          :aria-selected="mode === 'list'"
          @click="setMode('list')"
        >
          {{ _t('List') }}
        </button>
      </div>
    </div>

    <!-- Stale-data warning as an in-flow row (was a floating banner that
             covered tiles): the tree froze on its last known state. -->
    <div v-if="!preview && root && !states.connected" class="ft-stale-row" role="status">
      {{ _t('Connection lost — showing last known state') }}
    </div>

    <div v-if="!root" class="ft-placeholder">{{ _t('Waiting for folder data…') }}</div>
    <div v-else-if="!root.children.length" class="ft-placeholder">
      {{
        _t(
          'No folders to show. The selected connection has no SETUP folders, or your filters hide them.'
        )
      }}
    </div>
    <div v-else-if="filterEmpty" class="ft-placeholder ft-placeholder--filter">
      <span>{{
        problemsOnly && parsedQuery.length === 0
          ? _t('No problems — everything is OK.')
          : _t('No matches for the current filter.')
      }}</span>
      <button type="button" class="ft-tool" @click="clearFilters">
        {{ _t('Clear filter') }}
      </button>
    </div>
    <FolderTreeMap
      v-else-if="mode === 'map'"
      ref="mapRef"
      :query="parsedQuery"
      :problems-only="problemsOnly"
      :problems-severity="problemsSeverity"
      :show-services="showServices"
      :services-by-host="effectiveServices"
      :service-loading="serviceLoading"
      :service-error="serviceError"
      @expand-host="ensureServices"
      @select-host="$emit('select-host', $event)"
      @select-service="(h, n) => $emit('select-service', h, n)"
      @ctx-folder="(n, x, y) => $emit('ctx-folder', n, x, y)"
    />
    <!-- Virtualized list: the tree is flattened to ``flatRows`` and only the
             rows intersecting the viewport (+ overscan) are in the DOM, so the
             list scales to 100k+ hosts. Fixed 28px row height → trivial windowing
             (no dependency). A spacer of the full height drives the scrollbar; the
             rendered window is offset into place. -->
    <div
      v-else
      ref="scrollEl"
      class="ft-tree"
      role="tree"
      :style="{ '--ft-row-h': ROW_H + 'px' }"
      @scroll="onListScroll"
    >
      <div class="ft-vlist" :style="{ height: totalHeight + 'px' }">
        <div class="ft-vwindow" :style="{ transform: `translateY(${offsetY}px)` }">
          <template v-for="row in windowRows" :key="row.key">
            <div
              v-if="row.note"
              class="ft-note"
              :class="{ 'ft-note--err': row.note === 'error' }"
              :style="{ paddingLeft: row.depth * 18 + 16 + 'px' }"
            >
              {{ noteLabel(row) }}
            </div>
            <FolderTreeRow
              v-else
              :node="row.node"
              :rev="states.folderTreeVersion"
              :depth="row.depth"
              :is-open="row.isOpen"
              :is-expandable="row.isExpandable"
              :multi-site="multiSite"
              v-bind="rowHostNameProps(row)"
              @toggle="toggle"
              @expand-host="ensureServices"
              @select-host="$emit('select-host', $event)"
              @select-service="(h, n) => $emit('select-service', h, n)"
              @hover-host="(n, x, y) => $emit('hover-host', n, x, y)"
              @hover-service="(h, n, x, y) => $emit('hover-service', h, n, x, y)"
              @hover-clear="$emit('hover-clear')"
              @ctx-folder="(n, x, y) => $emit('ctx-folder', n, x, y)"
            />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, reactive, ref, useTemplateRef, watch } from 'vue'

import BoardSearch from '@/components/board/BoardSearch.vue'
import FolderTreeMap from '@/components/board/FolderTreeMap.vue'
import FolderTreeRow from '@/components/board/FolderTreeRow.vue'
import ProblemsOnlyToggle from '@/components/board/ProblemsOnlyToggle.vue'

import { boardsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import { useStatesStore } from '@/stores/states'
import type { FolderHostService, FolderTreeNode, FolderTreeView } from '@/types/api'
import {
  type ProblemSeverity,
  isFilterActive,
  isProblemState,
  parseFolderQuery,
  selfMatches,
  subtreeVisible,
  visibleServices
} from '@/utils/folderTreeFilter'
import { severityPills } from '@/utils/stateColors'
import usei18n from '@/vendor/cmk/lib/i18n'
import { useDebounceFn } from '@/vendor/cmk/lib/useDebounce'

const props = defineProps<{
  view: FolderTreeView
  preview?: boolean
  kiosk?: boolean
  boardName?: string
}>()
defineEmits<{
  'select-host': [FolderTreeNode]
  'select-service': [string, FolderTreeNode]
  'hover-host': [FolderTreeNode, number, number]
  'hover-service': [string, FolderTreeNode, number, number]
  'hover-clear': []
  'ctx-folder': [FolderTreeNode, number, number]
}>()

const { _t } = usei18n()
const auth = useAuthStore()
const boards = useBoardsStore()
const states = useStatesStore()
const root = computed<FolderTreeNode | null>(() => states.folderTree)

// A kiosk/wall display forces the map: the scrolling list can't be an ambient
// "always shows status" surface.
const mode = ref<'map' | 'list'>(props.kiosk ? 'map' : (props.view.default_view ?? 'map'))
const expanded = reactive(new Set<string>())
const problemsOnly = ref(props.view.problems_only ?? false)
const problemsSeverity = computed<ProblemSeverity>(() => props.view.problems_severity ?? 'any')
const showServices = computed(() => props.view.show_services ?? false)

const filterText = ref('')
const parsedQuery = computed(() => parseFolderQuery(filterText.value))
const filterActive = computed(() => isFilterActive(parsedQuery.value, problemsOnly.value))

// Service leaves injected by the server-side service search (keyed by host).
// Hosts surfaced purely by a service match (their own name may not match) drive
// tree visibility so a `s:` query reveals the host to drill into. Populated by
// runServiceSearch() below; the search snapshot is kept live on each SSE tick.
const searchServices = reactive<Record<string, FolderTreeNode[]>>({})
const searchTruncated = ref(false)
const searchPending = ref(false)
const matchedHosts = computed(() => new Set(Object.keys(searchServices)))
// The query carries a service/bare term (so it's answered by the server search)
// — used to suppress the "no matches" state while the term is still too short or
// a request is in flight, so the tree doesn't flash empty mid-typing.
const hasServiceOrBareTerm = computed(() =>
  parsedQuery.value.some((t) => t.field === 'service' || t.field === 'any')
)
// Terms ≥2 chars (shorter is too broad); the backend re-applies the same floor.
const serviceSearchTerms = computed(() => {
  const long = (t: string) => t.length >= 2
  const of = (field: string) =>
    parsedQuery.value
      .filter((t) => t.field === field)
      .map((t) => t.needle)
      .filter(long)
  return { s: of('service'), h: of('host'), q: of('any') }
})
const hasServiceSearch = computed(
  () => serviceSearchTerms.value.s.length > 0 || serviceSearchTerms.value.q.length > 0
)

// Count hosts (and their problem-state breakdown) that survive the active
// filter, so the summary reflects what's actually shown — not the whole tree.
function visibleHostStats(
  node: FolderTreeNode,
  ancestorMatched: boolean
): { hosts: number; counts: Record<string, number> } {
  const selfMatch = ancestorMatched || selfMatches(node, parsedQuery.value)
  if (node.kind === 'service') return { hosts: 0, counts: {} }
  if (node.kind === 'host') {
    if (
      !subtreeVisible(
        node,
        parsedQuery.value,
        problemsOnly.value,
        ancestorMatched,
        matchedHosts.value,
        problemsSeverity.value
      )
    ) {
      return { hosts: 0, counts: {} }
    }
    return {
      hosts: 1,
      counts: isProblemState(node.state) ? { [node.state]: 1 } : {}
    }
  }
  const counts: Record<string, number> = {}
  let hosts = 0
  for (const c of node.children) {
    const s = visibleHostStats(c, selfMatch)
    hosts += s.hosts
    for (const [k, v] of Object.entries(s.counts)) counts[k] = (counts[k] ?? 0) + v
  }
  return { hosts, counts }
}

const summary = computed(() => {
  void states.folderTreeVersion // re-derive on in-place tree patches
  const r = root.value
  if (!r) return { hosts: 0, counts: {} as Record<string, number> }
  if (!filterActive.value) return { hosts: r.host_count, counts: r.severity_counts }
  return visibleHostStats(r, false)
})
const summaryPills = computed(() => severityPills(summary.value.counts))
// Healthy remainder so the pill breakdown sums to the host count.
const summaryOk = computed(() =>
  Math.max(0, summary.value.hosts - Object.values(summary.value.counts).reduce((a, b) => a + b, 0))
)
// The server service search hasn't settled: a request is in flight, or the term
// is still too short to fire. While unsettled the previous matches stay and the
// "no matches" state is held back, so the tree doesn't flash empty mid-typing.
const searchUnsettled = computed(
  () => hasServiceOrBareTerm.value && (searchPending.value || !hasServiceSearch.value)
)
// A filter is active but nothing matches → distinct empty state with a reset.
const filterEmpty = computed(
  () => !!root.value && filterActive.value && summary.value.hosts === 0 && !searchUnsettled.value
)

function clearFilters() {
  filterText.value = ''
  problemsOnly.value = false
}

const mapRef = useTemplateRef<InstanceType<typeof FolderTreeMap>>('mapRef')

// Persist a view-preference patch (view mode / "Problems only") so the board
// reopens the same way (mirrors the Flow board's services-layout control),
// best-effort and never in preview. The server's response — new version and
// merged view — is folded back into the shared board: otherwise each such write
// silently bumps the board version on disk while the client keeps the stale one,
// so the next Settings save 409s ("changed elsewhere"), and the next preference
// write re-sends an outdated `view` that reverts the field we just changed.
function persistView(patch: Partial<FolderTreeView>) {
  if (props.preview || !props.boardName || !auth.accessToken) return
  void boardsApi
    .update(props.boardName, { view: { ...props.view, ...patch } }, auth.accessToken)
    .then((updated) => {
      const cur = boards.currentBoard
      if (cur && cur.name === updated.name) {
        if (updated.version !== undefined) cur.version = updated.version
        cur.view = updated.view
      }
    })
    .catch(() => {})
}

function setMode(m: 'map' | 'list') {
  if (mode.value === m) return
  mode.value = m
  persistView({ default_view: m })
}

watch(problemsOnly, (po) => {
  if (po === (props.view.problems_only ?? false)) return
  persistView({ problems_only: po })
})

function activeExpandAll() {
  if (mode.value === 'map') mapRef.value?.expandAll()
  else expandAll()
}
function activeCollapseAll() {
  if (mode.value === 'map') mapRef.value?.collapseAll()
  else collapseAll()
}

// Lazily-fetched services keyed by host name. The backend never pushes services
// over SSE (would not scale to 4M-host sites); they're fetched per-host only
// when the operator expands that host, then cached here for both List and Map.
const servicesByHost = reactive<Record<string, FolderTreeNode[]>>({})
const serviceLoading = reactive(new Set<string>())
const serviceError = reactive(new Set<string>())
// Path + site of every host whose services we've fetched, so we can re-fetch
// them in place on each live refresh (the leaves live outside the SSE tree).
const loadedHosts = reactive<Record<string, { path: string; siteId: string | null }>>({})

// Build a service-leaf tree node from a fetched/searched service. Shared by the
// lazy per-host fetch and the server search so both inject identical leaves.
function toServiceNode(
  s: FolderHostService,
  pathPrefix: string,
  siteId: string | null
): FolderTreeNode {
  return {
    path: `${pathPrefix}/${s.name}`,
    title: s.name,
    kind: 'service',
    state: s.state,
    is_empty: false,
    folder_id: '',
    host_count: 0,
    problem_count: 0,
    severity_counts: {},
    output: s.output,
    acknowledged: s.acknowledged,
    in_downtime: s.in_downtime,
    is_flapping: s.is_flapping,
    last_state_change: s.last_state_change,
    site_id: siteId,
    children: []
  }
}

async function fetchServices(name: string, hostPath: string, siteId: string | null) {
  if (!props.boardName || !auth.accessToken) return
  const svcs = await boardsApi.folderHostServices(props.boardName, name, auth.accessToken)
  servicesByHost[name] = svcs.map((s) => toServiceNode(s, hostPath, siteId))
}

async function ensureServices(host: FolderTreeNode) {
  const name = host.title
  if (!showServices.value || !props.boardName || !auth.accessToken) return
  if (servicesByHost[name] || serviceLoading.has(name)) return
  loadedHosts[name] = { path: host.path, siteId: host.site_id }
  serviceLoading.add(name)
  serviceError.delete(name)
  try {
    await fetchServices(name, host.path, host.site_id)
  } catch {
    serviceError.add(name)
  } finally {
    serviceLoading.delete(name)
  }
}

function clearSearchServices() {
  for (const k of Object.keys(searchServices)) delete searchServices[k]
  searchTruncated.value = false
}

// Monotonic token to discard out-of-order responses: typing + the periodic SSE
// re-run fire independent requests, so without this a slow earlier response
// could overwrite a newer query's results (matchedHosts then disagrees with the
// query box). Only the latest request is allowed to mutate state.
let searchSeq = 0

async function runServiceSearch() {
  if (props.preview || !props.boardName || !auth.accessToken || !hasServiceSearch.value) {
    clearSearchServices()
    searchPending.value = false
    return
  }
  const seq = ++searchSeq
  searchPending.value = true
  try {
    const res = await boardsApi.folderSearch(
      props.boardName,
      serviceSearchTerms.value,
      auth.accessToken
    )
    if (seq !== searchSeq) return // a newer search superseded this one
    const seen = new Set<string>()
    for (const m of res.matches) {
      seen.add(m.host)
      searchServices[m.host] = m.services.map((s) => toServiceNode(s, m.host, m.site_id))
    }
    for (const k of Object.keys(searchServices)) if (!seen.has(k)) delete searchServices[k]
    searchTruncated.value = res.truncated
  } catch {
    if (seq === searchSeq) clearSearchServices()
  } finally {
    if (seq === searchSeq) searchPending.value = false
  }
}

const runServiceSearchDebounced = useDebounceFn(runServiceSearch, 250)
// Mark pending the moment a service-bearing query changes (before the debounce
// fires) so the empty-state stays suppressed during the wait, not just during
// the request.
watch(serviceSearchTerms, () => {
  if (hasServiceSearch.value) searchPending.value = true
  void runServiceSearchDebounced()
})

// One service-leaf source for Map + List: a manually expanded host (full lazy
// list) overrides the search snapshot for that host.
const effectiveServices = computed<Record<string, FolderTreeNode[]>>(() => ({
  ...searchServices,
  ...servicesByHost
}))

// Keep lazily-loaded service leaves live: re-fetch the services of every host
// the operator has drilled into whenever the board's state refreshes, so leaf
// state / acknowledged / downtime stay current (a downtime set after expansion
// would otherwise never appear). Bounded by what the operator actually expanded.
// An active service search is re-run on the same tick so its (un-expanded) hits
// stay live too — one Livestatus query, independent of match count.
let lastSvcRefresh = 0
watch(
  () => states.folderTreeVersion,
  () => {
    const now = Date.now()
    if (now - lastSvcRefresh < 4000) return
    lastSvcRefresh = now
    for (const [name, meta] of Object.entries(loadedHosts)) {
      void fetchServices(name, meta.path, meta.siteId).catch(() => {})
    }
    if (hasServiceSearch.value) void runServiceSearch()
  }
)

function collectFolders(node: FolderTreeNode, acc: FolderTreeNode[] = []): FolderTreeNode[] {
  if (node.kind === 'folder') {
    acc.push(node)
    node.children.forEach((c) => collectFolders(c, acc))
  }
  return acc
}

function seed(node: FolderTreeNode, depth: number, maxDepth: number) {
  if (node.kind !== 'folder') return
  if (depth < maxDepth) expanded.add(node.path)
  node.children.forEach((c) => seed(c, depth + 1, maxDepth))
}

// Main (root) is always open; its subfolders start collapsed and only
// pre-expand when default_expand_depth > 1 (so the default view is the
// top-level overview — drill on demand, like the map).
function reseedExpansion(r: FolderTreeNode) {
  expanded.clear()
  expanded.add(r.path)
  r.children.forEach((c) => seed(c, 1, props.view.default_expand_depth ?? 1))
}

// (Re)seed the expand state whenever the tree identity changes — but keep the
// operator's manual expand/collapse across live state refreshes (same root).
let seededFor = ''
watch(
  root,
  (r) => {
    if (!r) return
    const sig = r.path + '|' + r.children.length
    if (sig === seededFor) return
    seededFor = sig
    reseedExpansion(r)
  },
  { immediate: true }
)

// The Settings preview patches props.view in place; mirror it into local state.
// No-op-guarded so syncing in never re-triggers the persistView watchers above.
watch(
  () => props.view.problems_only,
  (v) => {
    const next = v ?? false
    if (problemsOnly.value !== next) problemsOnly.value = next
  }
)
watch(
  () => props.view.default_view,
  (v) => {
    if (!props.kiosk && v && mode.value !== v) mode.value = v
  }
)
watch(
  () => props.view.default_expand_depth,
  () => {
    if (root.value) reseedExpansion(root.value)
  }
)

// List renders the real root node ("Main") as the top row so the hierarchy
// mirrors Checkmk's SETUP tree (root-level hosts sit under Main, not floating).
// Standalone backends have no root .wato → fall back to "Main".
const rootDisplay = computed<FolderTreeNode | null>(() => {
  const r = root.value
  if (!r) return null
  return r.title ? r : { ...r, title: 'Main' }
})

const multiSite = computed(() => {
  if (!root.value) return false
  const sites = new Set<string>()
  const walk = (n: FolderTreeNode) => {
    if (n.kind === 'host' && n.site_id) sites.add(n.site_id)
    n.children.forEach(walk)
  }
  walk(root.value)
  return sites.size > 1
})

function toggle(path: string) {
  if (expanded.has(path)) expanded.delete(path)
  else expanded.add(path)
}

function expandAll() {
  if (!root.value) return
  collectFolders(root.value).forEach((f) => expanded.add(f.path))
}

function collapseAll() {
  if (!root.value) return
  expanded.clear()
  expanded.add(root.value.path)
}

// One flattened, virtualized row. ``note`` rows are the host's loading/error/
// no-services placeholders (the host stays the parent for depth/key).
interface FlatRow {
  key: string
  node: FolderTreeNode
  depth: number
  isOpen: boolean
  isExpandable: boolean
  hostName?: string | undefined
  note?: 'loading' | 'error' | 'empty'
}

// FolderTreeRow's `hostName?:` prop rejects an explicit `undefined` under
// exactOptionalPropertyTypes — spread the prop in only when a value exists.
function rowHostNameProps(row: FlatRow): { hostName?: string } {
  return row.hostName !== undefined ? { hostName: row.hostName } : {}
}

// A folder's visible children under the active filter (the matched-hosts set is
// passed so the list matches the summary count for s:-searches).
function rowChildren(node: FolderTreeNode, childAncestorMatched: boolean): FolderTreeNode[] {
  if (!filterActive.value) return node.children
  return node.children.filter((c) =>
    subtreeVisible(
      c,
      parsedQuery.value,
      problemsOnly.value,
      childAncestorMatched,
      matchedHosts.value,
      problemsSeverity.value
    )
  )
}

// A host's visible (lazily-loaded) service leaves under the active filter.
function rowServices(host: FolderTreeNode, hostMatched: boolean): FolderTreeNode[] {
  return visibleServices(
    host.title,
    effectiveServices.value[host.title] ?? [],
    parsedQuery.value,
    problemsOnly.value,
    hostMatched,
    problemsSeverity.value
  )
}

// Project the visible (expanded + filtered) tree into a flat row list. Open and
// expandable state is resolved here so the row component stays presentational;
// the order mirrors the old recursive render exactly (folder's own rows, then
// subfolders). A text search auto-opens every folder on the path to a match.
const flatRows = computed<FlatRow[]>(() => {
  const out: FlatRow[] = []
  const rd = rootDisplay.value
  if (!rd) return out
  const q = parsedQuery.value
  const searchActive = q.length > 0
  const expandableOf = (n: FolderTreeNode) =>
    n.kind === 'folder' || (n.kind === 'host' && showServices.value) || n.children.length > 0

  const walk = (
    node: FolderTreeNode,
    depth: number,
    ancestorMatched: boolean,
    hostName?: string
  ): void => {
    const selfMatch = ancestorMatched || selfMatches(node, q)
    let isOpen = false
    if (expanded.has(node.path)) isOpen = true
    else if (!searchActive) isOpen = false
    else if (node.kind === 'folder') isOpen = true
    else if (node.kind === 'host')
      isOpen =
        showServices.value && !selfMatches(node, q) && rowServices(node, selfMatch).length > 0

    out.push({
      key: node.path + ':' + node.kind + ':' + node.title,
      node,
      depth,
      isOpen,
      isExpandable: expandableOf(node),
      hostName
    })
    if (!isOpen) return

    if (node.kind === 'host') {
      const note = (n: 'loading' | 'error' | 'empty'): void => {
        out.push({
          key: `${node.path}:${n}`,
          node,
          depth: depth + 1,
          isOpen: false,
          isExpandable: false,
          note: n
        })
      }
      if (serviceLoading.has(node.title)) return note('loading')
      if (serviceError.has(node.title)) return note('error')
      const svcs = rowServices(node, selfMatch)
      if (!svcs.length) return note('empty')
      for (const s of svcs) walk(s, depth + 1, selfMatch, node.title)
    } else {
      for (const c of rowChildren(node, selfMatch)) walk(c, depth + 1, selfMatch)
    }
  }

  walk(rd, 0, false)
  return out
})

function noteLabel(row: FlatRow): string {
  if (row.note === 'loading') return _t('Loading services…')
  if (row.note === 'error') return _t('Could not load services')
  return problemsOnly.value ? _t('No problem services') : _t('No services')
}

// Fixed-height windowing: render only the rows intersecting the viewport plus a
// small overscan, offset into place by a full-height spacer.
const ROW_H = 28
const OVERSCAN = 10
const scrollEl = useTemplateRef<HTMLDivElement>('scrollEl')
const scrollTop = ref(0)
const viewportH = ref(0)
const totalHeight = computed(() => flatRows.value.length * ROW_H)
// Clamp to the list length so a shrink (collapse-all / filter) while scrolled
// down can't leave firstIndex past the end → blank window until the browser's
// scroll clamp fires.
const firstIndex = computed(() =>
  Math.max(0, Math.min(Math.floor(scrollTop.value / ROW_H) - OVERSCAN, flatRows.value.length - 1))
)
const lastIndex = computed(() =>
  Math.min(flatRows.value.length, Math.ceil((scrollTop.value + viewportH.value) / ROW_H) + OVERSCAN)
)
const windowRows = computed(() => flatRows.value.slice(firstIndex.value, lastIndex.value))
const offsetY = computed(() => firstIndex.value * ROW_H)

function onListScroll() {
  scrollTop.value = scrollEl.value?.scrollTop ?? 0
}

// Track the viewport height (and reset scroll position) whenever the list
// element appears (mode switch) or resizes.
let listResizeObs: ResizeObserver | null = null
watch(scrollEl, (el) => {
  listResizeObs?.disconnect()
  listResizeObs = null
  if (!el) return
  viewportH.value = el.clientHeight
  scrollTop.value = el.scrollTop
  listResizeObs = new ResizeObserver(() => {
    viewportH.value = el.clientHeight
  })
  listResizeObs.observe(el)
})
onUnmounted(() => listResizeObs?.disconnect())
</script>

<style scoped>
.ft-board {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* Reserved, non-overlapping toolbar — wraps to a second line on narrow boards
   instead of clipping, never covers the view below. */
.ft-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 44px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.ft-spacer {
  flex: 1;
}

.ft-summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

/* In-flow stale-data row (replaces the floating banner that covered tiles). */
.ft-stale-row {
  flex-shrink: 0;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  color: var(--color-yellow-50, #fbbf24);
  background: rgb(251 191 36 / 12%);
  border-bottom: 1px solid var(--color-yellow-50, #fbbf24);
}

.ft-tool {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text);
  cursor: pointer;
}

.ft-tool:hover {
  background: var(--bg-hover);
}

.ft-segment {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.ft-seg {
  font-size: 12px;
  padding: 3px 12px;
  border: none;
  background: var(--bg-surface);
  color: var(--text-muted);
  cursor: pointer;
}

.ft-seg + .ft-seg {
  border-left: 1px solid var(--border);
}

.ft-seg--active {
  background: var(--accent);
  color: white;
}

.ft-summary-pill {
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  padding: 2px 7px;
  border-radius: 9px;
}

.ft-summary-ok {
  color: var(--text-muted);
}

.ft-summary-trunc {
  font-weight: 600;
  color: var(--color-yellow-50, #fbbf24);
}

.ft-tree {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 8px;
}

/* Full-height spacer drives the scrollbar; the rendered window is absolutely
   positioned and translated into view (no vertical padding on .ft-tree so
   scrollTop maps cleanly to row index). */
.ft-vlist {
  position: relative;
}

.ft-vwindow {
  position: absolute;
  inset: 0 0 auto;
}

.ft-note {
  display: flex;
  align-items: center;

  /* Driven by ROW_H (the windowing source of truth); fallback keeps it sane
       if the var is ever missing. */
  height: var(--ft-row-h, 28px);
  font-size: 12px;
  font-style: italic;
  color: var(--text-muted);
}

.ft-note--err {
  color: var(--color-state-critical);
  font-style: normal;
}

.ft-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 24px;
  text-align: center;
}

.ft-placeholder--filter {
  flex-direction: column;
  gap: 12px;
}
</style>
