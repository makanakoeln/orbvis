import { computed, ref, watch } from 'vue'

import type { BoardObject } from '@/types/api'

interface AnchorRect {
  left: number
  top: number
  right: number
  bottom: number
}

interface PropertiesPopoverOptions {
  anchorRect: () => AnchorRect | null | undefined
  object: () => BoardObject
}

/**
 * Placement + drag behaviour for the object-properties card. With an anchor it
 * renders as a popover beside the clicked object (preferring the right side,
 * clamped to the viewport); without one it is a centered modal. The header is a
 * drag handle that offsets the card via a transform, with a 4-px threshold so a
 * plain header click still works. Drag offset resets whenever the object swaps.
 */
export function usePropertiesPopover(options: PropertiesPopoverOptions) {
  const { anchorRect, object } = options

  const isPopover = computed(() => !!anchorRect())

  const popoverStyle = computed<Record<string, string>>(() => {
    const r = anchorRect()
    if (!r) return {}
    const margin = 12
    const cardW = 400
    const cardMaxH = window.innerHeight * 0.75 // matches max-h-[75vh]

    // Horizontal: prefer right of object, fall back to left
    let left: number
    if (r.right + margin + cardW <= window.innerWidth) {
      left = r.right + margin
    } else {
      left = Math.max(margin, r.left - margin - cardW)
    }

    // Vertical: align top of card with top of object, clamp to viewport
    let top = r.top
    // If the card would overflow the bottom, push it up
    if (top + cardMaxH + margin > window.innerHeight) {
      top = window.innerHeight - cardMaxH - margin
    }
    top = Math.max(margin, top)

    return { left: `${left}px`, top: `${top}px` }
  })

  const dragOffset = ref({ dx: 0, dy: 0 })
  const dragStart = ref<{ px: number; py: number; ox: number; oy: number } | null>(null)
  const dragging = ref(false)

  const cardStyle = computed<Record<string, string>>(() => {
    const base: Record<string, string> = isPopover.value ? { ...popoverStyle.value } : {}
    if (dragOffset.value.dx !== 0 || dragOffset.value.dy !== 0) {
      base.transform = `translate(${dragOffset.value.dx}px, ${dragOffset.value.dy}px)`
    }
    return base
  })

  function onHeaderPointerDown(e: PointerEvent) {
    if (e.button !== 0) return
    // Don't start a drag from interactive children (the close button etc.).
    if ((e.target as HTMLElement).closest('button')) return
    dragStart.value = {
      px: e.clientX,
      py: e.clientY,
      ox: dragOffset.value.dx,
      oy: dragOffset.value.dy
    }
  }

  function onHeaderPointerMove(e: PointerEvent) {
    const s = dragStart.value
    if (!s) return
    const dx = s.ox + (e.clientX - s.px)
    const dy = s.oy + (e.clientY - s.py)
    if (!dragging.value && Math.abs(dx - s.ox) < 4 && Math.abs(dy - s.oy) < 4) {
      return // below threshold: don't engage drag yet (preserves click on header)
    }
    if (!dragging.value) {
      dragging.value = true
      const target = e.currentTarget as HTMLElement
      try {
        target.setPointerCapture(e.pointerId)
      } catch {
        // pointer may have ended
      }
    }
    dragOffset.value = { dx, dy }
  }

  function onHeaderPointerUp() {
    dragStart.value = null
    dragging.value = false
  }

  watch(object, () => {
    dragOffset.value = { dx: 0, dy: 0 }
    dragStart.value = null
  })

  return {
    isPopover,
    cardStyle,
    dragging,
    onHeaderPointerDown,
    onHeaderPointerMove,
    onHeaderPointerUp
  }
}
