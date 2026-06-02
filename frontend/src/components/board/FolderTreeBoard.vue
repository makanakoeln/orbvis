<template>
    <div class="ft-board">
        <!-- Reserved top toolbar (not a floating overlay): the treemap fills 100%
             of the stage and the list is a full-width scroller, so floating
             controls would always cover data. Summary left, tools right. -->
        <div v-if="!preview" class="ft-toolbar">
            <span v-if="root" class="ft-summary">
                <span
                    >{{ filterActive ? t('board.ftShowing') + ' ' : '' }}{{ summary.hosts }}
                    {{ t('board.ftHosts') }}</span
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
                <span v-else class="ft-summary-ok">· {{ t('board.ftAllOk') }}</span>
                <span v-if="searchTruncated" class="ft-summary-trunc">{{
                    t('board.ftSearchTruncated')
                }}</span>
            </span>
            <span class="ft-spacer" />
            <BoardSearch
                v-model="filterText"
                inline
                :placeholder="t('board.ftSearchPlaceholder')"
                :exclude-prefixes="['hg', 'sg', 'id']"
            >
                <template #trailing>
                    <ProblemsOnlyToggle v-model="problemsOnly" :title="t('board.ftProblemsOnly')" />
                </template>
            </BoardSearch>
            <button type="button" class="ft-tool" @click="activeExpandAll">
                {{ t('board.ftExpandAll') }}
            </button>
            <button type="button" class="ft-tool" @click="activeCollapseAll">
                {{ t('board.ftCollapseAll') }}
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
                    {{ t('board.ftMap') }}
                </button>
                <button
                    type="button"
                    class="ft-seg"
                    :class="{ 'ft-seg--active': mode === 'list' }"
                    role="tab"
                    :aria-selected="mode === 'list'"
                    @click="setMode('list')"
                >
                    {{ t('board.ftList') }}
                </button>
            </div>
        </div>

        <!-- Stale-data warning as an in-flow row (was a floating banner that
             covered tiles): the tree froze on its last known state. -->
        <div v-if="!preview && root && !states.connected" class="ft-stale-row" role="status">
            {{ t('board.ftConnectionLost') }}
        </div>

        <div v-if="!root" class="ft-placeholder">{{ t('board.ftWaiting') }}</div>
        <div v-else-if="!root.children.length" class="ft-placeholder">
            {{ t('board.ftNoFolders') }}
        </div>
        <div v-else-if="filterEmpty" class="ft-placeholder ft-placeholder--filter">
            <span>{{
                problemsOnly && parsedQuery.length === 0
                    ? t('board.ftNoProblems')
                    : t('board.ftNoMatches')
            }}</span>
            <button type="button" class="ft-tool" @click="clearFilters">
                {{ t('board.ftClearFilters') }}
            </button>
        </div>
        <FolderTreeMap
            v-else-if="mode === 'map'"
            ref="mapRef"
            :query="parsedQuery"
            :problems-only="problemsOnly"
            :show-services="showServices"
            :services-by-host="effectiveServices"
            :service-loading="serviceLoading"
            :service-error="serviceError"
            @expand-host="ensureServices"
            @select-host="$emit('select-host', $event)"
            @select-service="(h, n) => $emit('select-service', h, n)"
        />
        <div v-else class="ft-tree" role="tree">
            <FolderTreeRow
                v-if="rootDisplay"
                :node="rootDisplay"
                :depth="0"
                :expanded="expanded"
                :multi-site="multiSite"
                :query="parsedQuery"
                :problems-only="problemsOnly"
                :ancestor-matched="false"
                :matched-hosts="matchedHosts"
                :show-services="showServices"
                :services-by-host="effectiveServices"
                :service-loading="serviceLoading"
                :service-error="serviceError"
                :can-command="canCommand"
                @toggle="toggle"
                @expand-host="ensureServices"
                @select-host="$emit('select-host', $event)"
                @select-service="(h, n) => $emit('select-service', h, n)"
                @folder-action="$emit('folder-action', $event)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';

