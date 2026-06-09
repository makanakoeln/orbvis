import { select } from 'd3'
import { type Ref, computed, ref } from 'vue'

import type { FNode } from '@/composables/useFlowNodeModel'
import type { BoardObject } from '@/types/api'

// SELECTION_STROKE matches --color-yellow-50 from cmk/colors.css. Inlined as a
// hex literal because d3 attr() must operate on SVG attribute strings — CSS
// custom properties aren't available there without a getComputedStyle hop.
const SELECTION_STROKE = 'rgb(255, 215, 3)'

interface FlowSelectionOptions {
  svgEl: Ref<SVGSVGElement | null>
  hostHalo: (d: FNode) => { stroke: string; width: number }
  boardObjectFromFNode: (d: FNode) => BoardObject
}

/**
 * Multi-select for the flow board: shift-click toggles a node, shift-drag
 * lassoes a box, and the bulk-action toolbar applies a host/service command
 * sequentially over the set. Selection styling is written directly onto the
 * SVG circles (restoring each node's halo on deselect).
 */
export function useFlowSelection(options: FlowSelectionOptions) {
  const { svgEl, hostHalo, boardObjectFromFNode } = options

  const selectedIds = ref<Set<string>>(new Set())
  const selectedFNodes = new Map<string, FNode>()

  function toggleSelection(d: FNode): void {
    if (selectedIds.value.has(d.id)) {
      selectedIds.value.delete(d.id)
      selectedFNodes.delete(d.id)
    } else {
      selectedIds.value.add(d.id)
      selectedFNodes.set(d.id, d)
    }
    selectedIds.value = new Set(selectedIds.value)
    applySelectionStyles()
  }

  function clearSelection(): void {
    selectedIds.value = new Set()
    selectedFNodes.clear()
    applySelectionStyles()
  }

  function attachLasso(svg: SVGSVGElement): void {
    let startX = 0
    let startY = 0
    let lassoEl: SVGRectElement | null = null
    let active = false

    const onPointerDown = (event: PointerEvent) => {
      if (!event.shiftKey || event.button !== 0) return
      const target = event.target as Element
      if (target.closest('g.node')) return
      active = true
      const rect = svg.getBoundingClientRect()
      startX = event.clientX - rect.left
      startY = event.clientY - rect.top
      lassoEl = document.createElementNS('http://www.w3.org/2000/svg', 'rect')
      lassoEl.setAttribute('fill', 'rgba(255,215,3,0.08)')
      lassoEl.setAttribute('stroke', 'rgb(255,215,3)')
      lassoEl.setAttribute('stroke-dasharray', '4 4')
      lassoEl.setAttribute('pointer-events', 'none')
      svg.appendChild(lassoEl)
      svg.setPointerCapture(event.pointerId)
      event.preventDefault()
    }

    const onPointerMove = (event: PointerEvent) => {
      if (!active || !lassoEl) return
      const rect = svg.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top
      const minX = Math.min(startX, x)
      const minY = Math.min(startY, y)
      const w = Math.abs(x - startX)
      const h = Math.abs(y - startY)
      lassoEl.setAttribute('x', String(minX))
      lassoEl.setAttribute('y', String(minY))
      lassoEl.setAttribute('width', String(w))
      lassoEl.setAttribute('height', String(h))
    }

    const onPointerUp = (event: PointerEvent) => {
      if (!active) return
      active = false
      svg.releasePointerCapture(event.pointerId)
      const rect = svg.getBoundingClientRect()
      const endX = event.clientX - rect.left
      const endY = event.clientY - rect.top
      const minX = Math.min(startX, endX)
      const minY = Math.min(startY, endY)
      const maxX = Math.max(startX, endX)
      const maxY = Math.max(startY, endY)
      if (lassoEl) {
        lassoEl.remove()
        lassoEl = null
      }
      // Trivial 4-px box = treat as missed-click, do nothing
      if (maxX - minX < 4 && maxY - minY < 4) return
      select(svg)
        .selectAll<SVGGElement, FNode>('g.node')
        .each(function (d) {
          const r = (this as SVGGElement).getBoundingClientRect()
          const cx = r.x + r.width / 2 - rect.left
          const cy = r.y + r.height / 2 - rect.top
          if (cx >= minX && cx <= maxX && cy >= minY && cy <= maxY) {
            selectedIds.value.add(d.id)
            selectedFNodes.set(d.id, d)
          }
        })
      selectedIds.value = new Set(selectedIds.value)
      applySelectionStyles()
    }

    svg.addEventListener('pointerdown', onPointerDown)
    svg.addEventListener('pointermove', onPointerMove)
    svg.addEventListener('pointerup', onPointerUp)
    svg.addEventListener('pointercancel', onPointerUp)
  }

  function applySelectionStyles(): void {
    if (!svgEl.value) return
    select(svgEl.value)
      .selectAll<SVGGElement, FNode>('g.node')
      .each(function (d) {
        const isSel = selectedIds.value.has(d.id)
        const circle = (this as SVGGElement).querySelector('circle')
        if (!circle) return
        if (isSel) {
          circle.setAttribute('data-selected', '1')
          circle.setAttribute('stroke', SELECTION_STROKE)
          circle.setAttribute('stroke-width', '3')
        } else if (circle.getAttribute('data-selected') === '1') {
          circle.removeAttribute('data-selected')
          if (d.nodeType === 'host') {
            const halo = hostHalo(d)
            circle.setAttribute('stroke', halo.stroke)
            circle.setAttribute('stroke-width', String(halo.width))
          } else {
            circle.setAttribute('stroke', 'rgba(0,0,0,0.4)')
            circle.setAttribute('stroke-width', '1')
          }
        }
      })
  }

  const selectedObjects = computed(() =>
    [...selectedFNodes.values()].map((d) => boardObjectFromFNode(d))
  )

  async function bulkAction(
    handler: (obj: BoardObject | null) => Promise<void> | void
  ): Promise<void> {
    const objs = selectedObjects.value.slice()
    for (const obj of objs) {
      await Promise.resolve(handler(obj))
    }
  }

  return {
    selectedIds,
    toggleSelection,
    clearSelection,
    attachLasso,
    applySelectionStyles,
    bulkAction
  }
}
