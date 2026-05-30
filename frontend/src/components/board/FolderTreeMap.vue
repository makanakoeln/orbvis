<template>
    <div class="ftm">
        <div v-if="!root" class="ftm-placeholder">Waiting for folder data…</div>
        <template v-else>
            <div class="ftm-bar">
                <span class="ftm-root">{{ rootTitle }}</span>
                <button type="button" class="ftm-btn" @click="expandAll">Expand all</button>
                <button type="button" class="ftm-btn" @click="collapseAll">Collapse all</button>
            </div>
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
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';

import { useStatesStore } from '@/stores/states';
import type { FolderTreeNode } from '@/types/api';
import { severityPills, stateColor, stateRank } from '@/utils/stateColors';

const props = defineProps<{ problemsOnly: boolean }>();
const emit = defineEmits<{ 'select-host': [FolderTreeNode] }>();

const states = useStatesStore();
const root = computed<FolderTreeNode | null>(() => states.folderTree);
const rootTitle = computed(() => currentRoot().title || 'Main');

const svgEl = ref<SVGSVGElement | null>(null);
const hostEl = ref<HTMLDivElement | null>(null);

type FNode = HierarchyRectangularNode<FolderTreeNode>;

const HEADER = 19; // expanded-folder title bar height
const PROBLEM = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN']);
const isProblem = (n: FolderTreeNode) => PROBLEM.has(n.state);

const tip = ref<{ x: number; y: number; title: string; meta: string; color: string } | null>(null);
const empty = ref(false);

// Folders start collapsed (shown as solid status tiles); the operator expands
// them in place, just like the List view. Path-keyed so it survives relayout.
const expanded = reactive(new Set<string>());

let lastSig = '';
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

// Layout node carries children only for the (always-open) root and explicitly
// expanded folders; everything else is a leaf tile.
const isExpanded = (d: FNode) => d.data.kind === 'folder' && (d.children?.length ?? 0) > 0;

function fillFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 'transparent';
    if (isExpanded(d)) return isProblem(n) ? stateColor(n.state) : 'var(--bg-surface)';
    return stateColor(n.state); // host or collapsed folder → solid status tile
}

function fillOpacityFor(d: FNode): number {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 1;
    if (isExpanded(d)) return isProblem(n) ? 0.12 : 0.04; // faint backdrop for children
    return isProblem(n) ? 1 : 0.4; // healthy tiles recede, problems dominate
}

function strokeFor(d: FNode): string {
    const n = d.data;
    if (n.kind === 'folder' && n.is_empty) return 'var(--text-muted)';
    if (isExpanded(d) && isProblem(n)) return stateColor(n.state);
    return 'var(--border)';
}

function folderLabel(n: FolderTreeNode): string {
    if (n.is_empty) return `${n.title} · empty`;
    const pills = severityPills(n.severity_counts);
    if (pills.length) return `${n.title} · ${pills[0].count} ${pills[0].state}`;
    return `${n.title} · ${n.host_count}`;
}

function allFolderPaths(node: FolderTreeNode, acc: string[] = []): string[] {
    if (node.kind === 'folder') {
        if (node.path) acc.push(node.path);
        node.children.forEach((c) => allFolderPaths(c, acc));
    }
    return acc;
}

function layout(): FNode | null {
    if (!dims.w || !dims.h) return null;
    const rootData = currentRoot();
    const isOpen = (d: FolderTreeNode) =>
        d.kind === 'folder' && d.children.length > 0 && (d === rootData || expanded.has(d.path));
    const h = hierarchy<FolderTreeNode>(rootData, (d) => (isOpen(d) ? d.children : undefined))
        // A collapsed folder is a leaf sized by its host count, so it stays
        // visible without expanding; hosts count 1; open folders sum their kids
        // (contribute 0 themselves).
        .sum((d) => (d.kind === 'host' ? 1 : isOpen(d) ? 0 : Math.max(d.host_count, 1)))
        // Worst severity first → problems cluster top-left; ties → bigger first.
        .sort(
            (a, b) =>
                stateRank(b.data.state) - stateRank(a.data.state) ||
                (b.value ?? 0) - (a.value ?? 0),
        );
    return treemap<FolderTreeNode>()
        .tile(treemapSquarify.ratio(1))
        .size([dims.w, dims.h])
        .paddingOuter(3)
        .paddingTop((d) => (d.children ? HEADER : 0))
        .paddingInner(3)
        .round(true)(h);
}

function visibleSig(node: FNode): string {
    return node
        .descendants()
        .map((d) => d.data.path)
        .join('|');
}

function toggleFolder(path: string): void {
    if (expanded.has(path)) expanded.delete(path);
    else expanded.add(path);
    draw(true);
}

function expandAll(): void {
    allFolderPaths(currentRoot()).forEach((p) => expanded.add(p));
    draw(true);
}

function collapseAll(): void {
    expanded.clear();
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
    const laid = layout();
    if (!laid) return;
    lastSig = visibleSig(laid);
    const nodes = laid.descendants().slice(1); // skip the root (it is the canvas)
    empty.value = nodes.length === 0;

    const svg = select(svgEl.value).attr('viewBox', `0 0 ${dims.w} ${dims.h}`);
    let g = svg.select<SVGGElement>('g.ftm-cells');
    if (g.empty()) g = svg.append('g').attr('class', 'ftm-cells');

    const dur = animate ? 450 : 0;

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
            else toggleFolder(d.data.path);
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
        if (isExpanded(d)) {
            // Expanded folder: title in the header bar.
            t.attr('x', 6)
                .attr('y', 13)
                .attr('text-anchor', 'start')
                .style('display', w > 26 ? 'inline' : 'none')
                .text(folderLabel(d.data));
        } else {
            // Host or collapsed folder: centered label.
            const label = d.data.kind === 'folder' ? folderLabel(d.data) : d.data.title;
            t.attr('x', w / 2)
                .attr('y', h / 2 + 4)
                .attr('text-anchor', 'middle')
                .style('display', w > 46 && h > 18 ? 'inline' : 'none')
                .text(label);
        }
    });
}

// Recolor without relayout when only states changed (same visible set). Labels
// carry live severity counts, so refresh their text too.
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
        d.data.kind === 'folder' ? folderLabel(d.data) : d.data.title,
    );
}

watch(
    [root, () => props.problemsOnly],
    () => {
        if (!root.value || !svgEl.value || !dims.w) return;
        const laid = layout();
        if (laid && visibleSig(laid) === lastSig) recolor();
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

.ftm-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    font-size: 12px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.ftm-root {
    font-weight: 600;
    color: var(--text);
    margin-right: 4px;
}

.ftm-btn {
    font-size: 12px;
    padding: 3px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
}

.ftm-btn:hover {
    background: var(--bg-hover);
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