import { boardsApi } from '@/api/client';
import BoardSearch from '@/components/board/BoardSearch.vue';
import FolderTreeMap from '@/components/board/FolderTreeMap.vue';
import FolderTreeRow from '@/components/board/FolderTreeRow.vue';
import ProblemsOnlyToggle from '@/components/board/ProblemsOnlyToggle.vue';
import { useAuthStore } from '@/stores/auth';
import { useBoardsStore } from '@/stores/boards';
import { useStatesStore } from '@/stores/states';
import type { FolderHostService, FolderTreeNode, FolderTreeView } from '@/types/api';
import {
    isFilterActive,
    isProblemState,
    parseFolderQuery,
    selfMatches,
    subtreeVisible,
} from '@/utils/folderTreeFilter';
import { severityPills } from '@/utils/stateColors';
import { useDebounceFn } from '@/vendor/cmk/lib/useDebounce';

const props = defineProps<{ view: FolderTreeView; preview?: boolean; boardName?: string }>();
defineEmits<{
    'select-host': [FolderTreeNode];
    'select-service': [string, FolderTreeNode];
    'folder-action': [FolderTreeNode];
}>();

const { t } = useI18n();
const auth = useAuthStore();
const boards = useBoardsStore();
const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);

const mode = ref<'map' | 'list'>(props.view.default_view ?? 'list');
const expanded = reactive(new Set<string>());
const problemsOnly = ref(props.view.problems_only ?? false);
const showServices = computed(() => props.view.show_services ?? false);

const filterText = ref('');
const parsedQuery = computed(() => parseFolderQuery(filterText.value));
const filterActive = computed(() => isFilterActive(parsedQuery.value, problemsOnly.value));

// Service leaves injected by the server-side service search (keyed by host).
// Hosts surfaced purely by a service match (their own name may not match) drive
// tree visibility so a `s:` query reveals the host to drill into. Populated by
// runServiceSearch() below; the search snapshot is kept live on each SSE tick.
const searchServices = reactive<Record<string, FolderTreeNode[]>>({});
const searchTruncated = ref(false);
const searchPending = ref(false);
const matchedHosts = computed(() => new Set(Object.keys(searchServices)));
// The query carries a service/bare term (so it's answered by the server search)
// — used to suppress the "no matches" state while the term is still too short or
// a request is in flight, so the tree doesn't flash empty mid-typing.
const hasServiceOrBareTerm = computed(() =>
    parsedQuery.value.some((t) => t.field === 'service' || t.field === 'any'),
);
// Terms ≥2 chars (shorter is too broad); the backend re-applies the same floor.
const serviceSearchTerms = computed(() => {
    const long = (t: string) => t.length >= 2;
    const of = (field: string) =>
        parsedQuery.value
            .filter((t) => t.field === field)
            .map((t) => t.needle)
            .filter(long);
    return { s: of('service'), h: of('host'), q: of('any') };
});
const hasServiceSearch = computed(
    () => serviceSearchTerms.value.s.length > 0 || serviceSearchTerms.value.q.length > 0,
);

// Count hosts (and their problem-state breakdown) that survive the active
// filter, so the summary reflects what's actually shown — not the whole tree.
function visibleHostStats(
    node: FolderTreeNode,
    ancestorMatched: boolean,
): { hosts: number; counts: Record<string, number> } {
    const selfMatch = ancestorMatched || selfMatches(node, parsedQuery.value);
    if (node.kind === 'service') return { hosts: 0, counts: {} };
    if (node.kind === 'host') {
        if (
            !subtreeVisible(
                node,
                parsedQuery.value,
                problemsOnly.value,
                ancestorMatched,
                matchedHosts.value,
            )
        ) {
            return { hosts: 0, counts: {} };
        }
        return {
            hosts: 1,
            counts: isProblemState(node.state) ? { [node.state]: 1 } : {},
        };
    }
    const counts: Record<string, number> = {};
    let hosts = 0;
    for (const c of node.children) {
        const s = visibleHostStats(c, selfMatch);
        hosts += s.hosts;
        for (const k of Object.keys(s.counts)) counts[k] = (counts[k] ?? 0) + s.counts[k];
    }
    return { hosts, counts };
}

const summary = computed(() => {
    const r = root.value;
    if (!r) return { hosts: 0, counts: {} as Record<string, number> };
    if (!filterActive.value) return { hosts: r.host_count, counts: r.severity_counts };
    return visibleHostStats(r, false);
});
const summaryPills = computed(() => severityPills(summary.value.counts));
// The server service search hasn't settled: a request is in flight, or the term
// is still too short to fire. While unsettled the previous matches stay and the
// "no matches" state is held back, so the tree doesn't flash empty mid-typing.
const searchUnsettled = computed(
    () => hasServiceOrBareTerm.value && (searchPending.value || !hasServiceSearch.value),
);
// A filter is active but nothing matches → distinct empty state with a reset.
const filterEmpty = computed(
    () => !!root.value && filterActive.value && summary.value.hosts === 0 && !searchUnsettled.value,
);

