<template>
    <div class="ft-board">
        <div class="ft-toolbar">
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
                {{ root.host_count }} hosts · {{ root.problem_count }} with problems
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
            @select-host="$emit('select-host', $event)"
        />
        <div v-else class="ft-tree" role="tree">
            <FolderTreeRow
                v-for="child in visibleRootChildren"
                :key="child.path + ':' + child.kind + ':' + child.title"
                :node="child"
                :depth="0"
                :expanded="expanded"
                :multi-site="multiSite"
                :problems-only="problemsOnly"
                @toggle="toggle"
                @select-host="$emit('select-host', $event)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import FolderTreeMap from '@/components/board/FolderTreeMap.vue';
import FolderTreeRow from '@/components/board/FolderTreeRow.vue';
import { useStatesStore } from '@/stores/states';
import type { FolderTreeNode, FolderTreeView } from '@/types/api';

const props = defineProps<{ view: FolderTreeView }>();
defineEmits<{ 'select-host': [FolderTreeNode] }>();

const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);

const mode = ref<'map' | 'list'>('map');
const expanded = reactive(new Set<string>());
const problemsOnly = ref(props.view.problems_only ?? false);

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
        expanded.add(r.path);
        r.children.forEach((c) => seed(c, 0, Math.max(1, props.view.default_expand_depth ?? 1)));
    },
    { immediate: true },
);

const PROBLEM_STATES = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);
const visibleRootChildren = computed(() => {
    if (!root.value) return [];
    if (!problemsOnly.value) return root.value.children;
    return root.value.children.filter((c) =>
        c.kind === 'folder' ? c.problem_count > 0 : PROBLEM_STATES.has(c.state),
    );
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
    font-size: 12px;
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
