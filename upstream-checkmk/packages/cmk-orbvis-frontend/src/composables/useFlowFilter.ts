import { select } from 'd3'
import { type Ref, computed, ref, watch } from 'vue'

import type { FLink, FNode } from '@/composables/useFlowNodeModel'
import { HEALTHY_HOST_STATES } from '@/utils/flowGeometry'
import {
  DIMMED_FILTER,
  DIMMED_OPACITY,
  type FilterField,
  matchesFilterTerms,
  parseFilterTerms
} from '@/utils/objectFilter'

interface FlowFilterOptions {
  svgEl: Ref<SVGSVGElement | null>
  problemsOnly: () => boolean | undefined
  worstServiceState: (d: FNode) => string | null
}

/**
 * Search/problem filter for the flow map. Rather than removing nodes (which
 * would re-trigger force-collide and rearrange the map on every keystroke),
 * non-matching nodes/links are dimmed via opacity + a desaturating SVG filter,
 * and matches are raised to the top. Group operators (hg:/sg:) are dropped —
 * flow nodes are only hosts/services so they could never match.
 */
export function useFlowFilter(options: FlowFilterOptions) {
  const { svgEl, problemsOnly, worstServiceState } = options

  const filterText = ref('')
  const UNSUPPORTED_FLOW_FIELDS: ReadonlySet<FilterField> = new Set(['hostgroup', 'servicegroup'])
  const filterTerms = computed(() =>
    parseFilterTerms(filterText.value).filter((term) => !UNSUPPORTED_FLOW_FIELDS.has(term.field))
  )

  function nodeHasProblem(d: FNode): boolean {
    if (d.nodeType === 'host') {
      if (!HEALTHY_HOST_STATES.has(d.state)) return true
      return worstServiceState(d) !== null
    }
    return d.state !== 'OK' && d.state !== 'PENDING'
  }

  function flowFieldValue(d: FNode, field: FilterField): string[] {
    const isService = d.nodeType === 'service'
    const svcName = isService ? d.id.split('::').slice(1).join('::') : ''
    const hostName = isService || d.nodeType === 'more' ? (d.hostId ?? '') : d.id
    switch (field) {
      case 'host':
        return [hostName, d.topo?.alias ?? d.parentTopo?.alias ?? '']
      case 'service':
        return [svcName]
      case 'id':
        return [d.id]
      case 'any':
        return [d.id, hostName, svcName, d.topo?.alias ?? '', d.parentTopo?.alias ?? '']
      case 'hostgroup':
      case 'servicegroup':
        return []
    }
  }

  function nodeMatchesFilter(d: FNode): boolean {
    if (problemsOnly() && !nodeHasProblem(d)) return false
    return matchesFilterTerms(filterTerms.value, (field) => flowFieldValue(d, field))
  }

  const filterIsActive = computed(() => !!problemsOnly() || filterTerms.value.length > 0)

  let filterOpacityActive = false

  function applyFilterOpacity(): void {
    if (!svgEl.value) return
    const sel = select(svgEl.value)
    if (!filterIsActive.value) {
      if (!filterOpacityActive) return
      filterOpacityActive = false
      sel.selectAll('g.node, g.links line').attr('opacity', 1)
      sel.selectAll('g.node').style('filter', null)
      return
    }
    filterOpacityActive = true
    sel
      .selectAll<SVGGElement, FNode>('g.node')
      .attr('opacity', (d) => (nodeMatchesFilter(d) ? 1 : DIMMED_OPACITY))
      .style('filter', (d) => (nodeMatchesFilter(d) ? null : DIMMED_FILTER))
      .filter((d) => nodeMatchesFilter(d))
      .raise()
    sel.selectAll<SVGLineElement, FLink>('g.links line').attr('opacity', (d) => {
      const src = d.source as FNode
      const tgt = d.target as FNode
      return nodeMatchesFilter(src) && nodeMatchesFilter(tgt) ? 1 : DIMMED_OPACITY
    })
  }

  watch([filterText, problemsOnly], () => {
    if (svgEl.value) applyFilterOpacity()
  })

  return { filterText, applyFilterOpacity }
}