function clearFilters() {
    filterText.value = '';
    problemsOnly.value = false;
}

const mapRef = useTemplateRef<InstanceType<typeof FolderTreeMap>>('mapRef');

// Persist a view-preference patch (view mode / "Problems only") so the board
// reopens the same way (mirrors the Flow board's services-layout control),
// best-effort and never in preview. The server's response — new version and
// merged view — is folded back into the shared board: otherwise each such write
// silently bumps the board version on disk while the client keeps the stale one,
// so the next Settings save 409s ("changed elsewhere"), and the next preference
// write re-sends an outdated `view` that reverts the field we just changed.
function persistView(patch: Partial<FolderTreeView>) {
    if (props.preview || !props.boardName || !auth.accessToken) return;
    void boardsApi
        .update(props.boardName, { view: { ...props.view, ...patch } }, auth.accessToken)
        .then((updated) => {
            const cur = boards.currentBoard;
            if (cur && cur.name === updated.name) {
                cur.version = updated.version;
                cur.view = updated.view;
            }
        })
        .catch(() => {});
}

function setMode(m: 'map' | 'list') {
    if (mode.value === m) return;
    mode.value = m;
    persistView({ default_view: m });
}

watch(problemsOnly, (po) => {
    if (po === (props.view.problems_only ?? false)) return;
    persistView({ problems_only: po });
});

function activeExpandAll() {
    if (mode.value === 'map') mapRef.value?.expandAll();
    else expandAll();
}
function activeCollapseAll() {
    if (mode.value === 'map') mapRef.value?.collapseAll();
    else collapseAll();
}

// Lazily-fetched services keyed by host name. The backend never pushes services
// over SSE (would not scale to 4M-host sites); they're fetched per-host only
// when the operator expands that host, then cached here for both List and Map.
const servicesByHost = reactive<Record<string, FolderTreeNode[]>>({});
const serviceLoading = reactive(new Set<string>());
const serviceError = reactive(new Set<string>());
// Path + site of every host whose services we've fetched, so we can re-fetch
// them in place on each live refresh (the leaves live outside the SSE tree).
const loadedHosts = reactive<Record<string, { path: string; siteId: string | null }>>({});

// Build a service-leaf tree node from a fetched/searched service. Shared by the
// lazy per-host fetch and the server search so both inject identical leaves.
function toServiceNode(
    s: FolderHostService,
    pathPrefix: string,
    siteId: string | null,
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
        children: [],
    };
}

async function fetchServices(name: string, hostPath: string, siteId: string | null) {
    if (!props.boardName || !auth.accessToken) return;
    const svcs = await boardsApi.folderHostServices(props.boardName, name, auth.accessToken);
    servicesByHost[name] = svcs.map((s) => toServiceNode(s, hostPath, siteId));
}

async function ensureServices(host: FolderTreeNode) {
    const name = host.title;
    if (!showServices.value || !props.boardName || !auth.accessToken) return;
    if (servicesByHost[name] || serviceLoading.has(name)) return;
    loadedHosts[name] = { path: host.path, siteId: host.site_id };
    serviceLoading.add(name);
    serviceError.delete(name);
    try {
        await fetchServices(name, host.path, host.site_id);
    } catch {
        serviceError.add(name);
    } finally {
        serviceLoading.delete(name);
    }
}

function clearSearchServices() {
    for (const k of Object.keys(searchServices)) delete searchServices[k];
    searchTruncated.value = false;
}

// Monotonic token to discard out-of-order responses: typing + the periodic SSE
// re-run fire independent requests, so without this a slow earlier response
// could overwrite a newer query's results (matchedHosts then disagrees with the
// query box). Only the latest request is allowed to mutate state.
let searchSeq = 0;

async function runServiceSearch() {
    if (props.preview || !props.boardName || !auth.accessToken || !hasServiceSearch.value) {
        clearSearchServices();
        searchPending.value = false;
        return;
    }
    const seq = ++searchSeq;
    searchPending.value = true;
    try {
        const res = await boardsApi.folderSearch(
            props.boardName,
            serviceSearchTerms.value,
            auth.accessToken,
        );
        if (seq !== searchSeq) return; // a newer search superseded this one
        const seen = new Set<string>();
        for (const m of res.matches) {
            seen.add(m.host);
            searchServices[m.host] = m.services.map((s) => toServiceNode(s, m.host, m.site_id));
        }
        for (const k of Object.keys(searchServices)) if (!seen.has(k)) delete searchServices[k];
        searchTruncated.value = res.truncated;
    } catch {
        if (seq === searchSeq) clearSearchServices();
    } finally {
        if (seq === searchSeq) searchPending.value = false;
    }
}

