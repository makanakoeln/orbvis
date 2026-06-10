import { describe, expect, it } from 'vitest'

import type { TopologyNode } from '@/types/api'

import {
  type LayoutNode,
  bfsLevels,
  layoutR,
  needsServices,
  preLayoutHosts,
  preLayoutHostsBelowSite,
  rankBySeverity,
  siteScaleForZoom
} from './flowLayout'

function topo(name: string, state = 'UP', parents: string[] = []): TopologyNode {
  return { name, parents, state, output: '', services: [] } as unknown as TopologyNode
}

function host(id: string, state = 'UP'): LayoutNode {
  return { id, topo: topo(id, state) }
}

describe('rankBySeverity', () => {
  it('puts worst states first, ties broken alphabetically', () => {
    const ranked = rankBySeverity([
      host('zeta', 'UP'),
      host('alpha', 'UP'),
      host('down-host', 'DOWN'),
      host('warn-host', 'WARNING')
    ])
    expect(ranked.map((h) => h.id)).toEqual(['down-host', 'warn-host', 'alpha', 'zeta'])
  })

  it('does not mutate the input array', () => {
    const input = [host('b', 'UP'), host('a', 'DOWN')]
    rankBySeverity(input)
    expect(input.map((h) => h.id)).toEqual(['b', 'a'])
  })
})

describe('preLayoutHosts', () => {
  it('places the worst host nearest the center of the spiral', () => {
    const hosts = [host('healthy-1'), host('healthy-2'), host('crit', 'DOWN')]
    preLayoutHosts(hosts)
    const dist = (h: LayoutNode) => Math.hypot(h.x ?? 0, h.y ?? 0)
    const crit = hosts.find((h) => h.id === 'crit')!
    for (const h of hosts) {
      if (h !== crit) expect(dist(crit)).toBeLessThan(dist(h))
    }
  })

  it('assigns distinct positions (no pixel-perfect overlap)', () => {
    const hosts = Array.from({ length: 50 }, (_, i) => host(`h${i}`))
    preLayoutHosts(hosts)
    const keys = new Set(hosts.map((h) => `${Math.round(h.x!)}:${Math.round(h.y!)}`))
    expect(keys.size).toBe(50)
  })

  it('is a no-op for an empty list', () => {
    expect(() => preLayoutHosts([])).not.toThrow()
  })
})

describe('preLayoutHostsBelowSite', () => {
  it('keeps every host below the site anchor', () => {
    const hosts = Array.from({ length: 30 }, (_, i) => host(`h${i}`))
    const site = { x: 100, y: -200 }
    preLayoutHostsBelowSite(site, hosts, 40)
    for (const h of hosts) {
      expect(h.y!).toBeGreaterThanOrEqual(site.y + 40)
    }
  })
})

describe('layoutR / needsServices', () => {
  it('fan uses the fan radius, everything else the orbit radius', () => {
    // fanR packs a half circle, so it needs roughly twice the orbit radius.
    expect(layoutR('fan', 40)).toBeGreaterThan(layoutR('orbit', 40))
    expect(layoutR('donut', 40)).toBe(layoutR('orbit', 40))
  })

  it('only full-service layouts trigger the bulk service fetch', () => {
    expect(needsServices('fan')).toBe(true)
    expect(needsServices('orbit')).toBe(true)
    expect(needsServices('row')).toBe(true)
    expect(needsServices('donut')).toBe(false)
    expect(needsServices('off')).toBe(false)
    expect(needsServices(null)).toBe(false)
  })
})

describe('siteScaleForZoom', () => {
  it('inflates at low zoom, clamps at 3.5, stays 1 at full zoom', () => {
    expect(siteScaleForZoom(1)).toBe(1)
    expect(siteScaleForZoom(2)).toBe(1)
    expect(siteScaleForZoom(0.5)).toBe(2)
    expect(siteScaleForZoom(0.1)).toBe(3.5)
    // NaN/garbage zoom must not produce NaN transforms.
    expect(siteScaleForZoom(Number.NaN)).toBe(1)
  })
})

describe('bfsLevels', () => {
  it('assigns 0 to roots and increments per parent hop', () => {
    const nodes = [topo('root'), topo('child', 'UP', ['root']), topo('grandchild', 'UP', ['child'])]
    const levels = bfsLevels(nodes)
    expect(levels.get('root')).toBe(0)
    expect(levels.get('child')).toBe(1)
    expect(levels.get('grandchild')).toBe(2)
  })

  it('treats hosts whose parents are outside the visible set as roots', () => {
    const nodes = [topo('visible', 'UP', ['outside-the-board'])]
    expect(bfsLevels(nodes).get('visible')).toBe(0)
  })

  it('still levels every node in a parent cycle', () => {
    const nodes = [topo('a', 'UP', ['b']), topo('b', 'UP', ['a'])]
    const levels = bfsLevels(nodes)
    expect(levels.has('a')).toBe(true)
    expect(levels.has('b')).toBe(true)
  })
})
