// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

import type { BoardRead } from '@/types/api'

import { useBoardImportExport } from './useBoardImportExport'

const { boardsApi, boardsStore } = vi.hoisted(() => ({
  boardsApi: {
    importCfg: vi.fn().mockResolvedValue(undefined),
    importBoard: vi.fn().mockResolvedValue(undefined),
    exportBoard: vi.fn().mockResolvedValue(undefined),
    clone: vi.fn().mockResolvedValue(undefined)
  },
  boardsStore: { fetchBoards: vi.fn().mockResolvedValue(undefined) }
}))

vi.mock('@/api/client', () => ({ boardsApi }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ accessToken: 'tok' }) }))
vi.mock('@/stores/boards', () => ({ useBoardsStore: () => boardsStore }))
vi.mock('@/vendor/cmk/lib/i18n', () => ({ default: () => ({ _t: (s: string) => s }) }))

function fileEvent(file: File | null): Event {
  return { target: { files: file ? [file] : [], value: 'sentinel' } } as unknown as Event
}

function setup() {
  return useBoardImportExport({ cloneInputEl: ref<HTMLInputElement | null>(null) })
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('alert', vi.fn())
})

describe('useBoardImportExport — import', () => {
  it('parses a JSON board, imports it and refreshes the list', async () => {
    const api = setup()
    const ev = fileEvent(new File(['{"name":"b1","objects":[]}'], 'b1.json'))
    await api.importBoard(ev)
    expect(boardsApi.importBoard).toHaveBeenCalledWith({ name: 'b1', objects: [] }, 'tok', false)
    expect(boardsStore.fetchBoards).toHaveBeenCalledOnce()
    // The file input is always cleared so re-selecting the same file re-fires change.
    expect((ev.target as HTMLInputElement).value).toBe('')
  })

  it('routes .cfg uploads through the legacy importer', async () => {
    const api = setup()
    await api.importBoard(fileEvent(new File(['legacy'], 'old.cfg')))
    expect(boardsApi.importCfg).toHaveBeenCalledOnce()
    expect(boardsApi.importBoard).not.toHaveBeenCalled()
  })

  it('does nothing when no file is selected', async () => {
    const api = setup()
    await api.importBoard(fileEvent(null))
    expect(boardsApi.importBoard).not.toHaveBeenCalled()
  })

  it('surfaces an overwrite confirmation on "already exists" instead of failing', async () => {
    boardsApi.importBoard.mockRejectedValueOnce(new Error('Board already exists'))
    const api = setup()
    await api.importBoard(fileEvent(new File(['{"name":"dup","objects":[]}'], 'dup.json')))
    expect(api.importConflict.value?.name).toBe('dup')
    expect(boardsStore.fetchBoards).not.toHaveBeenCalled()

    // Confirming runs the stored action with overwrite=true and refreshes.
    await api.confirmImportOverwrite()
    expect(boardsApi.importBoard).toHaveBeenLastCalledWith(
      { name: 'dup', objects: [] },
      'tok',
      true
    )
    expect(boardsStore.fetchBoards).toHaveBeenCalledOnce()
    expect(api.importConflict.value).toBeNull()
  })

  it('alerts on invalid JSON and still clears the input', async () => {
    const api = setup()
    const ev = fileEvent(new File(['not json'], 'bad.json'))
    await api.importBoard(ev)
    expect(alert).toHaveBeenCalled()
    expect(boardsApi.importBoard).not.toHaveBeenCalled()
    expect((ev.target as HTMLInputElement).value).toBe('')
  })
})

describe('useBoardImportExport — clone', () => {
  it('pre-fills "_copy" name and a "(Copy)" alias', () => {
    const api = setup()
    api.cloneBoard({ name: 'prod', alias: 'Production' } as BoardRead)
    expect(api.confirmClone.value).toBe('prod')
    expect(api.cloneNewName.value).toBe('prod_copy')
    expect(api.cloneAlias.value).toBe('Production (Copy)')
  })

  it('sanitizes the typed clone name', () => {
    const api = setup()
    api.onCloneNameInput({ target: { value: 'My Board!' } } as unknown as Event)
    // sanitizeBoardName strips spaces/illegal chars — assert it changed, not raw.
    expect(api.cloneNewName.value).not.toBe('My Board!')
    expect(api.cloneNewName.value).not.toMatch(/[ !]/)
  })

  it('clones with the new name + alias, refreshes and closes', async () => {
    const api = setup()
    api.cloneBoard({ name: 'prod', alias: 'Production' } as BoardRead)
    await api.doClone()
    expect(boardsApi.clone).toHaveBeenCalledWith(
      'prod',
      { new_name: 'prod_copy', alias: 'Production (Copy)' },
      'tok'
    )
    expect(boardsStore.fetchBoards).toHaveBeenCalledOnce()
    expect(api.confirmClone.value).toBeNull()
  })

  it('reports a clone failure without closing the dialog', async () => {
    boardsApi.clone.mockRejectedValueOnce(new Error('name taken'))
    const api = setup()
    api.cloneBoard({ name: 'prod', alias: '' } as BoardRead)
    await api.doClone()
    expect(api.cloneError.value).toBe('name taken')
    expect(api.confirmClone.value).toBe('prod')
  })
})
