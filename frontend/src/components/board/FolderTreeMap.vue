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
                    @click="setFocus(crumb.path)"
                >
                    {{ crumb.title || 'Main'
                    }}<span v-if="i < breadcrumb.length - 1" class="ftm-sep">›</span>
                </button>
            </nav>
            <div ref="hostEl" class="ftm-stage">
                <svg ref="svgEl" class="ftm-svg" />
                <div v-if="tip" class="ftm-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
                    <span class="ftm-tip-dot" :style="{ background: tip.color }" />
                    <strong>{{ tip.title }}</strong>
                    <span class="ftm-tip-meta">{{ tip.meta }}</span>
                </div>
                <div v-if="empty" class="ftm-placeholder ftm-placeholder--overlay">
                    Nothing to show here.
                </div>
            </div>
        </template>
    </div>
</template>

<script setup lang="ts">
import { hierarchy, type HierarchyRectangularNode, select, treemap, treemapSquarify } from 'd3';
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import { useStatesStore } from '@/stores/states';
import type { FolderTreeNode } from '@/types/api';
import { severityPills, stateColor } from '@/utils/stateColors';

const props = defineProps<{ problemsOnly: boolean }>();
const emit = defineEmits<{ 'select-host': [FolderTreeNode] }>();

const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);

const svgEl = ref<SVGSVGElement | null>(null);
const hostEl = ref<HTMLDivElement | null>(null);

type FNode = HierarchyRectangularNode<FolderTreeNode>;

const HEADER = 19; // folder title bar height
const PROBLEM = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);
const isProblem = (n: FolderTreeNode) => PROBLEM.has(n.state);

const tip = ref<{ x: number; y: number; title: string; meta: string; color: string } | null>(null);
const breadcrumb = ref<{ path: string; title: string }[]>([]);
const empty = ref(false);

// Imperative state, kept outside Vue reactivity.
let focusPath = '';
let lastPathSig = '';
let dims = { w: 0, h: 0 };
let resizeObs: ResizeObserver | null = null;

function prune(node: FolderTreeNode): FolderTreeNode | null {
    if (node.kind === 'host') return isProblem(node) ? node : null;
    const kids = node.children.map(prune).filter((c): c is FolderTreeNode => c !== null);
    if (!kids.length && !isProblem(node)) return null;
    return { ...node, children: kids };
}

function currentRoot(): FolderTreeNode {
    if (!root.value) return { path: '', title: '', kind: 'folder' } as FolderTreeNode;
    if (!props.problemsOnly) return root.value;
    return prune(root.value) ?? { ...root.value, children: [] };
}

function findNode(node: FolderTreeNode, path: string): FolderTreeNode | null {
    if (node.path === path) return node;
    const next = node.children?.find((c) => path === c.path || path.startsWith(c.path + '/'));
    return next ? findNode(next, path) : null;
}

function chainTo(node: FolderTreeNode, target: string): { path: string; title: string }[] {
    const acc = [{ path: node.path, title: node.title }];
    if (node.path === target) return acc;
    const next = node.children?.find((c) => target === c.path || target.startsWith(c.path + '/'));
    return next ? acc.concat(chainTo(next, target)) : acc;
}

function leafValue(d: FolderTreeNode): number {
    if (d.kind === 'host') return 1;
    if (d.kind === 'folder' && d.is_empty) return 1; // keep empty folders visible
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
    // Healthy hosts recede so problem tiles dominate the operator's eye.
    if (n.kind === 'host') return isProblem(n) ? 1 : 0.4;
    if (n.kind === 'folder' && n.is_empty) return 1;
    return isProblem(n) ? 0.12 : 0.4;
}

function folderHeaderText(n: FolderTreeNode): string {
    if (n.is_empty) return `${n.title} · empty`;
    const pills = severityPills(n.severity_counts);
    if (pills.length) return `${n.title} · ${pills[0].count} ${pills[0].state}`;
    return `${n.title} · ${n.host_count}`;
}

function strokeFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'folder' && isProblem(n)) return stateColor(n.state);
    if (n.kind === 'folder' && n.is_empty) return 'var(--text-muted)';
    return 'var(--border)';
}

function layoutFocus(): FNode | null {
    if (!dims.w || !dims.h) return null;
    const focusData = findNode(currentRoot(), focusPath) ?? currentRoot();
    breadcrumb.value = chainTo(currentRoot(), focusData.path);
    const h = hierarchy<FolderTreeNode>(focusData, (d) =>
        d.kind === 'folder' ? d.children : undefined,
    )
        .sum(leafValue)
        .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    return treemap<FolderTreeNode>()
        .tile(treemapSquarify.ratio(1))
        .size([dims.w, dims.h])
        .paddingOuter(3)
        .paddingTop((d) => (d.children ? HEADER : 0))
        .paddingInner(3)
        .round(true)(h);
}

function pathSig(node: FNode): string {
    return node
        .descendants()
        .map((d) => d.data.path)
        .join('|');
}

function setFocus(path: string): void {
    focusPath = path;
    draw(true);
}

function showTip(event: MouseEvent, d: FNode): void {
    if (!hostEl.value) return;
    const rect = hostEl.value.getBoundingClientRect();
    const n = d.data;
    const pills = severityPills(n.severity_counts);
    const breakdown = pills.length
        ? pills.map((p) => `${p.count} ${p.state}`).join(' · ')
        : 'all OK';
    const meta =
        n.kind === 'host'
            ? n.state
            : n.is_empty
              ? 'empty · 0 hosts'
              : `${n.host_count} hosts · ${breakdown}`;
    tip.value = {
        x: event.clientX - rect.left + 12,
        y: event.clientY - rect.top + 12,
        title: n.title,
        meta,
        color: n.is_empty ? 'var(--text-muted)' : stateColor(n.state),
    };
}

