<template>
    <div class="ft-board">
        <div v-if="!preview" class="ft-toolbar">
            <div class="ft-segment" role="tablist">
                <button
                    type="button"
                    class="ft-seg"
                    :class="{ 'ft-seg--active': mode === 'map' }"
                    role="tab"
                    :aria-selected="mode === 'map'"
                    @click="mode = 'map'"
                >
                    Map
                </button>
                <button
                    type="button"
                    class="ft-seg"
                    :class="{ 'ft-seg--active': mode === 'list' }"
                    role="tab"
                    :aria-selected="mode === 'list'"
                    @click="mode = 'list'"
                >
                    List
                </button>
            </div>
            <template v-if="mode === 'list'">
                <button type="button" class="ft-tool" @click="expandAll">Expand all</button>
                <button type="button" class="ft-tool" @click="collapseAll">Collapse all</button>
            </template>
            <label class="ft-toggle-label">
                <input v-model="problemsOnly" type="checkbox" />
                Problems only
            </label>
            <span class="ft-spacer" />
            <span v-if="root" class="ft-summary">
                {{ root.host_count }} hosts
                <template v-if="summaryPills.length">
                    <span
                        v-for="p in summaryPills"
                        :key="p.state"
                        class="ft-summary-pill"
                        :style="{ background: p.bg, color: p.fg }"
                        >{{ p.count }} {{ p.state }}</span
                    >
                </template>
                <span v-else class="ft-summary-ok">· all OK</span>
            </span>
        </div>

        <div v-if="!root" class="ft-placeholder">Waiting for folder data…</div>
        <div v-else-if="!root.children.length" class="ft-placeholder">
            No folders to show. The selected connection has no SETUP folders, or your filters hide
            them.
        </div>
        <FolderTreeMap
            v-else-if="mode === 'map'"
            :problems-only="problemsOnly"
            :preview="preview"
            :show-services="showServices"
            :services-by-host="servicesByHost"
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
                :problems-only="problemsOnly"
                :show-services="showServices"
                :services-by-host="servicesByHost"
                :service-loading="serviceLoading"
                :service-error="serviceError"
                @toggle="toggle"
                @expand-host="ensureServices"
                @select-host="$emit('select-host', $event)"
                @select-service="(h, n) => $emit('select-service', h, n)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { boardsApi } from '@/api/client';
import FolderTreeMap from '@/components/board/FolderTreeMap.vue';
import FolderTreeRow from '@/components/board/FolderTreeRow.vue';
import { useAuthStore } from '@/stores/auth';
import { useStatesStore } from '@/stores/states';
import type { FolderTreeNode, FolderTreeView } from '@/types/api';
import { severityPills } from '@/utils/stateColors';

const props = defineProps<{ view: FolderTreeView; preview?: boolean; boardName?: string }>();
defineEmits<{ 'select-host': [FolderTreeNode]; 'select-service': [string, FolderTreeNode] }>();

const auth = useAuthStore();
const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);
const summaryPills = computed(() => severityPills(root.value?.severity_counts));

const mode = ref<'map' | 'list'>(props.view.default_view ?? 'list');
const expanded = reactive(new Set<string>());
const problemsOnly = ref(props.view.problems_only ?? false);
const showServices = computed(() => props.view.show_services ?? false);

// Lazily-fetched services keyed by host name. The backend never pushes services
// over SSE (would not scale to 4M-host sites); they're fetched per-host only
// when the operator expands that host, then cached here for both List and Map.
const servicesByHost = reactive<Record<string, FolderTreeNode[]>>({});
const serviceLoading = reactive(new Set<string>());
const serviceError = reactive(new Set<string>());
// Path + site of every host whose services we've fetched, so we can re-fetch
// them in place on each live refresh (the leaves live outside the SSE tree).
const loadedHosts = reactive<Record<string, { path: string; siteId: string | null }>>({});

async function fetchServices(name: string, hostPath: string, siteId: string | null) {
    if (!props.boardName || !auth.accessToken) return;
    const svcs = await boardsApi.folderHostServices(props.boardName, name, auth.accessToken);
    servicesByHost[name] = svcs.map((s) => ({
        path: `${hostPath}/${s.name}`,
        title: s.name,
        kind: 'service' as const,
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
    }));
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

// Keep lazily-loaded service leaves live: re-fetch the services of every host
// the operator has drilled into whenever the board's state refreshes, so leaf
// state / acknowledged / downtime stay current (a downtime set after expansion
// would otherwise never appear). Bounded by what the operator actually expanded.
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

.ft-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
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

.ft-toggle-label {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--text);
    cursor: pointer;
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
</style>
