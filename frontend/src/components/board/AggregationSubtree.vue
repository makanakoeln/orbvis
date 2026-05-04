<template>
    <svg
        :width="size.w"
        :height="size.h"
        :viewBox="`${-size.w / 2} 0 ${size.w} ${size.h}`"
        class="absolute pointer-events-none"
        :style="{ left: `${-size.w / 2 + iconSize / 2}px`, top: `${iconSize}px` }"
    >
        <line
            v-for="link in renderedLinks"
            :key="link.key"
            :x1="link.x1"
            :y1="link.y1"
            :x2="link.x2"
            :y2="link.y2"
            stroke="rgb(113 113 122 / 0.5)"
            stroke-width="1"
        />
        <!-- Root is the BoardObject icon itself, so skip it here -->
        <g
            v-for="node in renderedNodes"
            :key="node.id"
            :transform="`translate(${node.x}, ${node.y})`"
            class="pointer-events-auto cursor-pointer"
            @click.stop="onNodeClick(node.data)"
            @mouseenter="onNodeEnter(node.data, $event)"
            @mouseleave="$emit('node-leave')"
        >
            <title>{{ tooltipFor(node.data) }}</title>
            <circle
                :r="nodeRadius"
                :fill="stateColorFor(node.data)"
                :stroke="strokeFor(node.data)"
                :stroke-width="node.data.in_downtime || node.data.acknowledged ? 2.5 : 1.5"
                :stroke-dasharray="node.data.in_downtime ? '3 2' : undefined"
            />
            <!-- Downtime/ack badges — same SVG paths as BoardObject's badges so
                 the visual language matches across normal icons and subtree nodes. -->
            <g
                v-if="node.data.in_downtime"
                :transform="`translate(${-BADGE_OFFSET_F * nodeRadius}, ${-BADGE_OFFSET_F * nodeRadius})`"
            >
                <circle
                    :r="nodeRadius * BADGE_RADIUS_F"
                    :fill="DOWNTIME_COLOR"
                    stroke="rgb(24 24 27)"
                    stroke-width="1"
                />
                <path
                    transform="translate(-6, -6) scale(0.5)"
                    fill="white"
                    d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"
                />
            </g>
            <g
                v-else-if="node.data.acknowledged"
                :transform="`translate(${BADGE_OFFSET_F * nodeRadius}, ${-BADGE_OFFSET_F * nodeRadius})`"
            >
                <circle
                    :r="nodeRadius * BADGE_RADIUS_F"
                    :fill="ACKNOWLEDGED_COLOR"
                    stroke="rgb(24 24 27)"
                    stroke-width="1"
                />
                <path
                    transform="translate(-6, -6) scale(0.5)"
                    fill="none"
                    stroke="rgb(24 24 27)"
                    stroke-width="3.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M4.5 12.75l6 6 9-13.5"
                />
            </g>
            <text
                :y="nodeRadius + fontSize + 2"
                text-anchor="middle"
                fill="rgb(212 212 216)"
                :font-size="fontSize"
                font-family="system-ui,-apple-system,sans-serif"
                style="paint-order: stroke; stroke: rgb(0 0 0 / 70%); stroke-width: 3px"
            >
                {{ truncate(node.data.name) }}
            </text>
        </g>
    </svg>
</template>

<script setup lang="ts">
import { hierarchy, type HierarchyNode, tree as d3Tree } from 'd3';
import { computed } from 'vue';

import { useSettingsStore } from '@/stores/settings';
import type { AggregationNode, BoardObject, MonitoringState, ObjectState } from '@/types/api';
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation';
import { ACKNOWLEDGED_COLOR, DOWNTIME_COLOR, stateColor } from '@/utils/stateColors';

const props = defineProps<{
    tree: AggregationNode;
    iconSize: number;
}>();

const emit = defineEmits<{
    'node-enter': [obj: BoardObject, state: ObjectState, event: MouseEvent];
    'node-leave': [];
}>();

const settingsStore = useSettingsStore();

// Sizes scale with the board's icon size so subtree nodes look proportional.
const nodeRadius = computed(() => Math.max(8, props.iconSize * 0.4));
const fontSize = computed(() => Math.max(11, Math.round(props.iconSize * 0.42)));
const vSpacing = computed(() => Math.max(70, props.iconSize * 2.6));
const hSpacing = computed(() => Math.max(120, props.iconSize * 4));

const MAX_LABEL = 18;
const BADGE_OFFSET_F = 0.7; // badge center offset from node center (× nodeRadius)
const BADGE_RADIUS_F = 0.55; // badge circle radius (× nodeRadius)
const TOP_PAD = 20; // top inset before the root row
const LABEL_PAD = 60; // extra horizontal padding for label overflow

