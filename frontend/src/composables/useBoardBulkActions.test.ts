import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import type { BoardListView, BoardRead } from '@/types/api'

import { useBoardBulkActions } from './useBoardBulkActions'

const { toast, store } = vi.hoisted(() => ({
  toast: { success: vi.fn(), error: vi.fn() },
  store: {
    boards: [] as BoardRead[],
    bulkDeleteBoards: vi.fn(),
    bulkEditBoards: vi.fn(),
    bulkExportBoards: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('@/composables/useToast', () => ({ useToast: () => toast }))
vi.mock('@/stores/boards', () => ({ useBoardsStore: () => store }))
vi.mock('@/vendor/cmk/lib/i18n', () => ({ default: () => ({ _t: (s: string) => s }) }))

function board(name: string, over: Partial<BoardRead> = {}): BoardRead {
  return { name, alias: name, readonly: false, ...over } as BoardRead
}

function setup(boards: BoardRead[], viewMode: Ref<BoardListView> = ref('table')) {
  store.boards = boards
  const openSettings = vi.fn()
  const api = useBoardBulkActions({
    filteredBoards: () => boards,
    viewMode: () => viewMode.value,
    openSettings
  })
  return { api, openSettings, viewMode }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useBoardBulkActions — selection', () => {
  it('toggles a board in and out of the selection', () => {
    const { api } = setup([board('a'), board('b')])
    api.toggleBoardSelection('a')
    expect(api.selectedCount.value).toBe(1)
    api.toggleBoardSelection('a')
    expect(api.selectedCount.value).toBe(0)
  })

  it('reports allFilteredSelected only when every filtered board is selected', () => {
    const { api } = setup([board('a'), board('b')])
    expect(api.allFilteredSelected.value).toBe(false)
    api.toggleSelectAllFiltered(true)
    expect(api.allFilteredSelected.value).toBe(true)
    expect(api.selectedCount.value).toBe(2)
    api.toggleSelectAllFiltered(false)
    expect(api.allFilteredSelected.value).toBe(false)
  })

  it('is false for an empty board list', () => {
    const { api } = setup([])
    expect(api.allFilteredSelected.value).toBe(false)
  })

  it('clears the selection when switching to cards view', async () => {
    const viewMode = ref<BoardListView>('table')
    const { api } = setup([board('a')], viewMode)
    api.toggleBoardSelection('a')
    expect(api.selectedCount.value).toBe(1)
    viewMode.value = 'cards'
    await nextTick()
    expect(api.selectedCount.value).toBe(0)
  })
})

describe('useBoardBulkActions — bulk delete', () => {
  it('does not open the confirm dialog when nothing is selected', () => {
    const { api } = setup([board('a')])
    api.openBulkDelete()
    expect(api.confirmBulkDelete.value).toBe(false)
  })

  it('keeps the failed boards selected on partial failure and reports it', async () => {
    store.bulkDeleteBoards.mockResolvedValueOnce({
      deleted: ['a'],
      failed: [{ name: 'b', error: 'busy' }]
    })
    const { api } = setup([board('a'), board('b')])
    api.toggleSelectAllFiltered(true)
    await api.doBulkDelete()
    // 'a' deleted, 'b' failed → 'b' stays selected for retry.
    expect(api.selectedCount.value).toBe(1)
    expect(api.selectedBoards.value.has('b')).toBe(true)
    expect(toast.error).toHaveBeenCalled()
    expect(api.confirmBulkDelete.value).toBe(false)
  })

  it('clears the selection and reports success when all delete', async () => {
    store.bulkDeleteBoards.mockResolvedValueOnce({ deleted: ['a', 'b'], failed: [] })
    const { api } = setup([board('a'), board('b')])
    api.toggleSelectAllFiltered(true)
    await api.doBulkDelete()
    expect(api.selectedCount.value).toBe(0)
    expect(toast.success).toHaveBeenCalled()
  })
})

describe('useBoardBulkActions — bulk edit', () => {
  it('excludes read-only boards from the editable set', () => {
    const { api } = setup([board('rw'), board('ro', { readonly: true })])
    api.toggleSelectAllFiltered(true)
    expect(api.editableSelectedNames.value).toEqual(['rw'])
  })

  it('errors when every selected board is read-only', () => {
    const { api } = setup([board('ro', { readonly: true })])
    api.toggleSelectAllFiltered(true)
    api.openBulkEdit()
    expect(toast.error).toHaveBeenCalled()
    expect(api.showBulkEdit.value).toBe(false)
  })

  it('collapses to the single-board settings modal when one editable board is selected', () => {
    const { api, openSettings } = setup([board('only')])
    api.toggleBoardSelection('only')
    api.openBulkEdit()
    expect(openSettings).toHaveBeenCalledWith(expect.objectContaining({ name: 'only' }))
    expect(api.showBulkEdit.value).toBe(false)
  })

  it('opens the bulk-edit slide-in for several editable boards', () => {
    const { api } = setup([board('a'), board('b')])
    api.toggleSelectAllFiltered(true)
    api.openBulkEdit()
    expect(api.showBulkEdit.value).toBe(true)
  })

  it('applies edits only to editable targets', async () => {
    store.bulkEditBoards.mockResolvedValueOnce({ updated: ['rw'], failed: [] })
    const { api } = setup([board('rw'), board('ro', { readonly: true })])
    api.toggleSelectAllFiltered(true)
    await api.doBulkEdit({ icon_size: 40 })
    expect(store.bulkEditBoards).toHaveBeenCalledWith(['rw'], { icon_size: 40 })
    expect(toast.success).toHaveBeenCalled()
  })

  it('skips the API call for an empty update set', async () => {
    const { api } = setup([board('a')])
    api.toggleBoardSelection('a')
    await api.doBulkEdit({})
    expect(store.bulkEditBoards).not.toHaveBeenCalled()
    expect(api.showBulkEdit.value).toBe(false)
  })
})