function draw(animate: boolean): void {
    if (!svgEl.value) return;
    const laid = layoutFocus();
    if (!laid) return;
    lastPathSig = pathSig(laid);
    const nodes = laid.descendants().slice(1); // skip the focus node (it is the canvas)
    empty.value = nodes.length === 0;

    const svg = select(svgEl.value)
        .attr('viewBox', `0 0 ${dims.w} ${dims.h}`)
        .on('click', () => {
            // Click on empty canvas zooms out one level.
            const parent = breadcrumb.value[breadcrumb.value.length - 2];
            if (parent) setFocus(parent.path);
        });
    let g = svg.select<SVGGElement>('g.ftm-cells');
    if (g.empty()) g = svg.append('g').attr('class', 'ftm-cells');

    const dur = animate ? 500 : 0;

    const cells = g
        .selectAll<SVGGElement, FNode>('g.ftm-cell')
        .data(nodes, (d) => d.data.path + ':' + d.data.kind);

    cells.exit().transition().duration(dur).style('opacity', 0).remove();

    const enter = cells
        .enter()
        .append('g')
        .attr('class', 'ftm-cell')
        .style('opacity', 0)
        .attr('transform', (d) => `translate(${d.x0},${d.y0})`);
    enter.append('rect');
    enter.append('text').attr('class', 'ftm-label');

    const merged = enter.merge(cells);
    merged
        .style('cursor', 'pointer')
        .on('click', (event: MouseEvent, d) => {
            event.stopPropagation();
            if (d.data.kind === 'host') emit('select-host', d.data);
            else setFocus(d.data.path);
        })
        .on('mousemove', showTip)
        .on('mouseleave', () => (tip.value = null));
    merged
        .transition()
        .duration(dur)
        .style('opacity', 1)
        .attr('transform', (d) => `translate(${d.x0},${d.y0})`);

    merged
        .select('rect')
        .attr('rx', 3)
        .attr('stroke-width', (d) => (d.data.kind === 'folder' && d.data.is_empty ? 1.4 : 1))
        .attr('stroke-dasharray', (d) =>
            d.data.kind === 'folder' && d.data.is_empty ? '4 3' : null,
        )
        .transition()
        .duration(dur)
        .attr('width', (d) => Math.max(0, d.x1 - d.x0))
        .attr('height', (d) => Math.max(0, d.y1 - d.y0))
        .attr('fill', fillFor)
        .attr('fill-opacity', fillOpacityFor)
        .attr('stroke', strokeFor);

    merged.select<SVGTextElement>('text').each(function (d) {
        const w = d.x1 - d.x0;
        const h = d.y1 - d.y0;
        const t = select(this);
        if (d.data.kind === 'folder') {
            // Title sits in the header bar.
            t.attr('x', 6)
                .attr('y', 13)
                .attr('text-anchor', 'start')
                .style('display', w > 26 ? 'inline' : 'none')
                .text(folderHeaderText(d.data));
        } else {
            // Host label centered, only when the tile is big enough.
            t.attr('x', w / 2)
                .attr('y', h / 2 + 4)
                .attr('text-anchor', 'middle')
                .style('display', w > 46 && h > 18 ? 'inline' : 'none')
                .text(d.data.title);
        }
    });
}

// Recolor without relayout when only states changed (same path set). Folder
// header text carries live severity counts, so refresh it here too.
function recolor(): void {
    if (!svgEl.value) return;
    const g = select(svgEl.value).select('g.ftm-cells');
    g.selectAll<SVGRectElement, FNode>('g.ftm-cell rect')
        .transition()
        .duration(400)
        .attr('fill', fillFor)
        .attr('fill-opacity', fillOpacityFor)
        .attr('stroke', strokeFor);
    g.selectAll<SVGTextElement, FNode>('g.ftm-cell text').text((d) =>
        d.data.kind === 'folder' ? folderHeaderText(d.data) : d.data.title,
    );
}

watch(
    [root, () => props.problemsOnly],
    () => {
        if (!root.value || !svgEl.value || !dims.w) return;
        const laid = layoutFocus();
        if (laid && pathSig(laid) === lastPathSig) recolor();
        else draw(true);
    },
    { flush: 'post' },
);

onMounted(() => {
    if (!hostEl.value) return;
    resizeObs = new ResizeObserver((entries) => {
        const r = entries[0].contentRect;
        const changed = Math.abs(r.width - dims.w) > 1 || Math.abs(r.height - dims.h) > 1;
        dims = { w: r.width, h: r.height };
        if (changed && root.value) draw(false);
    });
    resizeObs.observe(hostEl.value);
});

onUnmounted(() => {
    resizeObs?.disconnect();
    if (svgEl.value) select(svgEl.value).selectAll('*').interrupt();
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
    pointer-events: none;
    fill: var(--text);
    font-size: 12px;
    font-weight: 600;
    paint-order: stroke;
    stroke: var(--bg-glass);
    stroke-width: 2.5px;
    stroke-linejoin: round;
}

.ftm-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 13px;
    padding: 24px;
    text-align: center;
}

.ftm-placeholder--overlay {
    position: absolute;
    inset: 0;
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
