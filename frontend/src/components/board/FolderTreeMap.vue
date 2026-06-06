<template>
  <div class="ftm">
    <div v-if="!root" class="ftm-placeholder">{{ _t('Waiting for folder data…') }}</div>
    <template v-else>
      <div ref="hostEl" class="ftm-stage">
        <svg ref="svgEl" class="ftm-svg" />
        <div
          v-if="tip"
          ref="tipEl"
          class="ftm-tip"
          :style="{ left: tip.x + 'px', top: tip.y + 'px' }"
        >
          <span class="ftm-tip-dot" :style="{ background: tip.color }" />
          <strong>{{ tip.title }}</strong>
          <span class="ftm-tip-meta">{{ tip.meta }}</span>
        </div>
        <div v-if="empty" class="ftm-placeholder ftm-placeholder--overlay">
          {{ _t('Nothing to show here.') }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import {
  type BaseType,
  type HierarchyRectangularNode,
  type Selection,
  hierarchy,
  select,
  treemap,
  treemapSquarify
} from 'd3'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'

import { useStatesStore } from '@/stores/states'
import type { FolderTreeNode } from '@/types/api'
import {
  type FilterTerm,
  isFilterActive,
  selfMatches,
  serviceVisible,
  subtreeVisible,
  visibleServices
} from '@/utils/folderTreeFilter'
import { severityPills, stateColorVar, stateRank } from '@/utils/stateColors'
import usei18n from '@/vendor/cmk/lib/i18n'

const props = defineProps<{
  query: FilterTerm[]
  problemsOnly: boolean
  showServices: boolean
  servicesByHost: Record<string, FolderTreeNode[]>
  serviceLoading: Set<string>
  serviceError: Set<string>
}>()
const { _t } = usei18n()
const emit = defineEmits<{
  'select-host': [FolderTreeNode]
  'select-service': [string, FolderTreeNode]
  'expand-host': [FolderTreeNode]
  'ctx-folder': [FolderTreeNode, number, number]
}>()

const states = useStatesStore()
const root = computed<FolderTreeNode | null>(() => states.folderTree)

const svgEl = ref<SVGSVGElement | null>(null)
const hostEl = ref<HTMLDivElement | null>(null)
const tipEl = ref<HTMLDivElement | null>(null)
// Faint container tints are calibrated for the dark canvas; over a light canvas
// the same low-opacity status colour washes out to a muddy pastel. Track the
// theme so the tints can adapt (lighter, cleaner backdrop in light mode — the
// coloured header + frame carry the status instead).
const isLight = ref(document.documentElement.classList.contains('light'))
let themeObs: MutationObserver | null = null

// ``culled``: open container whose children were all too small to resolve.
type FNode = HierarchyRectangularNode<FolderTreeNode> & { culled?: boolean }

const HEADER = 19 // expanded-folder title bar height
const PROBLEM = new Set(['DOWN', 'UNREACHABLE', 'CRITICAL', 'WARNING', 'UNKNOWN'])
const isProblem = (n: FolderTreeNode) => PROBLEM.has(n.state)

const tip = ref<{ x: number; y: number; title: string; meta: string; color: string } | null>(null)
const empty = ref(false)

// Folders start collapsed (shown as solid status tiles); the operator expands
// them in place, just like the List view. Path-keyed so it survives relayout.
const expanded = reactive(new Set<string>())

let lastSig = ''
let dims = { w: 0, h: 0 }
let resizeObs: ResizeObserver | null = null

// Prune the store tree to the active "Problems only" + search filter, building a
// trimmed copy. Mirrors the List (shared folderTreeFilter helpers). A host also
// survives when one of its already-loaded services matches, so a service search
// still surfaces the host to drill into (lazy services aren't in the store tree).
function pruneTree(node: FolderTreeNode, ancestorMatched: boolean): FolderTreeNode | null {
  const selfMatch = ancestorMatched || selfMatches(node, props.query)
  if (node.kind !== 'folder') {
    if (subtreeVisible(node, props.query, props.problemsOnly, ancestorMatched)) return node
    if (node.kind === 'host') {
      const svcMatch = (props.servicesByHost[node.title] ?? []).some((s) =>
        serviceVisible(node.title, s, props.query, props.problemsOnly, selfMatch)
      )
      if (svcMatch) return node
    }
    return null
  }
  const kids = node.children
    .map((c) => pruneTree(c, selfMatch))
    .filter((c): c is FolderTreeNode => c !== null)
  if (kids.length) return { ...node, children: kids }
  return subtreeVisible(node, props.query, props.problemsOnly, ancestorMatched)
    ? { ...node, children: [] }
    : null
}

function currentRoot(): FolderTreeNode {
  if (!root.value) return { path: '', title: '', kind: 'folder' } as FolderTreeNode
  if (!isFilterActive(props.query, props.problemsOnly)) return root.value
  return pruneTree(root.value, false) ?? { ...root.value, children: [] }
}

// A node the operator can drill into: a non-empty folder, or — when
// show_services is on — a host (drills to its lazily-loaded services).
const canExpand = (n: FolderTreeNode): boolean =>
  n.kind === 'folder' ? !n.is_empty : n.kind === 'host' && props.showServices
// Mirror the List's filtering of service leaves so both views show the same set
// (pruneTree only covers folders/hosts in the store tree).
const hostServices = (n: FolderTreeNode): FolderTreeNode[] => {
  return visibleServices(
    n.title,
    props.servicesByHost[n.title] ?? [],
    props.query,
    props.problemsOnly,
    selfMatches(n, props.query)
  )
}

// Laid-out node that actually has children rendered inside it (folder or host
// expanded to its services).
const isExpanded = (d: FNode) => (d.children?.length ?? 0) > 0 && !d.culled

// Visual language: containers (folders, expanded hosts) read as faint framed
// cards with a header tab; leaves (collapsed hosts, services) read as solid
// status chips. So a collapsed folder never looks like a host (the recurring
// confusion) — folders are always framed, hosts/services are always solid.
const isContainerCell = (d: FNode): boolean =>
  (d.data.kind === 'folder' && !d.data.is_empty) || (d.data.kind === 'host' && isExpanded(d))

function fillFor(d: FNode): string {
  const n = d.data
  if (n.kind === 'folder' && n.is_empty) return 'transparent'
  // Both containers and leaf chips are tinted by their (worst) state — the
  // folder's overall status colour must match the List's dot (green when OK,
  // red when critical). Containers stay faint via opacity; chips are solid.
  return stateColorVar(n.state)
}

function fillOpacityFor(d: FNode): number {
  const n = d.data
  if (n.kind === 'folder' && n.is_empty) return 1
  if (isContainerCell(d)) {
    // Light canvas: keep the backdrop barely tinted (a clean near-white card)
    // so it doesn't turn into a muddy pastel; the coloured header + frame
    // carry the status. Dark canvas: a slightly stronger tint reads well.
    if (isLight.value) return isProblem(n) ? 0.1 : 0.05
    return isProblem(n) ? 0.16 : 0.09
  }
  return isProblem(n) ? 1 : 0.4 // healthy chips recede, problems dominate
}

function strokeFor(d: FNode): string {
  const n = d.data
  if (n.kind === 'folder' && n.is_empty) return 'var(--text-muted)'
  // Container frame always reflects the (worst) state so the folder status
  // colour reads correctly; problems additionally thicken the frame.
  if (isContainerCell(d)) return stateColorVar(n.state)
  return 'var(--border)'
}

// Header band is tinted by the container's worst state so the folder's overall
// status reads at a glance (red header = critical folder, green = healthy);
// problems get a stronger tint, healthy a soft one — the label's halo keeps it
// legible on either.
function headerOpacityFor(d: FNode): number {
  return isProblem(d.data) ? 0.7 : 0.38
}

function strokeWidthFor(d: FNode): number {
  const n = d.data
  if (n.kind === 'folder' && n.is_empty) return 1.4
  if (isContainerCell(d) && isProblem(n)) return 2 // colored frame on a problem container
  return 1
}

function folderLabel(n: FolderTreeNode): string {
  if (n.ok_group) return n.title // already "✓ N OK"
  const title = n.title || 'Main'
  if (n.is_empty) return `${title} · empty`
  const pill = severityPills(n.severity_counts)[0]
  if (pill) return `${title} · ${pill.count} ${pill.state}`
  return `${title} · ${n.host_count}`
}

// Bundle a folder's healthy leaf hosts into one collapsible "✓ N OK" container
// so problems dominate the treemap (Datadog/Tactical-Overview style). Skipped
// under problems-only (healthy already hidden) and for <2 healthy hosts.
const OK_GROUP_SUFFIX = '::ok-group'
function aggregatedChildren(folder: FolderTreeNode): FolderTreeNode[] {
  // During a text search, healthy matches must stay individually visible (with
  // their names) instead of collapsing into a "✓ N OK" tile that hides them.
  if (folder.ok_group || props.problemsOnly || props.query.length > 0) return folder.children
  const isHealthyHost = (c: FolderTreeNode) => c.kind === 'host' && !isProblem(c)
  const healthy = folder.children.filter(isHealthyHost)
  if (healthy.length < 2) return folder.children
  const group: FolderTreeNode = {
    path: folder.path + OK_GROUP_SUFFIX,
    title: `✓ ${healthy.length} OK`,
    kind: 'folder',
    state: 'OK',
    is_empty: false,
    folder_id: '',
    host_count: healthy.length,
    problem_count: 0,
    severity_counts: {},
    output: '',
    acknowledged: false,
    in_downtime: false,
    site_id: null,
    children: healthy,
    ok_group: true
  }
  return [...folder.children.filter((c) => !isHealthyHost(c)), group]
}

// A container cell shows a header band with a chevron + label. Folders are
// framed even when collapsed; a host only grows a header once expanded (its
// collapsed form stays a chip, with a chevron prefix to signal it can expand).
const hasHeader = (d: FNode) => isContainerCell(d)

function labelText(d: FNode): string {
  const n = d.data
  if (hasHeader(d)) {
    const chev = isExpanded(d) ? '▾ ' : '▸ '
    return n.kind === 'folder' ? `${chev}${folderLabel(n)}` : `${chev}${n.title}`
  }
  if (n.kind === 'folder') return folderLabel(n) // empty folder
  // Collapsed host that can drill into services → chevron hints expandability;
  // show a loading ellipsis while its lazy services are being fetched.
  if (n.kind === 'host' && canExpand(n)) {
    return `▸ ${n.title}${props.serviceLoading.has(n.title) ? ' …' : ''}`
  }
  return n.title // plain host or service chip
}

// Approx glyph advance at 12px/600 — used to clip labels to their tile so long
// service names ellipsize instead of bleeding out of the box (full name on hover).
const CHAR_W = 7
function fitLabel(text: string, width: number): string {
  const max = Math.floor((width - 12) / CHAR_W)
  if (max <= 1) return ''
  if (text.length <= max) return text
  return text.slice(0, Math.max(1, max - 1)).trimEnd() + '…'
}

// Command-state badges shown in a tile corner (text, not glyphs — a check mark
// reads as "OK"; mirrors the List's ACK/DT/FLAP). A failed lazy service fetch
// surfaces as "!" so the host doesn't just sit there silently.
function markText(n: FolderTreeNode): string {
  const t: string[] = []
  if (n.acknowledged) t.push('ACK')
  if (n.in_downtime) t.push('DT')
  if (n.is_flapping) t.push('FLAP')
  if (n.kind === 'host' && props.serviceError.has(n.title)) t.push('!')
  return t.join(' ')
}

function allFolderPaths(node: FolderTreeNode, acc: string[] = []): string[] {
  if (node.kind === 'folder') {
    if (node.path) acc.push(node.path)
    node.children.forEach((c) => allFolderPaths(c, acc))
  }
  return acc
}

function layout(): FNode | null {
  if (!dims.w || !dims.h) return null
  const rootData = currentRoot()
  // While a text search is active, currentRoot() is already pruned to the paths
  // leading to matches, so auto-open every folder on the way down — the matching
  // host/service surfaces directly instead of hiding inside a collapsed tile
  // (file-explorer search behavior). The operator's manual expand state is left
  // untouched and takes back over once the search is cleared. Problems-only
  // alone keeps the collapsed overview (it's a whole-tree filter, not a lookup).
  const searchActive = props.query.length > 0
  // A host is "open" only once its services have actually loaded — until then
  // it stays a chip (and the click that opened it triggered the lazy fetch).
  const isOpen = (d: FolderTreeNode) => {
    if (d.kind === 'folder') return d.children.length > 0 && (searchActive || expanded.has(d.path))
    if (d.kind === 'host') {
      if (!props.showServices || hostServices(d).length === 0) return false
      // A host that only survived the search via a matching service auto-opens
      // to reveal it; a host matched by its own name stays a chip.
      if (searchActive && !selfMatches(d, props.query)) return true
      return expanded.has(d.path)
    }
    return false
  }
  const childrenOf = (d: FolderTreeNode) =>
    d.kind === 'host' ? hostServices(d) : aggregatedChildren(d)
  const h = hierarchy<FolderTreeNode>(rootData, (d) => (isOpen(d) ? childrenOf(d) : undefined))
    // Tile weights: a folder reads as a slightly larger card than a single
    // host (container vs. leaf) without host-count dwarfing the map; empty
    // folders smallest; services size like hosts; the "✓ N OK" group stays
    // host-sized so it doesn't dominate. Open nodes contribute 0 and grow.
    .sum((d) =>
      d.kind === 'service'
        ? 1
        : d.kind === 'host' || d.ok_group
          ? isOpen(d)
            ? 0
            : 1
          : isOpen(d)
            ? 0
            : d.is_empty
              ? 0.5
              : 2
    )
    // Mirror the list order: a folder's own hosts before its subfolders,
    // then worst severity first (problems cluster top-left), then bigger.
    // The OK group counts as a host (healthy → sinks below problem hosts).
    .sort(
      (a, b) =>
        (a.data.kind === 'folder' && !a.data.ok_group ? 1 : 0) -
          (b.data.kind === 'folder' && !b.data.ok_group ? 1 : 0) ||
        stateRank(b.data.state) - stateRank(a.data.state) ||
        (b.value ?? 0) - (a.value ?? 0)
    )
  return treemap<FolderTreeNode>()
    .tile(treemapSquarify.ratio(1))
    .size([dims.w, dims.h])
    .paddingOuter(3)
    .paddingTop((d) => (d.children ? HEADER : 0))
    .paddingInner(3)
    .round(true)(h)
}

// Cells smaller than this (px, either side) aren't legible/clickable, so neither
// they nor their subtree are bound into the DOM — caps SVG nodes at the visible
// area, not the host count (a 100k-host folder is one tile, not 100k rects).
const MIN_RESOLVE = 24
// Drop child tiles too small to resolve; a container whose children all fail
// folds to an aggregate tile (``culled``), the rest blend into its body.
function visibleNodes(laid: FNode): FNode[] {
  const out: FNode[] = []
  const walk = (d: FNode) => {
    out.push(d)
    const kids = d.children
    if (!kids?.length) return
    const fit = kids.filter((c) => c.x1 - c.x0 >= MIN_RESOLVE && c.y1 - c.y0 >= MIN_RESOLVE)
    d.culled = fit.length === 0
    if (d.culled) return
    fit.forEach(walk)
  }
  walk(laid)
  return out
}

function sigOf(nodes: FNode[]): string {
  return nodes.map((d) => d.data.path).join('|')
}

function toggleFolder(path: string): void {
  if (expanded.has(path)) expanded.delete(path)
  else expanded.add(path)
  draw(true)
}

function expandAll(): void {
  const r = currentRoot()
  expanded.add(r.path)
  allFolderPaths(r).forEach((p) => expanded.add(p))
  draw(true)
}

function collapseAll(): void {
  // Keep Main open so the result is the top-level overview, not a single tile.
  expanded.clear()
  expanded.add(currentRoot().path)
  draw(true)
}

function showTip(event: MouseEvent, d: FNode): void {
  if (!hostEl.value) return
  const rect = hostEl.value.getBoundingClientRect()
  const n = d.data
  const pills = severityPills(n.severity_counts)
  const breakdown = pills.length ? pills.map((p) => `${p.count} ${p.state}`).join(' · ') : 'all OK'
  const flags = [
    n.acknowledged ? 'ACK' : '',
    n.in_downtime ? 'DOWNTIME' : '',
    n.is_flapping ? 'FLAPPING' : ''
  ]
    .filter(Boolean)
    .join(' · ')
  // Make the click outcome predictable (the same host tile expands when
  // show_services is on, opens the drawer otherwise).
  let hint = ''
  if (n.kind === 'host') {
    hint = canExpand(n)
      ? props.serviceError.has(n.title)
        ? 'services failed to load — click to retry'
        : props.serviceLoading.has(n.title)
          ? 'loading services…'
          : 'click: show services'
      : 'click: details'
  } else if (n.kind === 'service') {
    hint = 'click: details'
  } else if (canExpand(n)) {
    hint = isExpanded(d) ? 'click: collapse' : 'click: expand'
  }
  const base =
    n.kind === 'host' || n.kind === 'service'
      ? n.state
      : n.is_empty
        ? 'empty · 0 hosts'
        : `${n.host_count} hosts · ${breakdown}`
  const meta = [base, flags, hint].filter(Boolean).join(' · ')
  tip.value = {
    x: event.clientX - rect.left + 12,
    y: event.clientY - rect.top + 12,
    title: n.title,
    meta,
    color: n.is_empty ? 'var(--text-muted)' : stateColorVar(n.state)
  }
}

// Keep the hover tooltip inside the stage: once rendered we know its real size
// (it is white-space:nowrap, so it can be wide), so flip it to the other side of
// the cursor when it would overflow the right/bottom edge. flush:'post' runs
// after the DOM patch, so tipEl reflects the current content.
watch(
  tip,
  () => {
    const el = tipEl.value
    if (!tip.value || !el || !dims.w || !dims.h) return
    const w = el.offsetWidth
    const h = el.offsetHeight
    let x = tip.value.x
    let y = tip.value.y
    if (x + w + 4 > dims.w) x = Math.max(4, x - w - 24) // flip left of cursor
    if (y + h + 4 > dims.h) y = Math.max(4, y - h - 24) // flip above cursor
    el.style.left = `${x}px`
    el.style.top = `${y}px`
  },
  { flush: 'post' }
)

function activateCell(d: FNode): void {
  const n = d.data
  if (canExpand(n)) {
    if (n.kind === 'host') {
      if (expanded.has(n.path)) {
        expanded.delete(n.path)
        draw(true)
      } else {
        expanded.add(n.path)
        emit('expand-host', n)
        // First expand: services arrive async — let the servicesByHost
        // watch drive the single relayout, exactly like a reopen. Drawing
        // a transient "no services" frame here adds a second draw whose
        // service-tile entrance transition gets clobbered, leaving tiles
        // frozen at width 0 until the host is reopened. Cached → draw now.
        if (hostServices(n).length > 0) draw(true)
      }
    } else {
      toggleFolder(n.path)
    }
  } else if (n.kind === 'host') {
    emit('select-host', n)
  } else if (n.kind === 'service') {
    emit('select-service', d.parent?.data.title ?? '', n)
  }
}

// Spoken label for a tile (screen readers): name + state/host-count.
function cellAria(d: FNode): string {
  const n = d.data
  if (n.kind === 'folder' && n.is_empty) return `${n.title}, empty`
  if (n.kind === 'folder') {
    const pills = severityPills(n.severity_counts)
    const breakdown = pills.length ? pills.map((p) => `${p.count} ${p.state}`).join(', ') : 'OK'
    return `${n.title}, ${n.host_count} hosts, ${breakdown}`
  }
  return `${n.title}, ${n.state}`
}

function draw(animate: boolean, pre?: { laid: FNode; nodes: FNode[] }): void {
  if (!svgEl.value) return
  // Render the Main root too — as an outer container with a "Main" header — so
  // it is clear that the loose top-level host tiles are Main's direct hosts.
  const laid = pre?.laid ?? layout()
  if (!laid) return
  const nodes = pre?.nodes ?? visibleNodes(laid)
  lastSig = sigOf(nodes)
  // "Empty" = the data root truly has no folders/hosts — NOT merely a collapsed
  // Main (whose layout node then has no children). Otherwise the overlay would
  // cover the single Main tile and swallow the click that re-expands it.
  empty.value = currentRoot().children.length === 0

  const svg = select(svgEl.value).attr('viewBox', `0 0 ${dims.w} ${dims.h}`)
  let g = svg.select<SVGGElement>('g.ftm-cells')
  if (g.empty()) g = svg.append('g').attr('class', 'ftm-cells')

  const dur = animate ? 450 : 0

  const cells = g
    .selectAll<SVGGElement, FNode>('g.ftm-cell')
    .data(nodes, (d) => d.data.path + ':' + d.data.kind)

  // Named transition so a concurrent recolor() (e.g. a live SSE tick landing
  // mid-animation) can't interrupt this geometry/layout transition — an
  // unnamed clash froze freshly-expanded service tiles at width 0 on first open.
  cells.exit().transition('layout').duration(dur).style('opacity', 0).remove()

  const enter = cells
    .enter()
    .append('g')
    .attr('class', 'ftm-cell')
    .style('opacity', 0)
    .attr('transform', (d) => `translate(${d.x0},${d.y0})`)
  enter.append('rect').attr('class', 'ftm-body')
  enter.append('rect').attr('class', 'ftm-hdr')
  enter.append('text').attr('class', 'ftm-label')
  enter.append('text').attr('class', 'ftm-mark')

  const merged = enter.merge(cells)
  merged
    .style('cursor', 'pointer')
    // Keyboard-operable: each tile is a focusable button with a spoken label,
    // Enter/Space activates it (the Map can be the default view, so it must
    // not be mouse-only). The List already exposes ARIA tree roles.
    .attr('tabindex', 0)
    .attr('role', 'button')
    .attr('aria-label', cellAria)
    .on('click', (event: MouseEvent, d) => {
      event.stopPropagation()
      activateCell(d)
    })
    .on('keydown', (event: KeyboardEvent, d) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        event.stopPropagation()
        activateCell(d)
      }
    })
    .on('contextmenu', (event: MouseEvent, d) => {
      // Real folders only — the synthetic "✓ N OK" group has no bulk target.
      if (d.data.kind !== 'folder' || d.data.ok_group) return
      event.preventDefault()
      event.stopPropagation()
      emit('ctx-folder', d.data, event.clientX, event.clientY)
    })
    .on('mousemove', showTip)
    .on('mouseleave', () => (tip.value = null))
  merged
    .transition('layout')
    .duration(dur)
    .style('opacity', 1)
    .attr('transform', (d) => `translate(${d.x0},${d.y0})`)

  merged
    .select('rect.ftm-body')
    .attr('rx', 3)
    .attr('stroke-width', strokeWidthFor)
    .attr('stroke-dasharray', (d) => (d.data.kind === 'folder' && d.data.is_empty ? '4 3' : null))
    // fill/stroke via CSS style so the CMK `var(--color-state-*)` resolve
    // (SVG presentation attributes can't); geometry/opacity still animate.
    .style('fill', fillFor)
    .style('stroke', strokeFor)
    .transition('layout')
    .duration(dur)
    .attr('width', (d) => Math.max(0, d.x1 - d.x0))
    .attr('height', (d) => Math.max(0, d.y1 - d.y0))
    .attr('fill-opacity', fillOpacityFor)

  // Folder header band — a status-colored "tab" carrying the title; hidden for
  // host/service chips and empty folders.
  merged
    .select('rect.ftm-hdr')
    .attr('rx', 3)
    .style('fill', (d) => stateColorVar(d.data.state))
    .style('display', (d) => (hasHeader(d) ? null : 'none'))
    .transition('layout')
    .duration(dur)
    .attr('width', (d) => Math.max(0, d.x1 - d.x0))
    .attr('height', (d) => Math.min(HEADER, Math.max(0, d.y1 - d.y0)))
    .attr('fill-opacity', headerOpacityFor)

  paintLabels(merged)
}

