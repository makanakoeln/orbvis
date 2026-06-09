import { computed, ref, watch } from 'vue'

import { useToast } from '@/composables/useToast'
import { useBoardsStore } from '@/stores/boards'
import type { BoardBulkDeleteFailure, BoardListView, BoardRead } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

interface BoardBulkActionsOptions {
  filteredBoards: () => BoardRead[]
  viewMode: () => BoardListView
  /** Opens the single-board settings modal (used when a bulk edit targets one). */
  openSettings: (map: BoardRead) => void
}

/**
 * Multi-select + bulk delete/edit/export for the board list. Selection is reset
 * when switching to cards view (the checkboxes only render in the table). Bulk
 * delete keeps the still-selected set on partial failure so the operator can
 * retry; bulk edit collapses to the single-board settings modal when exactly one
 * editable board is selected. Read-only boards are filtered out of edits.
 */
export function useBoardBulkActions(options: BoardBulkActionsOptions) {
  const { filteredBoards, viewMode, openSettings } = options
  const boardsStore = useBoardsStore()
  const toast = useToast()
  const { _t } = usei18n()

  const selectedBoards = ref<Set<string>>(new Set())
  const confirmBulkDelete = ref(false)
  const bulkBusy = ref(false)
  const bulkFailures = ref<BoardBulkDeleteFailure[]>([])
  const showBulkEdit = ref(false)

  watch(viewMode, (mode) => {
    if (mode === 'cards' && selectedBoards.value.size > 0) {
      selectedBoards.value = new Set()
      bulkFailures.value = []
    }
  })

  function clearSelection() {
    selectedBoards.value = new Set()
    bulkFailures.value = []
  }

  function toggleBoardSelection(name: string) {
    const next = new Set(selectedBoards.value)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    selectedBoards.value = next
  }

  const selectedCount = computed(() => selectedBoards.value.size)

  const allFilteredSelected = computed(() => {
    const list = filteredBoards()
    if (list.length === 0) return false
    return list.every((b) => selectedBoards.value.has(b.name))
  })

  function toggleSelectAllFiltered(checked: boolean) {
    const next = new Set(selectedBoards.value)
    if (checked) {
      for (const b of filteredBoards()) next.add(b.name)
    } else {
      for (const b of filteredBoards()) next.delete(b.name)
    }
    selectedBoards.value = next
  }

  const selectedNames = computed(() => Array.from(selectedBoards.value))

  const selectedAliases = computed(() => {
    const byName = new Map(boardsStore.boards.map((b) => [b.name, b.alias || b.name]))
    return selectedNames.value.map((n) => byName.get(n) ?? n)
  })

  function openBulkDelete() {
    if (selectedCount.value === 0) return
    bulkFailures.value = []
    confirmBulkDelete.value = true
  }

  async function doBulkDelete() {
    if (bulkBusy.value) return
    bulkBusy.value = true
    try {
      const result = await boardsStore.bulkDeleteBoards(selectedNames.value)
      const okCount = result.deleted.length
      const failed = result.failed
      const okSet = new Set(result.deleted)
      const remaining = new Set<string>()
      for (const n of selectedBoards.value) {
        if (!okSet.has(n)) remaining.add(n)
      }
      selectedBoards.value = remaining
      bulkFailures.value = failed
      confirmBulkDelete.value = false
      if (failed.length === 0) {
        toast.success(_t('%{n} boards deleted', { n: okCount }))
      } else {
        toast.error(_t('%{ok} deleted, %{fail} failed', { ok: okCount, fail: failed.length }))
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Bulk delete failed')
      confirmBulkDelete.value = false
    } finally {
      bulkBusy.value = false
    }
  }

  const editableSelectedNames = computed(() => {
    const writable = new Set(boardsStore.boards.filter((b) => !b.readonly).map((b) => b.name))
    return selectedNames.value.filter((n) => writable.has(n))
  })

  const editableSelectedAliases = computed(() => {
    const byName = new Map(boardsStore.boards.map((b) => [b.name, b.alias || b.name]))
    return editableSelectedNames.value.map((n) => byName.get(n) ?? n)
  })

  function openBulkEdit() {
    if (editableSelectedNames.value.length === 0) {
      toast.error(_t('None of the selected boards is editable (all are read-only).'))
      return
    }
    if (editableSelectedNames.value.length === 1) {
      const board = boardsStore.boards.find((b) => b.name === editableSelectedNames.value[0])
      if (board) {
        openSettings(board)
        return
      }
    }
    showBulkEdit.value = true
  }

  async function doBulkEdit(updates: Record<string, unknown>) {
    if (bulkBusy.value) return
    if (Object.keys(updates).length === 0) {
      showBulkEdit.value = false
      return
    }
    const targets = editableSelectedNames.value
    if (targets.length === 0) {
      showBulkEdit.value = false
      return
    }
    bulkBusy.value = true
    try {
      const result = await boardsStore.bulkEditBoards(targets, updates)
      showBulkEdit.value = false
      if (result.failed.length === 0) {
        toast.success(_t('Updated %{n} boards', { n: result.updated.length }))
      } else {
        toast.error(
          _t('Updated %{ok}, %{fail} failed', {
            ok: result.updated.length,
            fail: result.failed.length
          })
        )
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Bulk edit failed')
    } finally {
      bulkBusy.value = false
    }
  }

  async function doBulkExport() {
    if (bulkBusy.value || selectedNames.value.length === 0) return
    bulkBusy.value = true
    try {
      await boardsStore.bulkExportBoards(selectedNames.value)
      toast.success(_t('Exported %{n} boards', { n: selectedNames.value.length }))
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Bulk export failed')
    } finally {
      bulkBusy.value = false
    }
  }

  return {
    selectedBoards,
    confirmBulkDelete,
    bulkBusy,
    showBulkEdit,
    clearSelection,
    toggleBoardSelection,
    selectedCount,
    allFilteredSelected,
    toggleSelectAllFiltered,
    selectedAliases,
    openBulkDelete,
    doBulkDelete,
    editableSelectedNames,
    editableSelectedAliases,
    openBulkEdit,
    doBulkEdit,
    doBulkExport
  }
}
