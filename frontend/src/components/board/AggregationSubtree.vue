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
        >
            <circle
                :r="NODE_R"
                :fill="stateColorFor(node.data)"
                stroke="rgb(24 24 27)"
                stroke-width="1.5"
            />
            <text
                :y="NODE_R + 10"
                text-anchor="middle"
                fill="rgb(212 212 216)"
                font-size="9"
                font-family="system-ui,-apple-system,sans-serif"
            >
                {{ truncate(node.data.name) }}
            </text>
        </g>
    </svg>
</template>

<script setup lang="ts">
import {
    forceCollide,
    forceLink,
    forceManyBody,
    forceSimulation,
    forceX,
    forceY,
    type SimulationLinkDatum,
    type SimulationNodeDatum,
} from 'd3';
import { computed, ref, watch } from 'vue';

import { useSettingsStore } from '@/stores/settings';
import type { AggregationNode } from '@/types/api';
import { buildCheckmkUrl, openUrl } from '@/utils/boardNavigation';
import { stateColor } from '@/utils/stateColors';

const props = defineProps<{
    tree: AggregationNode;
    iconSize: number;
}>();

const settingsStore = useSettingsStore();

const NODE_R = 7;
const V_SPACING = 60;
const H_SPACING = 50;
const MAX_LABEL = 16;

interface FNode extends SimulationNodeDatum {
    id: string;
    level: number;
    data: AggregationNode;
}
type FLink = SimulationLinkDatum<FNode>;

const BI_STATE_LABEL: Record<number, string> = {
    0: 'OK',
    1: 'WARNING',
    2: 'CRITICAL',
    3: 'UNKNOWN',
};

function stateColorFor(node: AggregationNode): string {
    return stateColor(BI_STATE_LABEL[node.state] ?? 'PENDING');
}

function truncate(s: string): string {
    return s.length > MAX_LABEL ? s.slice(0, MAX_LABEL - 2) + '…' : s;
}

function onNodeClick(node: AggregationNode) {
    if (node.node_type !== 'bi_leaf' || !node.host_name) return;
    const url = buildCheckmkUrl(
        {
            id: 'bi-leaf',
            type: node.service_description ? 'service' : 'host',
            x: 0,
            y: 0,
            z: 1,
            host_name: node.host_name,
            service_description: node.service_description ?? null,
            url_target: '_blank',
        },
        settingsStore.settings.checkmk_url ?? null,
    );
    if (url) openUrl(url, '_blank');
}

interface Flattened {
    nodes: FNode[];
    links: FLink[];
    maxLevel: number;
    topologyHash: string;
}

// Memoize the tree walk: parent re-emits `tree` on every state poll, but the
// topology only changes when nodes are added/removed/renamed. Hashing it lets
// runLayout skip the (expensive) force simulation on pure state updates.
const flat = computed<Flattened>(() => {
    const nodes: FNode[] = [];
    const links: FLink[] = [];
    const hashParts: string[] = [];
    let maxLevel = 0;
    const walk = (node: AggregationNode, level: number, parentId: string | null, idx: number) => {
        const id = parentId ? `${parentId}/${idx}` : 'root';
        nodes.push({ id, level, data: node });
        hashParts.push(
            `${id}|${node.node_type}|${node.host_name ?? ''}|${node.service_description ?? ''}`,
        );
        maxLevel = Math.max(maxLevel, level);
        if (parentId !== null) links.push({ source: parentId, target: id });
        node.children.forEach((c, i) => walk(c, level + 1, id, i));
    };
    walk(props.tree, 0, null, 0);
    return { nodes, links, maxLevel, topologyHash: hashParts.join('\n') };
});

const size = computed(() => {
    const { nodes, maxLevel } = flat.value;
    const leafCount = nodes.filter((n) => n.level === maxLevel).length;
    return {
        w: Math.max(300, leafCount * H_SPACING + 80),
        h: (maxLevel + 1) * V_SPACING + 40,
    };
});

const renderedNodes = ref<FNode[]>([]);
const renderedLinks = ref<{ key: string; x1: number; y1: number; x2: number; y2: number }[]>([]);

function runLayout() {
    const { nodes, links } = flat.value;
    if (nodes.length <= 1) {
        renderedNodes.value = [];
        renderedLinks.value = [];
        return;
    }

    nodes[0].fx = 0;
    nodes[0].fy = 20;

    const sim = forceSimulation<FNode>(nodes)
        .force(
            'link',
            forceLink<FNode, FLink>(links)
                .id((d) => d.id)
                .distance(V_SPACING * 0.9)
                .strength(0.5),
        )
        .force('charge', forceManyBody<FNode>().strength(-180))
        .force('collide', forceCollide<FNode>(NODE_R + 6).iterations(3))
        .force('y', forceY<FNode>((d) => 20 + d.level * V_SPACING).strength(0.9))
        .force('x', forceX<FNode>(0).strength(0.05))
        .alphaDecay(0.1)
        .stop();

    for (let i = 0; i < 200; i++) sim.tick();

    const byId = new Map(nodes.map((n) => [n.id, n] as const));
    renderedNodes.value = nodes.slice(1);
    renderedLinks.value = links.map((l, idx) => {
        const src = typeof l.source === 'string' ? byId.get(l.source)! : (l.source as FNode);
        const tgt = typeof l.target === 'string' ? byId.get(l.target)! : (l.target as FNode);
        return {
            key: `${src.id}-${tgt.id}-${idx}`,
            x1: src.x ?? 0,
            y1: src.y ?? 0,
            x2: tgt.x ?? 0,
            y2: tgt.y ?? 0,
        };
    });
}

watch(() => flat.value.topologyHash, runLayout, { immediate: true });
</script>
