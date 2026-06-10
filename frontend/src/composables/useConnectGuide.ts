import { computed, ref, watch } from 'vue'

import type { PresentationElement } from '@/types/api'
import { type BindableElement, isBindable, isUnboundSlot } from '@/utils/presentationSampleState'

// The connect-data walkthrough: after designing a slide (or applying a
// template), every unbound data slot is visited in reading order and bound via
// the shared binding form. The guide only steers which slot is current — all
// mutations stay on the canvas's mutate() pipeline.
//
// Binding a host does NOT auto-advance: the slot stays current so the operator
// can still pick a service and label. Advancing is always explicit (Next/Skip,
// badge click), which keeps the flow predictable.

// Reading order: rows top→bottom (with a tolerance so slightly staggered tiles
// count as one row), left→right within a row.
const ROW_TOLERANCE = 80

function readingOrder(a: PresentationElement, b: PresentationElement): number {
  const rowA = Math.floor(a.y / ROW_TOLERANCE)
  const rowB = Math.floor(b.y / ROW_TOLERANCE)
  return rowA - rowB || a.x - b.x
}

export function useConnectGuide(elements: () => PresentationElement[]) {
  const active = ref(false)
  const currentId = ref<string | null>(null)
  // Slot count at entry — bound slots vanish from `slots`, so progress is
  // total minus remaining.
  const totalCount = ref(0)

  const slots = computed(() => elements().filter(isUnboundSlot).sort(readingOrder))
  const unboundCount = computed(() => slots.value.length)
  const boundCount = computed(() => Math.max(0, totalCount.value - slots.value.length))

  // The current slot survives being bound (unlike `slots`) so the popover can
  // stay open for the service/label step.
  const current = computed<BindableElement | null>(() => {
    const el = elements().find((e) => e.id === currentId.value)
    return el && isBindable(el) ? el : null
  })
  const currentBound = computed(() => !!current.value && !isUnboundSlot(current.value))

  function enter(): void {
    totalCount.value = slots.value.length
    currentId.value = slots.value[0]?.id ?? null
    active.value = totalCount.value > 0
  }

  function exit(): void {
    active.value = false
    currentId.value = null
  }

  function goTo(id: string): void {
    const el = elements().find((e) => e.id === id)
    if (el && isUnboundSlot(el)) currentId.value = id
  }

  // Next/prev move through the remaining unbound slots relative to the current
  // element's reading-order position — also when the current one is already
  // bound (and therefore no longer part of `slots`). With nothing left to
  // visit, Next finishes the walkthrough.
  function step(dir: 1 | -1): void {
    const list = slots.value
    if (!list.length) {
      exit()
      return
    }
    const cur = current.value
    const idx = list.findIndex((s) => s.id === currentId.value)
    if (idx !== -1) {
      currentId.value = list[(idx + dir + list.length) % list.length]?.id ?? null
      return
    }
    if (!cur) {
      currentId.value = list[0]?.id ?? null
      return
    }
    const after = list.filter((s) => readingOrder(cur, s) < 0)
    const before = list.filter((s) => readingOrder(cur, s) >= 0)
    const target =
      dir === 1 ? (after[0] ?? list[0]) : (before[before.length - 1] ?? list[list.length - 1])
    currentId.value = target?.id ?? null
  }

  function next(): void {
    step(1)
  }
  function prev(): void {
    step(-1)
  }

  // Only a deleted current element retargets the guide; with nothing bindable
  // left at all the walkthrough ends. Sync flush so a delete that is undone in
  // the same tick can't slip past the pre-flush change comparison.
  watch(
    current,
    (c) => {
      if (!active.value || c) return
      if (slots.value.length) currentId.value = slots.value[0]?.id ?? null
      else exit()
    },
    { flush: 'sync' }
  )

  return {
    active,
    slots,
    unboundCount,
    boundCount,
    totalCount,
    current,
    currentBound,
    currentId,
    enter,
    exit,
    goTo,
    next,
    prev
  }
}
