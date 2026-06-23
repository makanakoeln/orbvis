import { beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, nextTick, ref } from 'vue'

import type { MapListView, MapRead } from '@/types/api'

import { useMapBulkActions } from './useMapBulkActions'

const { toast, store } = vi.hoisted(() => ({
  toast: { success: vi.fn(), error: vi.fn() },
  store: {
    maps: [] as MapRead[],
    bulkDeleteMaps: vi.fn(),
    bulkEditMaps: vi.fn(),
    bulkExportMaps: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('@/composables/useToast', () => ({ useToast: () => toast }))
vi.mock('@/stores/maps', () => ({ useMapsStore: () => store }))
vi.mock('@cmk/lib/i18n', () => ({ default: () => ({ _t: (s: string) => s }) }))

function map(name: string, over: Partial<MapRead> = {}): MapRead {
  return { name, alias: name, readonly: false, ...over } as MapRead
}

function setup(maps: MapRead[], viewMode: Ref<MapListView> = ref('table')) {
  store.maps = maps
  const openSettings = vi.fn()
  const api = useMapBulkActions({
    filteredMaps: () => maps,
    viewMode: () => viewMode.value,
    openSettings
  })
  return { api, openSettings, viewMode }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useMapBulkActions — selection', () => {
  it('toggles a map in and out of the selection', () => {
    const { api } = setup([map('a'), map('b')])
    api.toggleMapSelection('a')
    expect(api.selectedCount.value).toBe(1)
    api.toggleMapSelection('a')
    expect(api.selectedCount.value).toBe(0)
  })

  it('reports allFilteredSelected only when every filtered map is selected', () => {
    const { api } = setup([map('a'), map('b')])
    expect(api.allFilteredSelected.value).toBe(false)
    api.toggleSelectAllFiltered(true)
    expect(api.allFilteredSelected.value).toBe(true)
    expect(api.selectedCount.value).toBe(2)
    api.toggleSelectAllFiltered(false)
    expect(api.allFilteredSelected.value).toBe(false)
  })

  it('is false for an empty map list', () => {
    const { api } = setup([])
    expect(api.allFilteredSelected.value).toBe(false)
  })

  it('clears the selection when switching to cards view', async () => {
    const viewMode = ref<MapListView>('table')
    const { api } = setup([map('a')], viewMode)
    api.toggleMapSelection('a')
    expect(api.selectedCount.value).toBe(1)
    viewMode.value = 'cards'
    await nextTick()
    expect(api.selectedCount.value).toBe(0)
  })
})

describe('useMapBulkActions — bulk delete', () => {
  it('does not open the confirm dialog when nothing is selected', () => {
    const { api } = setup([map('a')])
    api.openBulkDelete()
    expect(api.confirmBulkDelete.value).toBe(false)
  })

  it('keeps the failed maps selected on partial failure and reports it', async () => {
    store.bulkDeleteMaps.mockResolvedValueOnce({
      deleted: ['a'],
      failed: [{ name: 'b', error: 'busy' }]
    })
    const { api } = setup([map('a'), map('b')])
    api.toggleSelectAllFiltered(true)
    await api.doBulkDelete()
    // 'a' deleted, 'b' failed → 'b' stays selected for retry.
    expect(api.selectedCount.value).toBe(1)
    expect(api.selectedMaps.value.has('b')).toBe(true)
    expect(toast.error).toHaveBeenCalled()
    expect(api.confirmBulkDelete.value).toBe(false)
  })

  it('clears the selection and reports success when all delete', async () => {
    store.bulkDeleteMaps.mockResolvedValueOnce({ deleted: ['a', 'b'], failed: [] })
    const { api } = setup([map('a'), map('b')])
    api.toggleSelectAllFiltered(true)
    await api.doBulkDelete()
    expect(api.selectedCount.value).toBe(0)
    expect(toast.success).toHaveBeenCalled()
  })
})

describe('useMapBulkActions — bulk edit', () => {
  it('excludes read-only maps from the editable set', () => {
    const { api } = setup([map('rw'), map('ro', { readonly: true })])
    api.toggleSelectAllFiltered(true)
    expect(api.editableSelectedNames.value).toEqual(['rw'])
  })

  it('errors when every selected map is read-only', () => {
    const { api } = setup([map('ro', { readonly: true })])
    api.toggleSelectAllFiltered(true)
    api.openBulkEdit()
    expect(toast.error).toHaveBeenCalled()
    expect(api.showBulkEdit.value).toBe(false)
  })

  it('collapses to the single-map settings modal when one editable map is selected', () => {
    const { api, openSettings } = setup([map('only')])
    api.toggleMapSelection('only')
    api.openBulkEdit()
    expect(openSettings).toHaveBeenCalledWith(expect.objectContaining({ name: 'only' }))
    expect(api.showBulkEdit.value).toBe(false)
  })

  it('opens the bulk-edit slide-in for several editable maps', () => {
    const { api } = setup([map('a'), map('b')])
    api.toggleSelectAllFiltered(true)
    api.openBulkEdit()
    expect(api.showBulkEdit.value).toBe(true)
  })

  it('applies edits only to editable targets', async () => {
    store.bulkEditMaps.mockResolvedValueOnce({ updated: ['rw'], failed: [] })
    const { api } = setup([map('rw'), map('ro', { readonly: true })])
    api.toggleSelectAllFiltered(true)
    await api.doBulkEdit({ icon_size: 40 })
    expect(store.bulkEditMaps).toHaveBeenCalledWith(['rw'], { icon_size: 40 })
    expect(toast.success).toHaveBeenCalled()
  })

  it('skips the API call for an empty update set', async () => {
    const { api } = setup([map('a')])
    api.toggleMapSelection('a')
    await api.doBulkEdit({})
    expect(store.bulkEditMaps).not.toHaveBeenCalled()
    expect(api.showBulkEdit.value).toBe(false)
  })
})
