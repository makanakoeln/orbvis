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
        <!-- Folders expand via a chevron; hosts expand via their own icon (below),
             so a host needs no leading arrow. Services/leaves get a spacer. -->
        <button
            v-if="isExpandable && node.kind === 'folder'"
            type="button"
            class="ft-chevron"
            :aria-label="isOpen ? t('board.ftCollapse') : t('board.ftExpand')"
            @click.stop="onChevron"
        >
            {{ isOpen ? '▾' : '▸' }}
        </button>
        <span v-else class="ft-chevron ft-chevron--spacer" />

        <!-- Theme-aware folder glyph (Tabler-style) instead of an OS-dependent emoji. -->
        <svg
            v-if="node.kind === 'folder'"
            class="ft-icon"
            :class="{ 'ft-icon--empty': isEmpty }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
        >
            <path
                v-if="isOpen"
                d="M5 19l2.757-7.351A1 1 0 0 1 8.694 11H21l-2.757 7.351A1 1 0 0 1 17.306 19zM3 19V6a1 1 0 0 1 1-1h5l3 3h6a1 1 0 0 1 1 1v2"
            />
            <path
                v-else
                d="M3 6a1 1 0 0 1 1-1h5l3 3h8a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"
            />
        </svg>
        <!-- Host = a monitor/host glyph; when it can drill into services it is the
             expand toggle (click), so no separate chevron. Plain icon otherwise. -->
        <svg
            v-else-if="node.kind === 'host'"
            class="ft-icon ft-host-icon"
            :class="{
                'ft-host-icon--toggle': isExpandable,
                'ft-host-icon--open': isExpandable && isOpen,
            }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            :role="isExpandable ? 'button' : undefined"
            :aria-label="
                isExpandable ? (isOpen ? t('board.ftCollapse') : t('board.ftExpand')) : undefined
            "
            @click="onHostIconClick"
        >
            <rect x="3" y="4" width="18" height="13" rx="1" />
            <path d="M7 21h10M9 17v4M15 17v4" />
        </svg>
        <span
            v-if="!isEmpty && !(node.kind === 'folder' && pills.length)"
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
        <span v-if="node.acknowledged" class="ft-cmd ft-cmd--ack" title="Acknowledged">ACK</span>
        <span v-if="node.in_downtime" class="ft-cmd ft-cmd--dt" title="In downtime">DT</span>
        <span v-if="node.is_flapping" class="ft-cmd ft-cmd--flap" title="Flapping">FLAP</span>
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
import { useI18n } from 'vue-i18n';

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

const { t } = useI18n();

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

// The host icon is the expand toggle when the host can drill into services;
// otherwise let the click bubble to the row so it opens the drawer.
function onHostIconClick(e: MouseEvent) {
    if (props.node.kind === 'host' && isExpandable.value) {
        e.stopPropagation();
        onChevron();
    }
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
    width: 15px;
    height: 15px;
    flex-shrink: 0;
    color: var(--text-muted);
}

.ft-icon--empty {
    opacity: 0.45;
}

/* Host icon doubles as the services expand-toggle when drillable. */
.ft-host-icon--toggle {
    cursor: pointer;
}

.ft-host-icon--toggle:hover {
    color: var(--text);
}

.ft-host-icon--open {
    color: var(--accent);
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

/* Command-state badges — explicit text so they're unambiguous (a check mark for
   "acknowledged" reads as "OK"). Muted, distinct accents per kind. */
.ft-cmd {
    flex-shrink: 0;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.03em;
    line-height: 1;
    padding: 2px 5px;
    border-radius: 4px;
    border: 1px solid var(--border);
    color: var(--text-muted);
    background: var(--bg-hover);
}

.ft-cmd--ack {
    color: var(--color-state-up, #0f0);
    border-color: color-mix(in srgb, var(--color-state-up, #0a0) 45%, var(--border));
}

.ft-cmd--dt {
    color: var(--accent);
    border-color: color-mix(in srgb, var(--accent) 45%, var(--border));
}

.ft-cmd--flap {
    color: var(--color-state-warning, #ffd000);
    border-color: color-mix(in srgb, var(--color-state-warning, #ffd000) 45%, var(--border));
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