const runServiceSearchDebounced = useDebounceFn(runServiceSearch, 250);
// Mark pending the moment a service-bearing query changes (before the debounce
// fires) so the empty-state stays suppressed during the wait, not just during
// the request.
watch(serviceSearchTerms, () => {
    if (hasServiceSearch.value) searchPending.value = true;
    void runServiceSearchDebounced();
});

// One service-leaf source for Map + List: a manually expanded host (full lazy
// list) overrides the search snapshot for that host.
const effectiveServices = computed<Record<string, FolderTreeNode[]>>(() => ({
    ...searchServices,
    ...servicesByHost,
}));

// Keep lazily-loaded service leaves live: re-fetch the services of every host
// the operator has drilled into whenever the board's state refreshes, so leaf
// state / acknowledged / downtime stay current (a downtime set after expansion
// would otherwise never appear). Bounded by what the operator actually expanded.
// An active service search is re-run on the same tick so its (un-expanded) hits
// stay live too — one Livestatus query, independent of match count.
let lastSvcRefresh = 0;
watch(
    () => states.folderTree,
    () => {
        const now = Date.now();
        if (now - lastSvcRefresh < 4000) return;
        lastSvcRefresh = now;
        for (const [name, meta] of Object.entries(loadedHosts)) {
            void fetchServices(name, meta.path, meta.siteId).catch(() => {});
        }
        if (hasServiceSearch.value) void runServiceSearch();
    },
);

function collectFolders(node: FolderTreeNode, acc: FolderTreeNode[] = []): FolderTreeNode[] {
    if (node.kind === 'folder') {
        acc.push(node);
        node.children.forEach((c) => collectFolders(c, acc));
    }
    return acc;
}

function seed(node: FolderTreeNode, depth: number, maxDepth: number) {
    if (node.kind !== 'folder') return;
    if (depth < maxDepth) expanded.add(node.path);
    node.children.forEach((c) => seed(c, depth + 1, maxDepth));
}

// (Re)seed the expand state whenever the tree identity changes — but keep the
// operator's manual expand/collapse across live state refreshes (same root).
let seededFor = '';
watch(
    root,
    (r) => {
        if (!r) return;
        const sig = r.path + '|' + r.children.length;
        if (sig === seededFor) return;
        seededFor = sig;
        expanded.clear();
        // Main (root) is always open; its subfolders start collapsed and only
        // pre-expand when default_expand_depth > 1 (so the default view is the
        // top-level overview — drill on demand, like the map).
        expanded.add(r.path);
        r.children.forEach((c) => seed(c, 1, props.view.default_expand_depth ?? 1));
    },
    { immediate: true },
);

// List renders the real root node ("Main") as the top row so the hierarchy
// mirrors Checkmk's SETUP tree (root-level hosts sit under Main, not floating).
// Standalone backends have no root .wato → fall back to "Main".
const rootDisplay = computed<FolderTreeNode | null>(() => {
    const r = root.value;
    if (!r) return null;
    return r.title ? r : { ...r, title: 'Main' };
});

const multiSite = computed(() => {
    if (!root.value) return false;
    const sites = new Set<string>();
    const walk = (n: FolderTreeNode) => {
        if (n.kind === 'host' && n.site_id) sites.add(n.site_id);
        n.children.forEach(walk);
    };
    walk(root.value);
    return sites.size > 1;
});

// Folder bulk actions go through the same admin-only command gate as the detail
// drawer (the Livestatus command pipe bypasses CMK contact-group ACLs, so the
// backend hard-gates on is_admin). Hide the affordance for non-admins / preview
// so we never offer an action that would 403.
const canCommand = computed(() => auth.isAdmin && !props.preview);

function toggle(path: string) {
    if (expanded.has(path)) expanded.delete(path);
    else expanded.add(path);
}

function expandAll() {
    if (!root.value) return;
    collectFolders(root.value).forEach((f) => expanded.add(f.path));
}

function collapseAll() {
    if (!root.value) return;
    expanded.clear();
    expanded.add(root.value.path);
}
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
    overflow: auto;
    padding: 6px 8px;
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
