import { computed } from 'vue'

import type { Box } from '@/composables/useSmartGuides'
import type { PresentationElement, ShapeElement } from '@/types/api'

interface SelectionGeometryOptions {
  selectedIds: () => string[]
  selectedElements: () => PresentationElement[]
  scale: () => number
  offsetX: () => number
  offsetY: () => number
  connectorEndpoints: (el: ShapeElement) => {
    start: { x: number; y: number }
    end: { x: number; y: number }
  }
  isConnectorShape: (el: PresentationElement) => el is ShapeElement
}

const HANDLES = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'] as const

/**
 * Read-only overlay geometry for the presentation editor's current selection:
 * the bounding box (a connector contributes its endpoint extent, not its
 * vestigial x/y/w/h), the resize/rotate handle styles (scaled to stay a
 * constant on-screen size), and the inspector anchor that flips below the
 * selection near the top edge. Pure derivation — no mutation, no side effects.
 */
export function usePresentationSelectionGeometry(options: SelectionGeometryOptions) {
  const {
    selectedIds,
    selectedElements,
    scale,
    offsetX,
    offsetY,
    connectorEndpoints,
    isConnectorShape
  } = options

  const selectionBox = computed<Box | null>(() => {
    const els = selectedElements()
    if (!els.length) return null
    let minX = Infinity
    let minY = Infinity
    let maxX = -Infinity
    let maxY = -Infinity
    for (const e of els) {
      // A connector's real extent is the box of its (possibly docked) endpoints,
      // not its vestigial x/y/w/h.
      if (isConnectorShape(e)) {
        const { start, end } = connectorEndpoints(e)
        minX = Math.min(minX, start.x, end.x)
        minY = Math.min(minY, start.y, end.y)
        maxX = Math.max(maxX, start.x, end.x)
        maxY = Math.max(maxY, start.y, end.y)
      } else {
        minX = Math.min(minX, e.x)
        minY = Math.min(minY, e.y)
        maxX = Math.max(maxX, e.x + e.w)
        maxY = Math.max(maxY, e.y + e.h)
      }
    }
    return { x: minX, y: minY, w: maxX - minX, h: maxY - minY }
  })

  // A single selected connector has no resize/rotate handles (its geometry comes
  // from its endpoints), so the overlay shows only the selection outline.
  const singleIsConnector = computed(
    () =>
      selectedIds().length === 1 &&
      !!selectedElements()[0] &&
      isConnectorShape(selectedElements()[0]!)
  )
  // On a single rotated element the overlay (and its handles) rotate with it so
  // the handles still sit on the element's corners.
  const singleRotation = computed(() =>
    selectedIds().length === 1 ? (selectedElements()[0]?.rotation ?? 0) : 0
  )
  const selBoxStyle = computed(() => {
    const b = selectionBox.value
    if (!b) return {}
    return {
      left: `${b.x}px`,
      top: `${b.y}px`,
      width: `${b.w}px`,
      height: `${b.h}px`,
      outlineWidth: `${1.5 / scale()}px`,
      transform: singleRotation.value ? `rotate(${singleRotation.value}deg)` : 'none',
      transformOrigin: 'center center'
    }
  })
  const handles = HANDLES
  function handleStyle(h: string): Record<string, string> {
    const s = 10 / scale()
    const pos: Record<string, [string, string]> = {
      nw: ['0%', '0%'],
      n: ['50%', '0%'],
      ne: ['100%', '0%'],
      e: ['100%', '50%'],
      se: ['100%', '100%'],
      s: ['50%', '100%'],
      sw: ['0%', '100%'],
      w: ['0%', '50%']
    }
    const [l, t] = pos[h] ?? ['0%', '0%']
    return {
      width: `${s}px`,
      height: `${s}px`,
      left: l,
      top: t,
      marginLeft: `${-s / 2}px`,
      marginTop: `${-s / 2}px`,
      borderWidth: `${1 / scale()}px`
    }
  }
  const rotateHandleStyle = computed(() => {
    const s = 12 / scale()
    return {
      width: `${s}px`,
      height: `${s}px`,
      left: '50%',
      top: `${-26 / scale()}px`,
      marginLeft: `${-s / 2}px`,
      borderWidth: `${1 / scale()}px`
    }
  })

  const inspectorEl = computed(() => (selectedIds().length === 1 ? selectedElements()[0] : null))
  // Anchor the inspector centered just above the selection; the card transforms
  // itself up by its own height (CSS translate -100%) so it never covers the
  // element. Near the top edge it flips below so it can't leave the viewport.
  const inspectorPos = computed(() => {
    const b = selectionBox.value
    if (!b || !inspectorEl.value) return null
    const topY = offsetY() + b.y * scale()
    const below = topY < 150
    return {
      x: offsetX() + (b.x + b.w / 2) * scale(),
      y: below ? offsetY() + (b.y + b.h) * scale() : topY,
      below
    }
  })

  return {
    selectionBox,
    singleIsConnector,
    selBoxStyle,
    handles,
    handleStyle,
    rotateHandleStyle,
    inspectorEl,
    inspectorPos
  }
}
