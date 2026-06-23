import type { ServiceLayout, TopologyNode } from '@/types/api'

import { fanR, finiteOr, orbitR, severityRank } from './flowGeometry'

// Structural subset of the Flow Map's FNode that the layout pre-pass needs —
// keeps this module free of a dependency on the d3 simulation types.
export interface LayoutNode {
  id: string
  topo?: TopologyNode | undefined
  x?: number | undefined
  y?: number | undefined
}

// Phyllotaxis (sunflower) layout: even-density spiral with no holes. Sorting
// by severity rank (desc) means hosts with the worst state get the inner
// slots, healthy hosts the outer. The combined effect is a compact disk
// whose center is dominated by problems and whose rim is mostly green —
// readable at a glance even on 500-host maps.
const PHYLLOTAXIS_ANGLE = Math.PI * (3 - Math.sqrt(5))
// Exported: the site-umbrella offset derives its disk radius from it.
export const SPIRAL_SPACING = 55

export function rankBySeverity<T extends LayoutNode>(hosts: T[]): T[] {
  return [...hosts].sort((a, b) => {
    const sa = severityRank(a.topo)
    const sb = severityRank(b.topo)
    if (sa !== sb) return sb - sa
    return a.id.localeCompare(b.id)
  })
}

export function preLayoutHosts(hosts: LayoutNode[]): void {
  if (!hosts.length) return
  rankBySeverity(hosts).forEach((d, i) => {
    const angle = i * PHYLLOTAXIS_ANGLE
    const r = SPIRAL_SPACING * Math.sqrt(i + 1)
    d.x = r * Math.cos(angle)
    d.y = r * Math.sin(angle)
  })
}

// Half-disk phyllotaxis below the site: mirror the negative-y points so the
// entire spiral lands in the lower half-plane. Hosts visually hang under
// their site root instead of orbiting around (0,0).
export function preLayoutHostsBelowSite(
  sitePos: { x: number; y: number },
  hosts: LayoutNode[],
  gap: number
): void {
  if (!hosts.length) return
  rankBySeverity(hosts).forEach((d, i) => {
    const angle = i * PHYLLOTAXIS_ANGLE
    const r = SPIRAL_SPACING * Math.sqrt(i + 1)
    d.x = sitePos.x + r * Math.cos(angle)
    d.y = sitePos.y + gap + Math.abs(r * Math.sin(angle))
  })
}

// Service-ring radius for the active layout.
export function layoutR(layout: ServiceLayout | null | undefined, N: number): number {
  return layout === 'fan' ? fanR(N) : orbitR(N)
}

// Layouts that need the full per-host service list. Donut renders only
// services_summary aggregates and therefore skips the bulk query entirely —
// that's the main scaling win for large installations.
export function needsServices(layout: ServiceLayout | null | undefined): boolean {
  return layout === 'fan' || layout === 'orbit' || layout === 'row'
}

// Site root box scales up at low zoom so the label stays legible. At fit-zoom
// (k≈0.25) the 110-px-wide rect would render as ~28px without this — too
// small to read. At full zoom the scale stays 1 (no inflation).
export function siteScaleForZoom(zoomK: number): number {
  const inv = 1 / Math.max(finiteOr(zoomK, 1), 0.0001)
  return Math.min(3.5, Math.max(1, inv))
}

// Loose BFS levels over the parent topology — feeds d3's forceY so layers
// roughly stack top-down. Hosts whose parents are all outside the visible
// set count as roots; unreachable leftovers sink to the bottom.
export function bfsLevels(topoNodes: TopologyNode[]): Map<string, number> {
  const nameSet = new Set(topoNodes.map((n) => n.name))
  const levels = new Map<string, number>()
  const roots = topoNodes.filter(
    (n) => !n.parents.length || n.parents.every((p) => !nameSet.has(p))
  )
  const queue: string[] = roots.map((r) => r.name)
  roots.forEach((r) => levels.set(r.name, 0))
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
  topoNodes.filter((n) => !levels.has(n.name)).forEach((n) => levels.set(n.name, levels.size))
  return levels
}
