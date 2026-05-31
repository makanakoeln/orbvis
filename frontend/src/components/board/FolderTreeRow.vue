<template>
    <div
        class="ft-row"
        :class="{
            'ft-row--folder': node.kind === 'folder',
            'ft-row--clickable': node.kind !== 'folder',
        }"
        role="treeitem"
        :aria-expanded="isExpandable ? isOpen : undefined"
        :title="node.output || undefined"
        @click="onRowClick"
    >
        <!-- One vertical guide per ancestor level so the nesting depth (e.g.
             a host directly under Main vs. inside a subfolder) is unambiguous. -->
        <span v-for="i in depth" :key="i" class="ft-guide" />
        <button
            v-if="isExpandable"
            type="button"
            class="ft-chevron"
            :aria-label="isOpen ? 'Collapse' : 'Expand'"
            @click.stop="onChevron"
        >
            {{ isOpen ? '▾' : '▸' }}
        </button>
        <span v-else class="ft-chevron ft-chevron--spacer" />

        <span class="ft-icon" :class="{ 'ft-icon--empty': isEmpty }">
            {{ node.kind === 'folder' ? (isOpen ? '📂' : '📁') : '' }}
        </span>
        <span
            v-if="!isEmpty"
            class="ft-dot"
            :style="{ background: stateColorVar(node.state) }"
            :title="node.state"
        />

        <span
            class="ft-title"
            :class="{ 'ft-title--empty': isEmpty, 'ft-title--svc': node.kind === 'service' }"
            >{{ node.title }}</span
        >

        <!-- Service plugin output fills the free row space — the operator's main
             triage signal ("DISK CRITICAL - free space: / 2%"); flexes + ellipsis
             so markers/age stay right-aligned. Full text on hover (row title). -->
        <span v-if="node.kind === 'service'" class="ft-output">{{ node.output }}</span>

        <span v-if="isEmpty" class="ft-badge ft-badge--empty">empty · 0 hosts</span>
        <span v-else-if="node.kind === 'folder'" class="ft-meta">{{ node.host_count }} hosts</span>
        <span v-if="node.kind === 'folder' && pills.length" class="ft-pills">
            <span
                v-for="p in pills"
                :key="p.state"
                class="ft-pill"
                :style="{ background: p.bg, color: p.fg }"
                :title="`${p.count} ${p.state}`"
                >{{ p.count }}</span
            >
        </span>

        <span v-if="node.kind === 'host' && multiSite && node.site_id" class="ft-site">{{
            node.site_id
        }}</span>
        <span v-if="node.acknowledged" class="ft-mark" title="Acknowledged">✔</span>
        <span v-if="node.in_downtime" class="ft-mark" title="In downtime">⏸</span>
        <span v-if="node.is_flapping" class="ft-mark" title="Flapping">↯</span>
        <span v-if="age" class="ft-age" title="Since last state change">{{ age }}</span>
    </div>

    <template v-if="isExpandable && isOpen">
        <!-- A host expands to its lazily-loaded services (fetched on demand so the
             board scales to huge sites); folders expand to their tree children. -->
        <template v-if="node.kind === 'host'">
            <div v-if="serviceLoading.has(node.title)" class="ft-note" :style="noteIndent">
                Loading services…
            </div>
            <div
                v-else-if="serviceError.has(node.title)"
                class="ft-note ft-note--err"
                :style="noteIndent"
            >
                Could not load services
            </div>
            <div v-else-if="!visibleChildren.length" class="ft-note" :style="noteIndent">
                {{ problemsOnly ? 'No problem services' : 'No services' }}
            </div>
            <FolderTreeRow
                v-for="child in visibleChildren"
                v-else
                :key="child.path + ':' + child.kind + ':' + child.title"
                :node="child"
                :depth="depth + 1"
                :expanded="expanded"
                :multi-site="multiSite"
                :query="query"
                :problems-only="problemsOnly"
                :ancestor-matched="childAncestorMatched"
                :show-services="showServices"
                :services-by-host="servicesByHost"
                :service-loading="serviceLoading"
                :service-error="serviceError"
                :host-name="node.title"
                @toggle="$emit('toggle', $event)"
                @expand-host="$emit('expand-host', $event)"
                @select-host="$emit('select-host', $event)"
                @select-service="(h, n) => $emit('select-service', h, n)"
            />
        </template>
        <template v-else>
            <FolderTreeRow
                v-for="child in visibleChildren"
                :key="child.path + ':' + child.kind + ':' + child.title"
                :node="child"
                :depth="depth + 1"
                :expanded="expanded"
                :multi-site="multiSite"
                :query="query"
                :problems-only="problemsOnly"
                :ancestor-matched="childAncestorMatched"
                :show-services="showServices"
                :services-by-host="servicesByHost"
                :service-loading="serviceLoading"
                :service-error="serviceError"
                @toggle="$emit('toggle', $event)"
                @expand-host="$emit('expand-host', $event)"
                @select-host="$emit('select-host', $event)"
                @select-service="(h, n) => $emit('select-service', h, n)"
            />
        </template>
    </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type { FolderTreeNode } from '@/types/api';
import {
    isFilterActive,
    type ParsedQuery,
    selfMatches,
    subtreeVisible,
} from '@/utils/folderTreeFilter';
import { severityPills, stateColorVar } from '@/utils/stateColors';
import { formatRelativeDuration } from '@/utils/time';