// Label + command-state marker rendering, shared by draw() and recolor() so a
// recolor pass doesn't clobber the marker text or drop label truncation.
function paintLabels(sel: Selection<SVGGElement, FNode, BaseType, unknown>): void {
  sel.attr('aria-label', cellAria) // keep the spoken label in sync on recolor
  sel.select<SVGTextElement>('text.ftm-label').each(function (d) {
    const w = d.x1 - d.x0
    const h = d.y1 - d.y0
    const t = select(this)
    if (hasHeader(d)) {
      // Folder/expanded host: label sits in the header band next to the chevron.
      t.text(fitLabel(labelText(d), w))
        .attr('x', 6)
        .attr('y', 13)
        .attr('text-anchor', 'start')
        .style('display', w > 30 ? 'inline' : 'none')
    } else {
      // Host or service chip: centered, clipped to the tile so it never
      // overflows the box (full name available via the hover tooltip).
      t.text(fitLabel(labelText(d), w))
        .attr('x', w / 2)
        .attr('y', h / 2 + 4)
        .attr('text-anchor', 'middle')
        .style('display', w > 34 && h > 18 ? 'inline' : 'none')
    }
  })
  sel.select<SVGTextElement>('text.ftm-mark').each(function (d) {
    const w = d.x1 - d.x0
    const h = d.y1 - d.y0
    const m = markText(d.data)
    select(this)
      .text(m)
      .attr('x', w - 4)
      .attr('y', 13)
      .attr('text-anchor', 'end')
      .style('display', m && w > 28 && h > 16 ? 'inline' : 'none')
  })
}

