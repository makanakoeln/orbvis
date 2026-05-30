<template>
    <div
        class="ft-row"
        :class="{
            'ft-row--folder': node.kind === 'folder',
            'ft-row--clickable': node.kind === 'host',
        }"
        :style="{ paddingLeft: `${depth * 18 + 6}px` }"
        role="treeitem"
        :aria-expanded="isExpandable ? isOpen : undefined"
        :title="node.output || undefined"
        @click="onRowClick"
    >
        <button
            v-if="isExpandable"
            type="button"
            class="ft-chevron"
            :aria-label="isOpen ? 'Collapse' : 'Expand'"
            @click.stop="$emit('toggle', node.path)"
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
            :style="{ background: stateColor(node.state) }"
            :title="node.state"
        />

        <span class="ft-title" :class="{ 'ft-title--empty': isEmpty }">{{ node.title }}</span>

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
    </div>

    <template v-if="isExpandable && isOpen">
        <FolderTreeRow
            v-for="child in visibleChildren"
            :key="child.path + ':' + child.kind + ':' + child.title"
            :node="child"
            :depth="depth + 1"
            :expanded="expanded"
            :multi-site="multiSite"
            :problems-only="problemsOnly"
            @toggle="$emit('toggle', $event)"
            @select-host="$emit('select-host', $event)"
        />
    </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type { FolderTreeNode } from '@/types/api';
import { severityPills, stateColor } from '@/utils/stateColors';

const props = defineProps<{
    node: FolderTreeNode;
    depth: number;
    expanded: Set<string>;
    multiSite: boolean;
    problemsOnly: boolean;
}>();

const emit = defineEmits<{ toggle: [string]; 'select-host': [FolderTreeNode] }>();

const isEmpty = computed(() => props.node.kind === 'folder' && props.node.is_empty);
const isOpen = computed(() => props.expanded.has(props.node.path));
const isExpandable = computed(() => props.node.kind === 'folder' || props.node.children.length > 0);
const pills = computed(() => severityPills(props.node.severity_counts));

const PROBLEM = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);

const visibleChildren = computed(() => {
    if (!props.problemsOnly) return props.node.children;
    return props.node.children.filter((c) =>
        c.kind === 'folder' ? c.problem_count > 0 : PROBLEM.has(c.state),
    );
});

function onRowClick() {
    if (props.node.kind === 'host') emit('select-host', props.node);
    else if (props.node.kind === 'folder') emit('toggle', props.node.path);
}
</script>

<style scoped>
.ft-row {
    display: flex;
    align-items: center;
    gap: 7px;
    height: 28px;
    font-size: 13px;
    color: var(--text);
    border-radius: 4px;
    user-select: none;
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
}

.ft-title--empty {
    color: var(--text-muted);
    font-style: italic;
    font-weight: 400;
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
}

.ft-mark {
    font-size: 11px;
    color: var(--text-muted);
}
</style>
