<template>
    <div class="ftm">
        <div v-if="!root" class="ftm-placeholder">Waiting for folder data…</div>
        <template v-else>
            <nav class="ftm-crumbs" aria-label="Folder path">
                <button
                    v-for="(crumb, i) in breadcrumb"
                    :key="crumb.path"
                    type="button"
                    class="ftm-crumb"
                    :class="{ 'ftm-crumb--current': i === breadcrumb.length - 1 }"
                    @click="focusPath(crumb.path)"
                >
                    {{ crumb.title }}<span v-if="i < breadcrumb.length - 1" class="ftm-sep">/</span>
                </button>
            </nav>
            <div ref="hostEl" class="ftm-stage">
                <svg ref="svgEl" class="ftm-svg" />
                <div v-if="tip" class="ftm-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
                    <span class="ftm-tip-dot" :style="{ background: tip.color }" />
                    <strong>{{ tip.title }}</strong>
                    <span class="ftm-tip-meta">{{ tip.meta }}</span>
                </div>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import { hierarchy, type HierarchyCircularNode, interpolateZoom, pack, select } from 'd3';
import { computed, onMounted, ref, watch } from 'vue';

import { useD3Cleanup } from '@/composables/useD3Cleanup';
import { useStatesStore } from '@/stores/states';
import type { FolderTreeNode } from '@/types/api';
import { stateColor } from '@/utils/stateColors';

const props = defineProps<{ problemsOnly: boolean }>();
const emit = defineEmits<{ 'select-host': [FolderTreeNode] }>();

const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);

const svgEl = ref<SVGSVGElement | null>(null);
const hostEl = ref<HTMLDivElement | null>(null);
useD3Cleanup(svgEl);

type FNode = HierarchyCircularNode<FolderTreeNode>;

const WIDTH = 932;
const PROBLEM = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);
const isProblem = (n: FolderTreeNode) => PROBLEM.has(n.state);

const tip = ref<{ x: number; y: number; title: string; meta: string; color: string } | null>(null);
const breadcrumb = ref<{ path: string; title: string }[]>([]);

// Imperative d3 state kept outside Vue reactivity.
let packed: FNode | null = null;
let focusNode: FNode | null = null;
let view: [number, number, number] = [0, 0, WIDTH];
let lastPathSig = '';

// Problems-only prunes the tree to branches that carry a problem.
function prune(node: FolderTreeNode): FolderTreeNode | null {
    if (node.kind === 'host') return isProblem(node) ? node : null;
    const kids = node.children.map(prune).filter((c): c is FolderTreeNode => c !== null);
    if (!kids.length && !isProblem(node)) return null;
    return { ...node, children: kids };
}

function leafValue(d: FolderTreeNode): number {
    if (d.kind === 'host') return 1;
    if (d.kind === 'folder' && d.is_empty) return 0.6; // floor so empty folders render
    return 0;
}

function fillFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'host') return stateColor(n.state);
    if (n.kind === 'folder' && n.is_empty) return 'transparent';
    if (isProblem(n)) return stateColor(n.state);
    return 'var(--bg-surface)';
}

function fillOpacityFor(d: FNode): number {
    const n = d.data;
    if (n.kind === 'host') return 1;
    if (n.kind === 'folder' && n.is_empty) return 1;
    return isProblem(n) ? 0.16 : 0.55;
}

function strokeFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 'var(--text-muted)';
    if (n.kind === 'folder' && isProblem(n)) return stateColor(n.state);
    if (n.kind === 'host') return 'var(--border)';
    return 'var(--border)';
}

function pathSig(node: FNode): string {
    return node
        .descendants()
        .map((d) => d.data.path)
        .join('|');
}

function buildHierarchy(srcRoot: FolderTreeNode): FNode {
    return pack<FolderTreeNode>().size([WIDTH, WIDTH]).padding(3)(
        hierarchy<FolderTreeNode>(srcRoot, (d) => (d.kind === 'folder' ? d.children : undefined))
            .sum(leafValue)
            .sort((a, b) => (b.value ?? 0) - (a.value ?? 0)),
    );
}

