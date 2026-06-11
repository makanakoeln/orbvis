import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { boardsApi } from '@/api/client'
import { useHistory } from '@/composables/useHistory'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import type {
  BoardConfig,
  PresentationElement,
  PresentationTheme,
  PresentationView
} from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

// JSON clone (not structuredClone): the view is pure JSON, and structuredClone
// throws DataCloneError on Vue reactive proxies.
export function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v))
}

// Undo snapshots carry the theme alongside the elements so applying a template
// (which switches both) rolls back as one step.
interface DocSnapshot {
  theme: PresentationTheme
  elements: PresentationElement[]
}

/**
 * The presentation editor's document model: the working copy of the view, the
 * snapshot-based undo/redo stack, and the debounced save pipeline (optimistic
 * locking with 409 realignment). All mutations funnel through ``mutate`` so
 * history and persistence stay uniform no matter which panel edits the slide.
 */
export function usePresentationDocument(config: () => BoardConfig, onBoardSwitch?: () => void) {
  const { _t } = usei18n()
  const auth = useAuthStore()
  const boardsStore = useBoardsStore()

  function initialView(): PresentationView {
    const v = config().view
    if (v.type === 'presentation') return clone(v)
    return { type: 'presentation', width: 1920, height: 1080, theme: 'midnight', elements: [] }
  }

  const local = ref<PresentationView>(initialView())
  const version = ref(config().version ?? 0)
  const elements = computed(() => local.value.elements)

  const history = useHistory<DocSnapshot>(
    (s) => JSON.stringify(s),
    (s) => JSON.parse(s)
  )
  function currentSnapshot(): DocSnapshot {
    return { theme: local.value.theme, elements: clone(elements.value) }
  }
  function snapshot(): void {
    history.record(currentSnapshot())
  }
  function applySnapshot(s: DocSnapshot): void {
    local.value = { ...local.value, theme: s.theme, elements: s.elements }
  }

  watch(
    () => config().name,
    () => {
      local.value = initialView()
      version.value = config().version ?? 0
      history.reset()
      onBoardSwitch?.()
    }
  )

  let saveTimer: ReturnType<typeof setTimeout> | null = null
  const saving = ref(false)
  const savedAt = ref(false)
  const saveLabel = computed(() =>
    saving.value ? _t('Saving…') : savedAt.value ? _t('Saved') : ''
  )

  function scheduleSave(): void {
    savedAt.value = false
    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(saveNow, 400)
  }

  async function saveNow(): Promise<void> {
    if (!auth.accessToken) return
    const name = config().name
    saving.value = true
    try {
      const payload = { view: clone(local.value) }
      const cfg = await boardsApi.update(name, payload, auth.accessToken, version.value)
      version.value = cfg.version ?? version.value
      if (boardsStore.currentBoard?.name === cfg.name) {
        boardsStore.currentBoard.version = cfg.version ?? 0
        boardsStore.currentBoard.view = cfg.view
      }
      savedAt.value = true
    } catch {
      // Version conflict or transient error: realign to the canonical version
      // without tearing the working copy down (fetchBoard nulls currentBoard,
      // which would unmount the editor and drop in-progress edits).
      try {
        const cfg = await boardsApi.get(name, auth.accessToken)
        version.value = cfg.version ?? 0
      } catch {
        /* leave version as-is; the next edit retries */
      }
    } finally {
      saving.value = false
    }
  }

  function mutate(fn: () => void): void {
    snapshot()
    fn()
    scheduleSave()
  }
  function setElements(next: PresentationElement[]): void {
    local.value = { ...local.value, elements: next }
  }

  function undo(): void {
    const restored = history.undo(currentSnapshot())
    if (restored) {
      applySnapshot(restored)
      scheduleSave()
    }
  }
  function redo(): void {
    const restored = history.redo(currentSnapshot())
    if (restored) {
      applySnapshot(restored)
      scheduleSave()
    }
  }

  // ── Element lookups shared by every editor surface ──────────────────────────
  const childToGroup = computed(() => {
    const map = new Map<string, string>()
    for (const el of elements.value) {
      if (el.kind === 'group') for (const c of el.children) map.set(c, el.id)
    }
    return map
  })
  function topLevelId(id: string): string {
    return childToGroup.value.get(id) ?? id
  }
  function byId(id: string | null | undefined): PresentationElement | undefined {
    return id ? elements.value.find((e) => e.id === id) : undefined
  }
  const nextZ = computed(() => elements.value.reduce((m, e) => Math.max(m, e.z), 0) + 1)

  onBeforeUnmount(() => {
    if (saveTimer) clearTimeout(saveTimer)
  })

  return {
    local,
    version,
    elements,
    history,
    snapshot,
    mutate,
    setElements,
    scheduleSave,
    saveNow,
    saving,
    saveLabel,
    undo,
    redo,
    childToGroup,
    topLevelId,
    byId,
    nextZ
  }
}