// Recolor without relayout when only states changed (same visible set). Labels
// carry live severity counts, so refresh their text too. The freshly-laid nodes
// are rebound (same keys → pure update) so a filtered tree — whose currentRoot()
// hands out pruneTree *copies* — recolors off the current data, not last draw's.
function recolor(nodes: FNode[]): void {
  if (!svgEl.value) return
  const cells = select(svgEl.value)
    .select('g.ftm-cells')
    .selectAll<SVGGElement, FNode>('g.ftm-cell')
    .data(nodes, (d) => d.data.path + ':' + d.data.kind)
  // Distinct transition name from draw()'s 'layout' so a recolor (state change
  // or live tick) only animates fill — never cancels an in-flight geometry
  // transition (which would freeze tiles mid-resize).
  cells
    .select<SVGRectElement>('rect.ftm-body')
    .style('fill', fillFor)
    .style('stroke', strokeFor)
    .transition('recolor')
    .duration(400)
    .attr('fill-opacity', fillOpacityFor)
  cells
    .select<SVGRectElement>('rect.ftm-hdr')
    .style('fill', (d) => stateColorVar(d.data.state))
    .transition('recolor')
    .duration(400)
    .attr('fill-opacity', headerOpacityFor)
  paintLabels(cells)
}

// Open the Main root by default (once per root identity), but leave it
// collapsible — the operator can fold the whole tree into a single Main tile.
let seededFor = ''
watch(
  root,
  (r) => {
    if (!r) return
    const sig = r.path + '|' + r.children.length
    if (sig === seededFor) return
    seededFor = sig
    expanded.add(currentRoot().path)
  },
  { immediate: true }
)