const props = defineProps<{
    node: FolderTreeNode;
    depth: number;
    expanded: Set<string>;
    multiSite: boolean;
    query: ParsedQuery;
    problemsOnly: boolean;
    // True once a containing folder/host already matched the query, so this
    // whole subtree counts as matching.
    ancestorMatched: boolean;
    showServices: boolean;
    servicesByHost: Record<string, FolderTreeNode[]>;
    serviceLoading: Set<string>;
    serviceError: Set<string>;
    // Set on service rows so a click can resolve the owning host for the drawer.
    hostName?: string;
}>();

const emit = defineEmits<{
    toggle: [string];
    'expand-host': [FolderTreeNode];
    'select-host': [FolderTreeNode];
    'select-service': [string, FolderTreeNode];
}>();

const isEmpty = computed(() => props.node.kind === 'folder' && props.node.is_empty);
const isOpen = computed(() => props.expanded.has(props.node.path));
// Hosts are expandable only when show_services is on (drill host → services).
const isExpandable = computed(
    () =>
        props.node.kind === 'folder' ||
        (props.node.kind === 'host' && props.showServices) ||
        props.node.children.length > 0,
);
const pills = computed(() => severityPills(props.node.severity_counts));
const age = computed(() =>
    props.node.kind === 'service' ? formatRelativeDuration(props.node.last_state_change) : '',
);
const noteIndent = computed(() => ({ paddingLeft: `${(props.depth + 1) * 18 + 16}px` }));

// Once this node matches the query, its whole subtree counts as matching.
const childAncestorMatched = computed(
    () => props.ancestorMatched || selfMatches(props.node, props.query),
);

// A host's children are its lazily-loaded services (keyed by host name);
// everything else uses the tree children pushed by the store.
const childNodes = computed<FolderTreeNode[]>(() =>
    props.node.kind === 'host'
        ? (props.servicesByHost[props.node.title] ?? [])
        : props.node.children,
);

const visibleChildren = computed(() => {
    if (!isFilterActive(props.query, props.problemsOnly)) return childNodes.value;
    return childNodes.value.filter((c) =>
        subtreeVisible(c, props.query, props.problemsOnly, childAncestorMatched.value),
    );
});

function onChevron() {
    emit('toggle', props.node.path);
    if (props.node.kind === 'host') emit('expand-host', props.node);
}

function onRowClick() {
    if (props.node.kind === 'host') emit('select-host', props.node);
    else if (props.node.kind === 'service')
        emit('select-service', props.hostName ?? '', props.node);
    else emit('toggle', props.node.path);
}
</script>

<style scoped>
.ft-row {
    display: flex;
    align-items: center;
    gap: 7px;
    height: 28px;
    padding-left: 6px;
    font-size: 13px;
    color: var(--text);
    border-radius: 4px;
    user-select: none;
}

/* One per ancestor level: an 18px column with a left guide line. The negative
   margin cancels the row's 7px flex gap so columns stay tight (18px each). */
.ft-guide {
    width: 18px;
    flex-shrink: 0;
    align-self: stretch;
    margin-right: -7px;
    border-left: 1px solid var(--border);
}

.ft-row--clickable {
    cursor: pointer;
}

.ft-row--folder {
    cursor: pointer;
    font-weight: 500;
}

.ft-row:hover {
    background: var(--bg-hover);
}

.ft-chevron {
    width: 16px;
    flex-shrink: 0;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 11px;
    padding: 0;
}

.ft-chevron--spacer {
    cursor: default;
}

.ft-icon {
    font-size: 13px;
    flex-shrink: 0;
}

.ft-icon--empty {
    opacity: 0.45;
}

.ft-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 0 1px var(--border);
}

.ft-title {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 0;
}

/* Service name yields to the plugin-output column once it gets long, but keeps
   priority up to a sensible cap. */
.ft-title--svc {
    font-weight: 400;
    flex-shrink: 1;
    max-width: 40%;
}

.ft-title--empty {
    color: var(--text-muted);
    font-style: italic;
    font-weight: 400;
}

.ft-output {
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 12px;
    color: var(--text-muted);
}

.ft-meta {
    color: var(--text-muted);
    font-size: 11px;
}

.ft-badge {
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 9px;
    flex-shrink: 0;
}

.ft-badge--empty {
    color: var(--text-muted);
    border: 1px dashed var(--border);
}

.ft-pills {
    display: inline-flex;
    gap: 3px;
    flex-shrink: 0;
}

.ft-pill {
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
    padding: 2px 6px;
    border-radius: 9px;
    min-width: 16px;
    text-align: center;
}

.ft-site {
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 4px;
    background: var(--bg-hover);
    color: var(--text-muted);
    border: 1px solid var(--border);
    flex-shrink: 0;
}

.ft-mark {
    font-size: 11px;
    color: var(--text-muted);
    flex-shrink: 0;
}

.ft-age {
    font-size: 11px;
    color: var(--text-muted);
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
}

.ft-note {
    display: flex;
    align-items: center;
    height: 24px;
    font-size: 12px;
    font-style: italic;
    color: var(--text-muted);
}

.ft-note--err {
    color: var(--color-state-critical);
    font-style: normal;
}
</style>