function zoomTo(v: [number, number, number]): void {
    if (!svgEl.value) return;
    const k = WIDTH / v[2];
    view = v;
    const g = select(svgEl.value).select('g');
    g.selectAll<SVGCircleElement, FNode>('circle')
        .attr('transform', (d) => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`)
        .attr('r', (d) => d.r * k);
    g.selectAll<SVGTextElement, FNode>('text')
        .attr('transform', (d) => `translate(${(d.x - v[0]) * k},${(d.y - v[1]) * k})`)
        // Sit the label on the upper rim so it never overlaps the child dots.
        .attr('y', (d) => -(d.r * k) + 16);
}

function updateBreadcrumb(): void {
    breadcrumb.value = focusNode
        ? focusNode
              .ancestors()
              .reverse()
              .map((a) => ({ path: a.data.path, title: a.data.title }))
        : [];
}

function labelVisible(d: FNode): number {
    // Show a folder's label when it sits one level below the current focus.
    return d.parent === focusNode && d.data.kind === 'folder' ? 1 : 0;
}

function zoomToNode(d: FNode): void {
    if (!svgEl.value) return;
    focusNode = d;
    updateBreadcrumb();
    const svg = select(svgEl.value);
    const target: [number, number, number] = [d.x, d.y, d.r * 2];
    svg.transition()
        .duration(680)
        .tween('zoom', () => {
            const i = interpolateZoom(view, target);
            return (t: number) => zoomTo(i(t) as [number, number, number]);
        });
    svg.select('g')
        .selectAll<SVGTextElement, FNode>('text')
        .transition()
        .duration(680)
        .style('fill-opacity', labelVisible)
        .on('start', function (this: SVGTextElement, dd) {
            if (labelVisible(dd)) this.style.display = 'inline';
        })
        .on('end', function (this: SVGTextElement, dd) {
            if (!labelVisible(dd)) this.style.display = 'none';
        });
}

function focusPath(path: string): void {
    if (!packed) return;
    const target = packed.descendants().find((d) => d.data.path === path);
    if (target) zoomToNode(target);
}

function showTip(event: MouseEvent, d: FNode): void {
    if (!hostEl.value) return;
    const rect = hostEl.value.getBoundingClientRect();
    const n = d.data;
    const meta =
        n.kind === 'host'
            ? n.state
            : n.is_empty
              ? 'empty · 0 hosts'
              : `${n.host_count} hosts · ${n.problem_count} with problems`;
    tip.value = {
        x: event.clientX - rect.left + 12,
        y: event.clientY - rect.top + 12,
        title: n.title,
        meta,
        color: n.is_empty ? 'var(--text-muted)' : stateColor(n.state),
    };
}

function render(): void {
    if (!svgEl.value || !root.value) return;
    const src = props.problemsOnly
        ? (prune(root.value) ?? { ...root.value, children: [] })
        : root.value;
    packed = buildHierarchy(src);

    // Preserve the operator's current focus across a rebuild when its folder
    // still exists; otherwise reset to root.
    const keepPath = focusNode?.data.path;
    focusNode = (keepPath && packed.descendants().find((d) => d.data.path === keepPath)) || packed;
    updateBreadcrumb();

    const svg = select(svgEl.value)
        .attr('viewBox', `${-WIDTH / 2} ${-WIDTH / 2} ${WIDTH} ${WIDTH}`)
        .style('cursor', 'pointer')
        .on('click', () => packed && zoomToNode(packed));

    svg.selectAll('g').remove();
    const g = svg.append('g');

    const nodes = packed.descendants().slice(1); // skip synthetic root circle

    g.selectAll<SVGCircleElement, FNode>('circle')
        .data(nodes, (d) => d.data.path)
        .join('circle')
        .attr('fill', fillFor)
        .attr('fill-opacity', fillOpacityFor)
        .attr('stroke', strokeFor)
        .attr('stroke-width', (d) => (d.data.kind === 'folder' && d.data.is_empty ? 1.5 : 1))
        .attr('stroke-dasharray', (d) =>
            d.data.kind === 'folder' && d.data.is_empty ? '4 3' : null,
        )
        .style('cursor', 'pointer')
        .on('click', (event: MouseEvent, d) => {
            event.stopPropagation();
            if (d.data.kind === 'host') emit('select-host', d.data);
            else zoomToNode(d);
        })
        .on('mousemove', showTip)
        .on('mouseleave', () => (tip.value = null));

    g.selectAll<SVGTextElement, FNode>('text')
        .data(
            nodes.filter((d) => d.data.kind === 'folder'),
            (d) => d.data.path,
        )
        .join('text')
        .attr('class', 'ftm-label')
        .style('fill-opacity', labelVisible)
        .style('display', (d) => (labelVisible(d) ? 'inline' : 'none'))
        .text((d) => d.data.title);

    zoomTo([focusNode.x, focusNode.y, focusNode.r * 2]);
    lastPathSig = pathSig(packed);
}

// Recolor only — no relayout — when structure is unchanged.
function recolor(): void {
    if (!svgEl.value) return;
    const g = select(svgEl.value).select('g');
    g.selectAll<SVGCircleElement, FNode>('circle')
        .transition()
        .duration(400)
        .attr('fill', fillFor)
        .attr('fill-opacity', fillOpacityFor)
        .attr('stroke', strokeFor);
}

watch(
    [root, () => props.problemsOnly],
    () => {
        if (!root.value || !svgEl.value) return;
        const next = props.problemsOnly
            ? (prune(root.value) ?? { ...root.value, children: [] })
            : root.value;
        const candidate = buildHierarchy(next);
        if (packed && pathSig(candidate) === lastPathSig) recolor();
        else render();
    },
    { flush: 'post' },
);

onMounted(() => {
    if (root.value) render();
});
</script>

<style scoped>
.ftm {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
}

.ftm-crumbs {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 2px;
    padding: 6px 12px;
    font-size: 12px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.ftm-crumb {
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    padding: 2px 3px;
    font-size: 12px;
}

.ftm-crumb:hover {
    color: var(--text);
}

.ftm-crumb--current {
    color: var(--text);
    font-weight: 600;
}

.ftm-sep {
    color: var(--text-muted);
    margin-left: 4px;
}

.ftm-stage {
    position: relative;
    flex: 1;
    min-height: 0;
}

.ftm-svg {
    width: 100%;
    height: 100%;
    display: block;
}

.ftm-svg :deep(.ftm-label) {
    text-anchor: middle;
    pointer-events: none;
    fill: var(--text);
    font-size: 15px;
    font-weight: 600;
    paint-order: stroke;
    stroke: var(--bg-glass);
    stroke-width: 3px;
    stroke-linejoin: round;
}

.ftm-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 13px;
}

.ftm-tip {
    position: absolute;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 5px 9px;
    border-radius: 6px;
    background: var(--bg-glass);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 12px;
    pointer-events: none;
    white-space: nowrap;
    box-shadow: 0 2px 10px rgb(0 0 0 / 18%);
}

.ftm-tip-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
}

.ftm-tip-meta {
    color: var(--text-muted);
}
</style>
