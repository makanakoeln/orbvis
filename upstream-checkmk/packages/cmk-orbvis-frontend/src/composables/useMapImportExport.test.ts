// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import type { MapRead } from '@/types/api'

import { useMapImportExport } from './useMapImportExport'

const { mapsApi, mapsStore } = vi.hoisted(() => ({
  mapsApi: {
    importCfg: vi.fn().mockResolvedValue(undefined),
    importMap: vi.fn().mockResolvedValue(undefined),
    exportMap: vi.fn().mockResolvedValue(undefined),
    clone: vi.fn().mockResolvedValue(undefined)
  },
  mapsStore: { fetchMaps: vi.fn().mockResolvedValue(undefined) }
}))

vi.mock('@/api/client', () => ({ mapsApi }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ accessToken: 'tok' }) }))
vi.mock('@/stores/maps', () => ({ useMapsStore: () => mapsStore }))
vi.mock('@cmk/lib/i18n', () => ({ default: () => ({ _t: (s: string) => s }) }))

function fileEvent(file: File | null): Event {
  return { target: { files: file ? [file] : [], value: 'sentinel' } } as unknown as Event
}

function setup() {
  return useMapImportExport({ cloneInputEl: ref<HTMLInputElement | null>(null) })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('alert', vi.fn())
})

describe('useMapImportExport — import', () => {
  it('parses a JSON map, imports it and refreshes the list', async () => {
    const api = setup()
    const ev = fileEvent(new File(['{"name":"b1","objects":[]}'], 'b1.json'))
    await api.importMap(ev)
    expect(mapsApi.importMap).toHaveBeenCalledWith({ name: 'b1', objects: [] }, 'tok', false)
    expect(mapsStore.fetchMaps).toHaveBeenCalledOnce()
    // The file input is always cleared so re-selecting the same file re-fires change.
    expect((ev.target as HTMLInputElement).value).toBe('')
  })

  it('routes .cfg uploads through the legacy importer', async () => {
    const api = setup()
    await api.importMap(fileEvent(new File(['legacy'], 'old.cfg')))
    expect(mapsApi.importCfg).toHaveBeenCalledOnce()
    expect(mapsApi.importMap).not.toHaveBeenCalled()
  })

  it('does nothing when no file is selected', async () => {
    const api = setup()
    await api.importMap(fileEvent(null))
    expect(mapsApi.importMap).not.toHaveBeenCalled()
  })

  it('surfaces an overwrite confirmation on "already exists" instead of failing', async () => {
    mapsApi.importMap.mockRejectedValueOnce(new Error('Map already exists'))
    const api = setup()
    await api.importMap(fileEvent(new File(['{"name":"dup","objects":[]}'], 'dup.json')))
    expect(api.importConflict.value?.name).toBe('dup')
    expect(mapsStore.fetchMaps).not.toHaveBeenCalled()

    // Confirming runs the stored action with overwrite=true and refreshes.
    await api.confirmImportOverwrite()
    expect(mapsApi.importMap).toHaveBeenLastCalledWith(
      { name: 'dup', objects: [] },
      'tok',
      true
    )
    expect(mapsStore.fetchMaps).toHaveBeenCalledOnce()
    expect(api.importConflict.value).toBeNull()
  })

  it('alerts on invalid JSON and still clears the input', async () => {
    const api = setup()
    const ev = fileEvent(new File(['not json'], 'bad.json'))
    await api.importMap(ev)
    expect(alert).toHaveBeenCalled()
    expect(mapsApi.importMap).not.toHaveBeenCalled()
    expect((ev.target as HTMLInputElement).value).toBe('')
  })
})

describe('useMapImportExport — clone', () => {
  it('pre-fills "_copy" name and a "(Copy)" alias', () => {
    const api = setup()
    api.cloneMap({ name: 'prod', alias: 'Production' } as MapRead)
    expect(api.confirmClone.value).toBe('prod')
    expect(api.cloneNewName.value).toBe('prod_copy')
    expect(api.cloneAlias.value).toBe('Production (Copy)')
  })

  it('sanitizes the typed clone name', () => {
    const api = setup()
    api.onCloneNameInput({ target: { value: 'My Map!' } } as unknown as Event)
    // sanitizeMapName strips spaces/illegal chars — assert it changed, not raw.
    expect(api.cloneNewName.value).not.toBe('My Map!')
    expect(api.cloneNewName.value).not.toMatch(/[ !]/)
  })

  it('clones with the new name + alias, refreshes and closes', async () => {
    const api = setup()
    api.cloneMap({ name: 'prod', alias: 'Production' } as MapRead)
    await api.doClone()
    expect(mapsApi.clone).toHaveBeenCalledWith(
      'prod',
      { new_name: 'prod_copy', alias: 'Production (Copy)' },
      'tok'
    )
    expect(mapsStore.fetchMaps).toHaveBeenCalledOnce()
    expect(api.confirmClone.value).toBeNull()
  })

  it('reports a clone failure without closing the dialog', async () => {
    mapsApi.clone.mockRejectedValueOnce(new Error('name taken'))
    const api = setup()
    api.cloneMap({ name: 'prod', alias: '' } as MapRead)
    await api.doClone()
    expect(api.cloneError.value).toBe('name taken')
    expect(api.confirmClone.value).toBe('prod')
  })
})
