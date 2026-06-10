import { computed, ref, watch } from 'vue'

import type { PresentationElement } from '@/types/api'
import { isUnboundSlot } from '@/utils/presentationSampleState'

// The connect-data walkthrough: after designing a slide (or applying a
// template), every unbound data slot is visited in reading order and bound via
// the shared binding form. The guide only steers which slot is current — all
// mutations stay on the canvas's mutate() pipeline.

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
  const current = computed(() => slots.value.find((s) => s.id === currentId.value) ?? null)

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
    if (slots.value.some((s) => s.id === id)) currentId.value = id
  }

  function step(dir: 1 | -1): void {
    const list = slots.value
    if (!list.length) return
    const idx = list.findIndex((s) => s.id === currentId.value)
    const next = idx === -1 ? 0 : (idx + dir + list.length) % list.length
    currentId.value = list[next]?.id ?? null
  }

  function next(): void {
    step(1)
  }
  function prev(): void {
    step(-1)
  }

  // When the current slot gets bound it disappears from the list — advance to
  // the nearest remaining slot; when none remain the walkthrough is done.
  watch(slots, (now, before) => {
    if (!active.value) return
    if (!now.length) {
      exit()
      return
    }
    if (currentId.value && !now.some((s) => s.id === currentId.value)) {
      const oldIdx = before?.findIndex((s) => s.id === currentId.value) ?? 0
      const target = now[Math.min(Math.max(oldIdx, 0), now.length - 1)]
      currentId.value = target?.id ?? null
    }
  })

  return {
    active,
    slots,
    unboundCount,
    boundCount,
    totalCount,
    current,
    currentId,
    enter,
    exit,
    goTo,
    next,
    prev
  }
}
