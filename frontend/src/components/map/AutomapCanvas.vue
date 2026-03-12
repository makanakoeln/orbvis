<template>
  <div class="absolute inset-0 bg-[var(--bg)]">
    <div v-if="loading" class="flex items-center justify-center h-full text-zinc-500 text-sm">Loading topology…</div>
    <div v-else-if="error" class="flex items-center justify-center h-full text-red-400 text-sm">{{ error }}</div>
    <svg v-else ref="svgEl" class="w-full h-full block" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { select } from 'd3-selection'
import {
  forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, forceY,
  type SimulationNodeDatum, type SimulationLinkDatum,
} from 'd3-force'
import { zoom, zoomIdentity } from 'd3-zoom'
import { drag } from 'd3-drag'
import type { TopologyNode } from '@/types/api'
import { backendsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

// d3-transition side-effect import not needed — no transitions on force nodes

const props = defineProps<{ backendId: string }>()
const auth = useAuthStore()

const NODE_R = 18
const svgEl = ref<SVGSVGElement | null>(null)
const nodes = ref<TopologyNode[]>([])
const loading = ref(true)
const error = ref('')
let timer: ReturnType<typeof setInterval> | null = null

// ---- Fetch ----
async function fetchTopology() {
  try {
    nodes.value = await backendsApi.topology(props.backendId, auth.accessToken!)
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Failed to load topology'
  } finally {
    loading.value = false
  }
}

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
    WARNING: '#f59e0b',
  }
  return map[state] ?? '#6b7280'
}

// ---- D3 force types ----
interface FNode extends SimulationNodeDatum {
  id: string
  state: string
  bfsLevel: number
  // d3-force sets x/y/vx/vy
}
interface FLink extends SimulationLinkDatum<FNode> {
  source: FNode
  target: FNode
  sourceState: string
}

let simulation: ReturnType<typeof forceSimulation<FNode>> | null = null
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
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 3])
      .on('zoom', (event) => {
        gZoom.attr('transform', event.transform)
      })
    el.call(zoomBehavior)
    // Initial centering after first tick settle
    setTimeout(() => {
      el.transition().duration(600)
        .call(zoomBehavior.transform, zoomIdentity.translate(W / 2, H / 2))
    }, 600)
  }

  // --- Build FNode list (reuse cached positions) ---
  const levels = bfsLevels(topoNodes)
  const maxLvl = Math.max(0, ...levels.values())
  const vSpacing = Math.min(130, (H * 0.8) / Math.max(1, maxLvl + 1))

  const fNodes: FNode[] = topoNodes.map(n => {
    const cached = nodeCache.get(n.name)
    const node: FNode = cached
      ? { ...cached, state: n.state, bfsLevel: levels.get(n.name) ?? 0 }
      : { id: n.name, state: n.state, bfsLevel: levels.get(n.name) ?? 0 }
    nodeCache.set(n.name, node)
    return node
  })
  // Remove stale cached nodes
  const nameSet = new Set(topoNodes.map(n => n.name))
  for (const k of nodeCache.keys()) { if (!nameSet.has(k)) nodeCache.delete(k) }

  const nodeById = new Map(fNodes.map(n => [n.id, n]))

  const fLinks: FLink[] = []
  for (const n of topoNodes) {
    for (const p of n.parents) {
      const src = nodeById.get(p)
      const tgt = nodeById.get(n.name)
      if (src && tgt) fLinks.push({ source: src, target: tgt, sourceState: src.state })
    }
  }

  // --- Update simulation ---
  if (simulation) simulation.stop()

  simulation = forceSimulation<FNode>(fNodes)
    .force('link', forceLink<FNode, FLink>(fLinks).id(d => d.id).distance(100).strength(0.5))
    .force('charge', forceManyBody<FNode>().strength(-350))
    .force('center', forceCenter<FNode>(0, 0).strength(0.05))
    .force('collide', forceCollide<FNode>(NODE_R + 20))
    .force('y', forceY<FNode>(d => (d.bfsLevel - maxLvl / 2) * vSpacing).strength(0.4))
    .alphaDecay(0.03)
    .on('tick', ticked)

  // --- Drag behaviour ---
  const dragBehavior = drag<SVGGElement, FNode>()
    .on('start', (event, d) => {
      if (!event.active) simulation!.alphaTarget(0.3).restart()
      d.fx = d.x; d.fy = d.y
    })
    .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
    .on('end', (event, d) => {
      if (!event.active) simulation!.alphaTarget(0)
      // Keep fx/fy set so the node stays where the user dropped it.
      // The nodeCache preserves these across topology refreshes.
      d.fx = d.x; d.fy = d.y
    })

  // --- Links ---
  const gLinks = gZoom.select<SVGGElement>('g.links')
  const linkSel = gLinks.selectAll<SVGLineElement, FLink>('line')
    .data(fLinks, d => `${(d.source as FNode).id}→${(d.target as FNode).id}`)
  linkSel.exit().remove()
  const linkEnter = linkSel.enter().append('line')
    .attr('stroke-opacity', 0.45)
    .attr('stroke-width', 1.5)
  const linkMerge = linkEnter.merge(linkSel)
    .attr('stroke', d => stateColor((d.source as FNode).state))

  // --- Nodes ---
  const gNodes = gZoom.select<SVGGElement>('g.nodes')
  const nodeSel = gNodes.selectAll<SVGGElement, FNode>('g.node')
    .data(fNodes, d => d.id)
  nodeSel.exit().remove()

  const nodeEnter = nodeSel.enter().append('g')
    .attr('class', 'node')
    .attr('cursor', 'grab')
    .call(dragBehavior as never)
    .on('click', (_event, d) => {
      // Future: open detail panel
      void d
    })

  nodeEnter.append('circle')
    .attr('r', NODE_R)
    .attr('stroke', 'rgba(0,0,0,0.4)')
    .attr('stroke-width', 1.5)

  nodeEnter.append('text')
    .attr('text-anchor', 'middle')
    .attr('dominant-baseline', 'central')
    .attr('fill', 'rgba(255,255,255,0.92)')
    .attr('font-size', 10)
    .attr('font-weight', '600')
    .attr('pointer-events', 'none')
    .attr('dy', NODE_R + 13)

  const nodeMerge = nodeEnter.merge(nodeSel)
  nodeMerge.select('circle').attr('fill', d => stateColor(d.state))
  nodeMerge.select('text').text(d => d.id)

  // --- Tick handler ---
  function ticked() {
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
}
</script>
