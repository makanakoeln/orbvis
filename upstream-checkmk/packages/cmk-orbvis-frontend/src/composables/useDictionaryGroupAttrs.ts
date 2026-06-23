import { type Ref, onBeforeUnmount, watch } from 'vue'

interface GroupedElement {
  group?: { key?: string | null } | null
}

export function useDictionaryGroupAttrs(
  container: Ref<HTMLElement | null>,
  elements: () => GroupedElement[] | undefined
) {
  let observer: MutationObserver | null = null

  function groupKeys(): string[] {
    const keys: string[] = []
    ;(elements() ?? []).forEach((el, i) => {
      const key = el.group?.key ?? `-ungrouped-${i}`
      if (!keys.includes(key)) keys.push(key)
    })
    return keys
  }

  function stamp() {
    const root = container.value
    const table = root?.querySelector('table')
    if (!table) return
    const rows = Array.from(table.querySelectorAll(':scope > tbody > tr')).filter((tr) =>
      tr.querySelector(':scope > td.form-dictionary__dictleft')
    )
    const keys = groupKeys()
    rows.forEach((tr, i) => {
      const key = keys[i]
      if (key !== undefined && tr.getAttribute('data-group') !== key) {
        tr.setAttribute('data-group', key)
      }
    })
  }

  watch(
    container,
    (el) => {
      observer?.disconnect()
      observer = null
      if (el) {
        stamp()
        observer = new MutationObserver(stamp)
        observer.observe(el, { childList: true, subtree: true })
      }
    },
    { immediate: true, flush: 'post' }
  )

  watch(() => elements(), stamp, { flush: 'post' })

  onBeforeUnmount(() => {
    observer?.disconnect()
    observer = null
  })

  return { stamp }
}
