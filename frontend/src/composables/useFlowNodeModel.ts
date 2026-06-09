import type { SimulationLinkDatum, SimulationNodeDatum } from 'd3'

import type { BoardObject, ObjectState, ServiceNode, TopologyNode } from '@/types/api'
import { type DonutSegment, HEALTHY_HOST_STATES } from '@/utils/flowGeometry'
import { stateColor } from '@/utils/stateColors'

export interface FNode extends SimulationNodeDatum {
  id: string
  state: string
  output: string
  bfsLevel: number
  nodeType: 'host' | 'service' | 'more' | 'site'
  hostId?: string
  siteId?: string
  svcTotalCount?: number // total services for this host (set on service nodes for label visibility)
  moreCount?: number // for nodeType='more': number of services hidden behind this aggregate
  // Cached pointer to the host's TopologyNode so the tooltip can show the
  // same status detail (alias, services_summary, …) as the static board.
  // Only set on host nodes; service nodes have minimal data via their parent.
  topo?: TopologyNode
  svc?: ServiceNode
  parentTopo?: TopologyNode
  // d3-force sets x/y/vx/vy
}

export interface FLink extends SimulationLinkDatum<FNode> {
  source: FNode
  target: FNode
  sourceState: string
  isServiceLink: boolean
}

export interface CmdMarker {
  key: string
  glyph: string
  fill: string
  fg: string
  title: string
  corner: 'tr' | 'tl' | 'br'
}

const HALO_DEFAULT_STROKE = 'rgba(0,0,0,0.4)'

interface FlowNodeModelOptions {
  nodes: () => TopologyNode[]
  connectionId: () => string | null | undefined
  topKWorstIds: () => Set<string>
}

/**
 * Maps flow-board d3 nodes (FNode) to OrbVis BoardObject/ObjectState (for the
 * shared drawer/menus) and derives their visual descriptors — halo stroke,
 * command-state badges, donut segments. Site nodes aggregate their member hosts
 * on the fly. `nodes`/`connectionId`/`topKWorstIds` are injected as getters.
 */
