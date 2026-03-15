<template>
  <div class="absolute inset-0 bg-[var(--bg)]">
    <div v-if="loading" class="flex items-center justify-center h-full text-zinc-500 text-sm">Loading topology…</div>
    <div v-else-if="error" class="flex items-center justify-center h-full text-red-400 text-sm">{{ error }}</div>
    <svg v-else ref="svgEl" class="w-full h-full block" />

    <!-- Zoom controls -->
    <div v-if="!loading && !error" class="absolute bottom-4 left-4 z-10 flex flex-col overflow-hidden rounded-xl ring-1 ring-[var(--border)] shadow-xl shadow-black/40">
      <button @click="zoomIn" title="Zoom in"
        class="p-2 bg-[var(--bg-surface)]/90 backdrop-blur-md text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors border-b border-[var(--border)]">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </button>
      <button @click="fitView" title="Fit all"
        class="p-2 bg-[var(--bg-surface)]/90 backdrop-blur-md text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors border-b border-[var(--border)]">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" />
        </svg>
      </button>
      <button @click="zoomOut" title="Zoom out"
        class="p-2 bg-[var(--bg-surface)]/90 backdrop-blur-md text-zinc-400 hover:text-[var(--text)] hover:bg-[var(--bg-hover)] transition-colors">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
        </svg>
      </button>
    </div>

    <!-- Hover tooltip -->
    <Transition enter-from-class="opacity-0 scale-95 translate-y-1" enter-active-class="transition-all duration-150 ease-out origin-bottom"
      leave-to-class="opacity-0 scale-95 translate-y-1" leave-active-class="transition-all duration-100 ease-in origin-bottom">
      <div v-if="tooltip.visible"
        class="absolute z-50 pointer-events-none"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px', transform: 'translateX(8px)' }">
        <div class="bg-[var(--bg-glass)] backdrop-blur-md ring-1 ring-[var(--border)] shadow-2xl shadow-black/60 rounded-xl p-3.5 min-w-44 max-w-64">
          <!-- Header: service name + host -->
          <div class="flex items-start gap-2 mb-2">
            <span class="w-2 h-2 rounded-full mt-1 shrink-0" :style="{ background: tooltip.stateColor }" />
            <div class="min-w-0">
              <div class="font-semibold text-[var(--text)] text-sm leading-tight truncate">{{ tooltip.title }}</div>
              <div class="text-xs text-zinc-500 mt-0.5 truncate">{{ tooltip.hostName }}</div>
            </div>
          </div>
          <!-- State label -->
          <div class="text-xs font-semibold" :style="{ color: tooltip.stateColor }">{{ tooltip.state }}</div>
          <!-- Plugin output -->
          <div v-if="tooltip.output"
            class="text-xs text-zinc-500 mt-2 leading-snug line-clamp-3 break-words">
            {{ tooltip.output }}
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive, onMounted, onUnmounted } from 'vue'
import { select } from 'd3-selection'
import {
  forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceY,
  type SimulationNodeDatum, type SimulationLinkDatum,
} from 'd3-force'
import { zoom, zoomIdentity } from 'd3-zoom'
import { drag } from 'd3-drag'
import type { TopologyNode } from '@/types/api'
import { connectionsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

import 'd3-transition'

const props = defineProps<{ backendId: string; serviceLayout: 'off' | 'fan' | 'row' | 'orbit' }>()
const auth = useAuthStore()

const NODE_R = 18
const SVC_R_MAX = 11   // service node radius at low service count
const ORBIT_R_MIN = 80 // minimum orbit/fan radius

// Scale service node radius down when a host has many services
function svcR(N: number): number {
  if (N <= 6) return SVC_R_MAX
  if (N <= 12) return 9
  if (N <= 20) return 7
  return 6
}

// Scale orbit radius up so service circles don't overlap.
// Full circle circumference = 2π·R must fit N circles of diameter 2r+gap.
function orbitR(N: number): number {
  const r = svcR(N)
  return Math.max(ORBIT_R_MIN, Math.ceil(N * (r * 2 + 3) / (2 * Math.PI)))
}

// Show labels only when few enough services per host
function showSvcLabel(N: number): boolean { return N <= 10 }
const svgEl = ref<SVGSVGElement | null>(null)
const nodes = ref<TopologyNode[]>([])
const loading = ref(true)
const error = ref('')
const tooltip = reactive({ visible: false, x: 0, y: 0, title: '', hostName: '', output: '', state: '', stateColor: '' })
let timer: ReturnType<typeof setInterval> | null = null

// ---- Fetch ----
async function fetchTopology() {
  try {
    nodes.value = await connectionsApi.topology(props.backendId, auth.accessToken!, props.serviceLayout !== 'off')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load topology'
  } finally {
    loading.value = false
  }
}

// Re-fetch and clear service cache when serviceLayout prop changes
watch(() => props.serviceLayout, () => {
  for (const k of nodeCache.keys()) {
    if (k.includes('::')) nodeCache.delete(k)
  }
  fetchTopology()
})

onMounted(() => { fetchTopology(); timer = setInterval(fetchTopology, 15000) })
onUnmounted(() => {
  if (timer) clearInterval(timer)
  simulation?.stop()
  if (svgEl.value) select(svgEl.value).selectAll('*').remove()
})

// ---- Color ----
function stateColor(state: string): string {
  const map: Record<string, string> = {
    UP: '#22c55e', OK: '#22c55e',
    DOWN: '#ef4444', CRITICAL: '#ef4444',
    UNREACHABLE: '#f97316', UNKNOWN: '#f97316',
    WARNING: '#ffd000',
  }
  return map[state] ?? '#6b7280'
}

// ---- D3 force types ----
interface FNode extends SimulationNodeDatum {
  id: string
  state: string
  output: string
  bfsLevel: number
  nodeType: 'host' | 'service'
  hostId?: string
  svcTotalCount?: number  // total services for this host (set on service nodes for label visibility)
  // d3-force sets x/y/vx/vy
}
interface FLink extends SimulationLinkDatum<FNode> {
  source: FNode
  target: FNode
  sourceState: string
  isServiceLink: boolean
}

let simulation: ReturnType<typeof forceSimulation<FNode>> | null = null
let zoomBeh: ReturnType<typeof zoom<SVGSVGElement, unknown>> | null = null
let lastFNodes: FNode[] = []
let _hasFitOnce = false

// Reset auto-fit when switching boards
watch(() => props.backendId, () => { _hasFitOnce = false })

// Stable node map — keeps d3 positions across topology refreshes
const nodeCache = new Map<string, FNode>()

// ---- BFS level (loose — for forceY only) ----
function bfsLevels(topoNodes: TopologyNode[]): Map<string, number> {
  const nameSet = new Set(topoNodes.map(n => n.name))
  const levels = new Map<string, number>()
  const roots = topoNodes.filter(n => !n.parents.length || n.parents.every(p => !nameSet.has(p)))
  const queue: string[] = roots.map(r => r.name)
  roots.forEach(r => levels.set(r.name, 0))
  while (queue.length) {
    const name = queue.shift()!
    const lvl = levels.get(name)!
    for (const n of topoNodes) {
      if (n.parents.includes(name) && !levels.has(n.name)) {
        levels.set(n.name, lvl + 1)
        queue.push(n.name)
      }
    }
  }
  topoNodes.filter(n => !levels.has(n.name)).forEach(n => levels.set(n.name, levels.size))
  return levels
}

// ---- Zoom controls ----
function fitView() {
  const svg = svgEl.value
  if (!svg || !zoomBeh || !lastFNodes.length) return
  const W = svg.clientWidth || 900
  const H = svg.clientHeight || 600
  const PAD = 64
  const xs = lastFNodes.map(n => n.x ?? n.fx ?? 0)
  const ys = lastFNodes.map(n => n.y ?? n.fy ?? 0)
  const minX = Math.min(...xs) - NODE_R - PAD
  const maxX = Math.max(...xs) + NODE_R + PAD
  const minY = Math.min(...ys) - NODE_R - PAD
  const maxY = Math.max(...ys) + NODE_R + PAD
  const scale = Math.min(3, Math.max(0.15, Math.min(W / (maxX - minX), H / (maxY - minY))))
  const tx = W / 2 - scale * ((minX + maxX) / 2)
  const ty = H / 2 - scale * ((minY + maxY) / 2)
  select(svg).transition().duration(500)
    .call(zoomBeh.transform, zoomIdentity.translate(tx, ty).scale(scale))
}

function zoomIn() {
  if (!svgEl.value || !zoomBeh) return
  select(svgEl.value).transition().duration(200).call(zoomBeh.scaleBy, 1.4)
}

function zoomOut() {
  if (!svgEl.value || !zoomBeh) return
  select(svgEl.value).transition().duration(200).call(zoomBeh.scaleBy, 1 / 1.4)
}

// ---- D3 rendering ----
watch([nodes, svgEl], () => {
  const svg = svgEl.value
  if (!svg || !nodes.value.length) return
  render(svg, nodes.value)
}, { flush: 'post' })

function render(svg: SVGSVGElement, topoNodes: TopologyNode[]) {
  const el = select(svg)
  const W = svg.clientWidth || 900
  const H = svg.clientHeight || 600

  // --- Ensure static containers exist (created once) ---
  let gZoom = el.select<SVGGElement>('g.zoom-layer')
  if (gZoom.empty()) {
    gZoom = el.append('g').attr('class', 'zoom-layer')
    gZoom.append('g').attr('class', 'links')
    gZoom.append('g').attr('class', 'nodes')
  }

  // --- Zoom behaviour (attached once) ---
  if (!(el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached) {
    (el.node() as SVGSVGElement & { __zoom_attached?: boolean }).__zoom_attached = true
    zoomBeh = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 3])
      .on('zoom', (event) => {
        gZoom.attr('transform', event.transform)
      })
    el.call(zoomBeh)
    // Center immediately so nodes don't flash at top-left on first render
    el.call(zoomBeh.transform, zoomIdentity.translate(W / 2, H / 2))
  }

  // --- Build FNode list (reuse cached positions) ---
  const levels = bfsLevels(topoNodes)
  const maxLvl = Math.max(0, ...levels.values())
  // When services are visible, increase vertical spacing to fit orbit rings
  const maxSvcN = Math.max(0, ...[...(nodes.value ?? []).map(n => n.services?.length ?? 0)])
  const minVSpacing = props.serviceLayout !== 'off' && maxSvcN > 0
    ? orbitR(maxSvcN) * 2 + 50
    : 0
  const vSpacing = Math.max(minVSpacing, Math.min(130, (H * 0.8) / Math.max(1, maxLvl + 1)))

  // Host nodes first
  const fNodes: FNode[] = topoNodes.map(n => {
    const cached = nodeCache.get(n.name)
    const node: FNode = cached
      ? { ...cached, state: n.state, output: n.output, bfsLevel: levels.get(n.name) ?? 0, nodeType: 'host' }
      : { id: n.name, state: n.state, output: n.output, bfsLevel: levels.get(n.name) ?? 0, nodeType: 'host' }
    nodeCache.set(n.name, node)
    return node
  })

  // Service nodes appended after host nodes
  if (props.serviceLayout !== 'off') {
    for (const n of topoNodes) {
      if (!n.services) continue
      const hostLevel = levels.get(n.name) ?? 0
      const N = n.services.length
      for (const svc of n.services) {
        const svcId = `${n.name}::${svc.name}`
        const cached = nodeCache.get(svcId)
        const svcNode: FNode = cached
          ? { ...cached, state: svc.state, output: svc.output, bfsLevel: hostLevel, nodeType: 'service', hostId: n.name, svcTotalCount: N }
          : { id: svcId, state: svc.state, output: svc.output, bfsLevel: hostLevel, nodeType: 'service', hostId: n.name, svcTotalCount: N }
        nodeCache.set(svcId, svcNode)
        fNodes.push(svcNode)
      }
    }
  }

  // Remove stale cached nodes
  const activeIds = new Set(fNodes.map(n => n.id))
  for (const k of nodeCache.keys()) { if (!activeIds.has(k)) nodeCache.delete(k) }

  const nodeById = new Map(fNodes.map(n => [n.id, n]))

  const fLinks: FLink[] = []
  // Host-to-host links
  for (const n of topoNodes) {
    for (const p of n.parents) {
      const src = nodeById.get(p)
      const tgt = nodeById.get(n.name)
      if (src && tgt) fLinks.push({ source: src, target: tgt, sourceState: src.state, isServiceLink: false })
    }
  }
  // Host-to-service links
  if (props.serviceLayout !== 'off') {
    for (const n of topoNodes) {
      if (!n.services) continue
      const hostNode = nodeById.get(n.name)
      if (!hostNode) continue
      for (const svc of n.services) {
        const svcNode = nodeById.get(`${n.name}::${svc.name}`)
        if (svcNode) fLinks.push({ source: hostNode, target: svcNode, sourceState: hostNode.state, isServiceLink: true })
      }
    }
  }

  // Pre-compute service groups per host for fan layout
  const servicesByHost = new Map<string, FNode[]>()
  for (const n of fNodes) {
    if (n.nodeType === 'service' && n.hostId) {
      const arr = servicesByHost.get(n.hostId) ?? []
      arr.push(n)
      servicesByHost.set(n.hostId, arr)
    }
  }

  // Measured row spacings per host (populated after first DOM render)
  const rowSpacings = new Map<string, number>()

  // Service positioning
  function updateFanPositions() {
    for (const [hostId, services] of servicesByHost) {
      const host = nodeById.get(hostId)
      if (!host) continue
      const hx = host.x ?? 0
      const hy = host.y ?? 0
      const N = services.length
      const R = orbitR(N)

      if (props.serviceLayout === 'fan' && N <= 8) {
        // Small fan: semicircle below host, evenly spaced
        const spread = N > 1 ? Math.PI * 0.9 : 0
        services.forEach((svc, i) => {
          const angle = Math.PI / 2 + (N > 1 ? -spread / 2 + i * spread / (N - 1) : 0)
          svc.fx = hx + R * Math.cos(angle)
          svc.fy = hy + R * Math.sin(angle)
        })
      } else if (props.serviceLayout === 'fan' || props.serviceLayout === 'orbit') {
        // Full circle — fan auto-upgrades to orbit when N > 8 to avoid overlap
        services.forEach((svc, i) => {
          const angle = (2 * Math.PI * i) / N - Math.PI / 2
          svc.fx = hx + R * Math.cos(angle)
          svc.fy = hy + R * Math.sin(angle)
        })
      } else {
        // Row: compact grid with automatic wrapping
        const r = svcR(N)
        const cols = Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))))
        const measured = rowSpacings.get(hostId)
        const fallback = services.reduce((max, svc) => {
          const label = svc.id.split('::').at(-1) ?? svc.id
          return Math.max(max, label.length * 5.5 + 8)
        }, r * 2 + 14)
        const spacingX = measured ?? fallback
        const spacingY = r * 2 + (showSvcLabel(N) ? 26 : 6)
        const yOffset = NODE_R + r + 22
        services.forEach((svc, i) => {
          const col = i % cols
          const row = Math.floor(i / cols)
          svc.fx = hx + (col - (cols - 1) / 2) * spacingX
          svc.fy = hy + yOffset + row * spacingY
        })
      }
    }
  }
  updateFanPositions()
  lastFNodes = fNodes

  // --- Update simulation ---
  if (simulation) simulation.stop()

  const hostLinks = fLinks.filter(l => !l.isServiceLink)

  simulation = forceSimulation<FNode>(fNodes)
    .force('link', forceLink<FNode, FLink>(hostLinks).id(d => d.id)
      .distance(d => {
        // Space hosts far enough apart that their service rings don't overlap
        const srcN = servicesByHost.get((d.source as FNode).id)?.length ?? 0
        const tgtN = servicesByHost.get((d.target as FNode).id)?.length ?? 0
        if (srcN === 0 && tgtN === 0) return 160
        return Math.max(200, orbitR(srcN) + orbitR(tgtN) + 60)
      })
      .strength(0.4))
    .force('charge', forceManyBody<FNode>().strength(d => d.nodeType === 'service' ? 0 : -600))
    .force('center', forceCenter<FNode>(0, 0).strength(0.05))
    .force('collide', forceCollide<FNode>(d => {
      if (d.nodeType === 'service') return 0
      const svcs = servicesByHost.get(d.id) ?? []
      const N = svcs.length
      if (N === 0 || props.serviceLayout === 'off') return NODE_R + 10
      if (props.serviceLayout === 'fan' || props.serviceLayout === 'orbit') return orbitR(N) + svcR(N) + 10
      // Row grid
      const cols = Math.min(N, Math.max(4, Math.ceil(Math.sqrt(N * 1.5))))
      const spacingX = rowSpacings.get(d.id) ?? 60
      return (cols / 2) * spacingX + svcR(N) + 10
    }))
    .force('y', forceY<FNode>(d => (d.bfsLevel - maxLvl / 2) * vSpacing).strength(d => d.nodeType === 'service' ? 0 : 0.4))
    .alphaDecay(0.03)
    .stop()

  // --- Drag behaviour ---
  const dragBehavior = drag<SVGGElement, FNode>()
    .on('start', (event, d) => {
      if (!event.active) simulation!.alphaTarget(0.3).restart()
      d.fx = d.x; d.fy = d.y
    })
    .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
    .on('end', (event, d) => {
      if (!event.active) simulation!.alphaTarget(0)
      d.fx = d.x; d.fy = d.y
    })

  // --- Links ---
  const gLinks = gZoom.select<SVGGElement>('g.links')
  const linkSel = gLinks.selectAll<SVGLineElement, FLink>('line')
    .data(fLinks, d => `${(d.source as FNode).id}→${(d.target as FNode).id}`)
  linkSel.exit().remove()
  const linkEnter = linkSel.enter().append('line')
  const linkMerge = linkEnter.merge(linkSel)
    .attr('stroke', d => stateColor((d.source as FNode).state))
    .attr('stroke-opacity', d => d.isServiceLink ? 0.3 : 0.45)
    .attr('stroke-width', d => d.isServiceLink ? 1 : 1.5)
    .attr('stroke-dasharray', d => d.isServiceLink ? '3,3' : null)

  // --- Nodes ---
  const gNodes = gZoom.select<SVGGElement>('g.nodes')
  const nodeSel = gNodes.selectAll<SVGGElement, FNode>('g.node')
    .data(fNodes, d => d.id)
  nodeSel.exit().remove()

  const nodeEnter = nodeSel.enter().append('g')
    .attr('class', 'node')
    .attr('cursor', d => d.nodeType === 'host' ? 'grab' : 'default')
    .on('click', (_event, d) => { void d })
    .on('mouseenter', (event: MouseEvent, d) => {
      if (d.nodeType !== 'service') return
      const nodeRect = (event.currentTarget as SVGGElement).getBoundingClientRect()
      const parentRect = (event.currentTarget as Element).closest('.absolute')!.getBoundingClientRect()
      tooltip.visible = true
      tooltip.x = nodeRect.right - parentRect.left
      tooltip.y = nodeRect.top - parentRect.top
      tooltip.title = d.id.split('::')[1]
      tooltip.hostName = d.hostId ?? ''
      tooltip.output = d.output
      tooltip.state = d.state
      tooltip.stateColor = stateColor(d.state)
    })
    .on('mouseleave', () => { tooltip.visible = false })

  // Drag only on host nodes
  nodeEnter.filter(d => d.nodeType === 'host').call(dragBehavior as never)

  // Host nodes
  const hostEnter = nodeEnter.filter(d => d.nodeType === 'host')
  hostEnter.append('circle')
    .attr('r', NODE_R)
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1.5)
  hostEnter.append('text')
    .attr('class', 'type-char')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'rgba(255,255,255,0.9)')
    .attr('font-size', 11)
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .text('H')
  hostEnter.append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 11)
    .attr('font-weight', '500')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--text)')
    .attr('y', NODE_R + 5)

  // Service nodes
  const svcEnter = nodeEnter.filter(d => d.nodeType === 'service')
  svcEnter.append('circle')
    .attr('r', d => svcR(d.svcTotalCount ?? 1))
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1)
  svcEnter.append('text')
    .attr('class', 'type-char')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'rgba(255,255,255,0.9)')
    .attr('font-size', d => svcR(d.svcTotalCount ?? 1) <= 7 ? 6 : 8)
    .attr('font-weight', '700')
    .attr('pointer-events', 'none')
    .text('S')
  svcEnter.append('text')
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'hanging')
    .attr('font-size', 9)
    .attr('font-weight', '400')
    .attr('pointer-events', 'none')
    .style('fill', 'var(--text)')
    .attr('y', d => svcR(d.svcTotalCount ?? 1) + 4)
    .style('display', d => showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none')

  const nodeMerge = nodeEnter.merge(nodeSel)
  nodeMerge.select('circle').attr('fill', d => stateColor(d.state))
  nodeMerge.select('text.node-label').text(d => {
    if (d.nodeType === 'service') {
      const parts = d.id.split('::')
      return parts[parts.length - 1]
    }
    return d.id
  })
  // Refresh service label visibility — may change when switching layout or on re-render
  nodeMerge.filter(d => d.nodeType === 'service').select('text.node-label')
    .style('display', d => showSvcLabel(d.svcTotalCount ?? 1) ? null : 'none')

  // --- Tick handler ---
  function ticked() {
    updateFanPositions()
    linkMerge
      .attr('x1', d => (d.source as FNode).x!)
      .attr('y1', d => (d.source as FNode).y!)
      .attr('x2', d => (d.target as FNode).x!)
      .attr('y2', d => (d.target as FNode).y!)
      .attr('stroke', d => stateColor((d.source as FNode).state))

    nodeMerge
      .attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
      .select('circle')
      .attr('fill', d => stateColor(d.state))
  }

  // Pre-tick to near-settled positions, render once, fit immediately, then animate remainder
  simulation.tick(150)
  updateFanPositions()
  ticked()

  // For row layout: measure actual label widths from DOM, re-layout with exact spacing
  if (props.serviceLayout === 'row') {
    for (const [hostId, services] of servicesByHost) {
      const N = services.length
      if (!showSvcLabel(N)) {
        // No labels — use diameter + gap as spacing
        rowSpacings.set(hostId, svcR(N) * 2 + 6)
        continue
      }
      let maxW = 0
      for (const svc of services) {
        const g = gNodes.selectAll<SVGGElement, FNode>('g.node').filter(d => d.id === svc.id).node()
        const textEl = g?.querySelector<SVGTextElement>('text.node-label')
        if (textEl) maxW = Math.max(maxW, textEl.getComputedTextLength())
      }
      if (maxW > 0) rowSpacings.set(hostId, maxW + 10)
    }
    updateFanPositions()
    ticked()
  }

  if (!_hasFitOnce) { _hasFitOnce = true; fitView() }
  simulation.on('tick', ticked).restart()
}
</script>