// Re-lay out (or just recolor when the visible set is unchanged) on any input
// that affects the treemap: live tree, problems-only toggle, or lazily-loaded
// host services arriving / changing state (a freshly expanded host grows into
// its service tiles).
function relayout(): void {
  if (!root.value || !svgEl.value || !dims.w) return
  const laid = layout()
  if (!laid) return
  const nodes = visibleNodes(laid)
  if (sigOf(nodes) === lastSig) recolor(nodes)
  else draw(true, { laid, nodes })
}

watch(
  [
    root,
    () => states.folderTreeVersion,
    () => props.problemsOnly,
    () => props.query.map((t) => `${t.field}:${t.needle}`).join('|'),
    () =>
      Object.entries(props.servicesByHost)
        .map(
          ([h, svcs]) =>
            `${h}:${svcs.length}:${svcs
              .map((s) => s.state + (s.acknowledged ? 'a' : '') + (s.in_downtime ? 'd' : ''))
              .join(',')}`
        )
        .join('|'),
    // Loading/error of lazily-fetched services → refresh the host label
    // ("…") and the "!" marker even though the visible set is unchanged.
    () => `${[...props.serviceLoading].join(',')}|${[...props.serviceError].join(',')}`
  ],
  relayout,
  { flush: 'post' }
)