// BI state codes (cmk.bi.bi_aggregation.BIStates) → service-style labels.
const BI_STATE_LABEL: Record<number, MonitoringState> = {
    0: 'OK',
    1: 'WARNING',
    2: 'CRITICAL',
    3: 'UNKNOWN',
};

function stateColorFor(node: AggregationNode): string {
    return stateColor(BI_STATE_LABEL[node.state] ?? 'PENDING');
}

function strokeFor(node: AggregationNode): string {
    if (node.in_downtime) return DOWNTIME_COLOR;
    if (node.acknowledged) return ACKNOWLEDGED_COLOR;
    return 'rgb(24 24 27)';
}

function truncate(s: string): string {
    return s.length > MAX_LABEL ? s.slice(0, MAX_LABEL - 2) + '…' : s;
}

function tooltipFor(node: AggregationNode): string {
    const stateLabel = BI_STATE_LABEL[node.state] ?? 'PENDING';
    const flags: string[] = [];
    if (node.in_downtime) flags.push('downtime');
    if (node.acknowledged) flags.push('ack');
    const suffix = flags.length ? ` (${flags.join(', ')})` : '';
    return `${node.name} — ${stateLabel}${suffix}`;
}

function syntheticObject(node: AggregationNode): BoardObject {
    const isLeaf = node.node_type === 'bi_leaf';
    const type = isLeaf ? (node.service_description ? 'service' : 'host') : 'aggregation';
    return {
        id: `bi-subtree-${node.host_name ?? ''}-${node.service_description ?? ''}-${node.name}`,
        type,
        x: 0,
        y: 0,
        z: 1,
        host_name: node.host_name ?? null,
        service_description: node.service_description ?? null,
        aggregation_id: isLeaf ? null : node.name,
        url_target: '_blank',
    };
}

function syntheticState(obj: BoardObject, node: AggregationNode): ObjectState {
    return {
        object_id: obj.id,
        type: obj.type,
        state: BI_STATE_LABEL[node.state] ?? 'PENDING',
        output: '',
        perf_data: '',
        acknowledged: node.acknowledged ?? false,
        in_downtime: node.in_downtime ?? false,
        stale: false,
    };
}

function onNodeClick(node: AggregationNode) {
    if (node.node_type !== 'bi_leaf' || !node.host_name) return;
    const url = buildCheckmkUrl(syntheticObject(node), settingsStore.settings.checkmk_url ?? null);
    if (url) openUrl(url, '_blank');
}

function onNodeEnter(node: AggregationNode, event: MouseEvent) {
    const obj = syntheticObject(node);
    emit('node-enter', obj, syntheticState(obj, node), event);
}

interface RenderedNode {
    id: string;
    x: number;
    y: number;
    data: AggregationNode;
}
interface RenderedLink {
    key: string;
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

// d3.tree() produces a tidy hierarchical layout: every parent's subtree gets a
// contiguous horizontal range, so siblings cluster under their parent and edges
// never cross. nodeSize gives a stable per-node footprint regardless of tree
// width — much more predictable than forceSimulation for strict hierarchies.
const layout = computed(() => {
    const root: HierarchyNode<AggregationNode> = hierarchy(props.tree, (n) => n.children);
    const layoutFn = d3Tree<AggregationNode>().nodeSize([hSpacing.value, vSpacing.value]);
    return layoutFn(root);
});

const renderedNodes = computed<RenderedNode[]>(() => {
    const out: RenderedNode[] = [];
    let i = 0;
    layout.value.each((n) => {
        if (n.depth === 0) {
            i++;
            return;
        }
        out.push({
            id: `n${i++}`,
            x: n.x ?? 0,
            y: TOP_PAD + (n.y ?? 0),
            data: n.data,
        });
    });
    return out;
});

const renderedLinks = computed<RenderedLink[]>(() => {
    const out: RenderedLink[] = [];
    let idx = 0;
    layout.value.each((n) => {
        if (!n.parent) return;
        out.push({
            key: `l${idx++}`,
            x1: n.parent.x ?? 0,
            y1: TOP_PAD + (n.parent.y ?? 0),
            x2: n.x ?? 0,
            y2: TOP_PAD + (n.y ?? 0),
        });
    });
    return out;
});

const size = computed(() => {
    let minX = 0;
    let maxX = 0;
    let maxY = 0;
    layout.value.each((n) => {
        const x = n.x ?? 0;
        const y = n.y ?? 0;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
    });
    return {
        w: Math.max(320, maxX - minX + hSpacing.value + LABEL_PAD),
        h: maxY + vSpacing.value + TOP_PAD * 2,
    };
});
</script>
