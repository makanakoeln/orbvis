import { type Ref, nextTick, ref } from 'vue'

import { boardsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useBoardsStore } from '@/stores/boards'
import type { BoardConfig, BoardRead } from '@/types/api'
import { sanitizeBoardName } from '@/utils/naming'
import usei18n from '@/vendor/cmk/lib/i18n'

interface BoardImportExportOptions {
  /** The clone-modal name input, selected when the clone dialog opens.
   *  Owned by the host SFC (the element lives in its template). */
  cloneInputEl: Ref<HTMLInputElement | null>
}

/**
 * Single-board import / export / clone for the board list. `.cfg` files go
 * through the legacy importer, everything else is parsed as JSON board config.
 * An "already exists" error surfaces an overwrite confirmation rather than
 * failing outright. Clone pre-fills `<name>_copy` and sanitizes the name as the
 * operator types.
 */
export function useBoardImportExport(options: BoardImportExportOptions) {
  const { cloneInputEl } = options
  const auth = useAuthStore()
  const boardsStore = useBoardsStore()
  const { _t } = usei18n()

  const importConflict = ref<{ name: string; action: () => Promise<unknown> } | null>(null)

  async function importBoard(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) return
    try {
      if (file.name.toLowerCase().endsWith('.cfg')) {
        try {
          await boardsApi.importCfg(file, auth.accessToken!, false)
        } catch (e: unknown) {
          if (e instanceof Error && e.message.includes('already exists')) {
            const name = file.name.replace(/\.cfg$/i, '')
            importConflict.value = {
              name,
              action: () => boardsApi.importCfg(file, auth.accessToken!, true)
            }
            return
          } else {
            throw e
          }
        }
      } else {
        const text = await file.text()
        const data: BoardConfig = JSON.parse(text)
        try {
          await boardsApi.importBoard(data, auth.accessToken!, false)
        } catch (e: unknown) {
          if (e instanceof Error && e.message.includes('already exists')) {
            importConflict.value = {
              name: data.name,
              action: () => boardsApi.importBoard(data, auth.accessToken!, true)
            }
            return
          } else {
            throw e
          }
        }
      }
      await boardsStore.fetchBoards()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : _t('Import failed'))
    } finally {
      ;(event.target as HTMLInputElement).value = ''
    }
  }

  async function confirmImportOverwrite() {
    if (!importConflict.value) return
    const action = importConflict.value.action
    importConflict.value = null
    try {
      await action()
      await boardsStore.fetchBoards()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : _t('Import failed'))
    }
  }

  async function exportBoard(name: string) {
    await boardsApi.exportBoard(name, auth.accessToken!)
  }

  const confirmClone = ref<string | null>(null)
  const cloneNewName = ref('')
  const cloneAlias = ref('')
  const cloneError = ref('')

  function cloneBoard(map: BoardRead) {
    confirmClone.value = map.name
    cloneNewName.value = `${map.name}_copy`
    cloneAlias.value = map.alias ? `${map.alias} (Copy)` : ''
    cloneError.value = ''
    nextTick(() => {
      cloneInputEl.value?.select()
    })
  }

  function onCloneNameInput(e: Event) {
    cloneNewName.value = sanitizeBoardName((e.target as HTMLInputElement).value)
  }

  async function doClone() {
    if (!confirmClone.value || !cloneNewName.value) return
    try {
      await boardsApi.clone(
        confirmClone.value,
        {
          new_name: cloneNewName.value,
          ...(cloneAlias.value ? { alias: cloneAlias.value } : {})
        },
        auth.accessToken!
      )
      await boardsStore.fetchBoards()
      confirmClone.value = null
    } catch (e: unknown) {
      cloneError.value = e instanceof Error ? e.message : _t('Clone failed')
    }
  }

  return {
    importConflict,
    importBoard,
    confirmImportOverwrite,
    exportBoard,
    confirmClone,
    cloneNewName,
    cloneAlias,
    cloneError,
    cloneBoard,
    onCloneNameInput,
    doClone
  }
}