onMounted(() => {
  if (!hostEl.value) return
  resizeObs = new ResizeObserver((entries) => {
    const entry = entries[0]
    if (!entry) return
    const r = entry.contentRect
    const changed = Math.abs(r.width - dims.w) > 1 || Math.abs(r.height - dims.h) > 1
    dims = { w: r.width, h: r.height }
    if (changed && root.value) draw(false)
  })
  resizeObs.observe(hostEl.value)

  // Re-tint when the user flips theme (the html `light`/`dark` class toggles).
  themeObs = new MutationObserver(() => {
    const light = document.documentElement.classList.contains('light')
    if (light !== isLight.value) {
      isLight.value = light
      if (root.value) draw(false)
    }
  })
  themeObs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})

onUnmounted(() => {
  resizeObs?.disconnect()
  themeObs?.disconnect()
  if (svgEl.value) select(svgEl.value).selectAll('*').interrupt()
})

// Expand/Collapse all are driven from the board's floating control cluster.
defineExpose({ expandAll, collapseAll })
</script>

<style scoped>
.ftm {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
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

.ftm-svg :deep(.ftm-cell:focus-visible) {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
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

.ftm-svg :deep(.ftm-mark) {
  pointer-events: none;
  fill: var(--text);
  font-size: 11px;
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
  pointer-events: none; /* never swallow clicks on the tiles beneath */
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