export function useFlowNodeModel(options: FlowNodeModelOptions) {
  const { nodes, connectionId, topKWorstIds } = options

  function worstServiceState(d: FNode): string | null {
    const s = d.topo?.services_summary
    if (!s) return null
    if (s.critical > 0) return 'CRITICAL'
    if (s.warning > 0) return 'WARNING'
    if (s.unknown > 0) return 'UNKNOWN'
    return null
  }

  function hostHalo(d: FNode): { stroke: string; width: number } {
    const isTopK = topKWorstIds().has(d.id)
    if (!HEALTHY_HOST_STATES.has(d.state)) {
      return isTopK
        ? { stroke: stateColor(d.state), width: 4 }
        : { stroke: HALO_DEFAULT_STROKE, width: 1.5 }
    }
    const worst = worstServiceState(d)
    if (!worst) return { stroke: HALO_DEFAULT_STROKE, width: 1.5 }
    return { stroke: stateColor(worst), width: isTopK ? 4 : 2.5 }
  }

  // Command-state markers shown on a node, mirroring the static board's badges:
  // acknowledged / in downtime / notifications-disabled. Source is the host
  // (d.topo) or the service (d.svc); both carry the same flags.
  function commandMarkers(d: FNode): CmdMarker[] {
    const src = d.nodeType === 'service' ? d.svc : d.topo
    if (!src) return []
    const out: CmdMarker[] = []
    if (src.acknowledged)
      out.push({
        key: 'ack',
        glyph: '✓',
        fill: 'var(--color-warning)',
        fg: '#18181b',
        title: 'Acknowledged',
        corner: 'tr'
      })
    if (src.in_downtime)
      out.push({
        key: 'dt',
        glyph: '‖',
        fill: 'var(--color-light-blue-50)',
        fg: '#ffffff',
        title: 'In downtime',
        corner: 'tl'
      })
    if (src.notifications_enabled === false)
      out.push({
        key: 'notif',
        glyph: '∅',
        fill: 'var(--text-muted)',
        fg: '#ffffff',
        title: 'Notifications disabled',
        corner: 'br'
      })
    return out
  }

  function badgeXY(corner: CmdMarker['corner'], r: number): [number, number] {
    const o = r * 0.72
    if (corner === 'tr') return [o, -o]
    if (corner === 'tl') return [-o, -o]
    return [o, o]
  }

  function donutSegments(n: TopologyNode): DonutSegment[] {
    const s = n.services_summary
    if (!s) return []
    // Order matters visually: critical first so it dominates the top of the ring.
    const all: DonutSegment[] = [
      { state: 'CRITICAL', value: s.critical },
      { state: 'WARNING', value: s.warning },
      { state: 'UNKNOWN', value: s.unknown },
      { state: 'PENDING', value: s.pending },
      { state: 'OK', value: s.ok }
    ]
    return all.filter((seg) => seg.value > 0)
  }

  function boardObjectFromFNode(d: FNode): BoardObject {
    if (d.nodeType === 'site') {
      return {
        id: d.id,
        type: 'site',
        x: 0,
        y: 0,
        host_name: d.siteId ?? null
      } as BoardObject
    }
    const isService = d.nodeType === 'service'
    const svcName = isService ? d.id.split('::').slice(1).join('::') : undefined
    // "+N more" pseudo nodes resolve to their host so clicking opens the
    // host's full service list in Checkmk.
    const hostNameForCheckmk = isService || d.nodeType === 'more' ? d.hostId : d.id
    return {
      id: d.id,
      type: isService ? 'service' : 'host',
      x: 0,
      y: 0,
      host_name: hostNameForCheckmk,
      service_description: svcName,
      // The flow board has no state-map entry to read site_id from, so carry
      // it from the topology node — commands need it to hit the right site.
      // Services and "+N more" nodes carry the host via parentTopo; host nodes
      // via topo.
      site_id: (isService || d.nodeType === 'more' ? d.parentTopo : d.topo)?.site_id ?? null
    } as BoardObject
  }

  function siteHostsAggregate(siteId: string): {
    hostCount: number
    hostsUp: number
    hostsDown: number
    hostsUnreachable: number
    summary: { ok: number; warning: number; critical: number; unknown: number; pending: number }
  } {
    let hostCount = 0
    let hostsUp = 0
    let hostsDown = 0
    let hostsUnreachable = 0
    const summary = { ok: 0, warning: 0, critical: 0, unknown: 0, pending: 0 }
    for (const n of nodes()) {
      const sid = n.site_id || connectionId()
      if (sid !== siteId) continue
      hostCount++
      if (n.state === 'UP') hostsUp++
      else if (n.state === 'DOWN') hostsDown++
      else if (n.state === 'UNREACHABLE') hostsUnreachable++
      const s = n.services_summary
      if (s) {
        summary.ok += s.ok
        summary.warning += s.warning
        summary.critical += s.critical
        summary.unknown += s.unknown
        summary.pending += s.pending
      }
    }
    return { hostCount, hostsUp, hostsDown, hostsUnreachable, summary }
  }

  function objectStateFromFNode(d: FNode): ObjectState {
    if (d.nodeType === 'site') {
      const agg = siteHostsAggregate(d.siteId ?? '')
      // Site state aggregation rules:
      // - DOWN: every host on this site is DOWN/UNREACHABLE (site itself is offline)
      // - CRITICAL: at least one host is DOWN/UNREACHABLE OR has critical services
      // - WARNING: at least one warning/unknown service, no criticals
      // - UP: everything is healthy
      // A single down host out of hundreds shouldn't paint the whole site
      // DOWN — that would mask the real picture during partial outages.
      const allDown = agg.hostCount > 0 && agg.hostsDown + agg.hostsUnreachable === agg.hostCount
      const anyDown = agg.hostsDown + agg.hostsUnreachable > 0
      const worst = allDown
        ? 'DOWN'
        : anyDown || agg.summary.critical > 0
          ? 'CRITICAL'
          : agg.summary.warning > 0 || agg.summary.unknown > 0
            ? 'WARNING'
            : 'UP'
      return {
        object_id: d.id,
        type: 'site',
        state: worst as ObjectState['state'],
        output:
          `${agg.hostCount} hosts ` +
          `(${agg.hostsUp} up, ${agg.hostsDown} down, ${agg.hostsUnreachable} unreachable)`,
        perf_data: '',
        acknowledged: false,
        in_downtime: false,
        stale: false,
        notifications_enabled: true,
        active_checks_enabled: true,
        site_id: d.siteId ?? null,
        services_summary: agg.summary
      }
    }
    if (d.nodeType === 'service') {
      const svc = d.svc
      const parent = d.parentTopo
      return {
        object_id: d.id,
        type: 'service',
        state: d.state as ObjectState['state'],
        output: d.output,
        perf_data: '',
        acknowledged: svc?.acknowledged ?? false,
        in_downtime: svc?.in_downtime ?? false,
        stale: false,
        notifications_enabled: svc?.notifications_enabled ?? true,
        active_checks_enabled: parent?.active_checks_enabled ?? true,
        ...(parent?.alias !== undefined && { alias: parent.alias }),
        ...(parent?.address !== undefined && { address: parent.address }),
        site_id: parent?.site_id ?? null,
        last_check: svc?.last_check ?? null,
        next_check: svc?.next_check ?? null,
        last_state_change: svc?.last_state_change ?? null,
        services_summary: null
      }
    }
    const topo = d.topo
    return {
      object_id: d.id,
      type: d.nodeType,
      state: d.state as ObjectState['state'],
      output: d.output,
      perf_data: '',
      acknowledged: topo?.acknowledged ?? false,
      in_downtime: topo?.in_downtime ?? false,
      stale: false,
      notifications_enabled: topo?.notifications_enabled ?? true,
      active_checks_enabled: topo?.active_checks_enabled ?? true,
      ...(topo?.alias !== undefined && { alias: topo.alias }),
      ...(topo?.address !== undefined && { address: topo.address }),
      site_id: topo?.site_id ?? null,
      last_check: topo?.last_check ?? null,
      next_check: topo?.next_check ?? null,
      last_state_change: topo?.last_state_change ?? null,
      ...(topo?.state_type !== undefined && { state_type: topo.state_type }),
      ...(topo?.current_attempt !== undefined && { current_attempt: topo.current_attempt }),
      ...(topo?.max_attempts !== undefined && { max_attempts: topo.max_attempts }),
      services_summary: topo?.services_summary ?? null
    }
  }

  return {
    worstServiceState,
    hostHalo,
    commandMarkers,
    badgeXY,
    donutSegments,
    boardObjectFromFNode,
    siteHostsAggregate,
    objectStateFromFNode
  }
}
