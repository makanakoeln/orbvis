import { type Ref, nextTick, ref } from 'vue'

import { mapsApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useMapsStore } from '@/stores/maps'
import type { MapConfig, MapRead } from '@/types/api'
import { sanitizeMapName } from '@/utils/naming'
import usei18n from '@cmk/lib/i18n'

interface MapImportExportOptions {
  /** The clone-modal name input, selected when the clone dialog opens.
   *  Owned by the host SFC (the element lives in its template). */
  cloneInputEl: Ref<HTMLInputElement | null>
}

/**
 * Single-map import / export / clone for the map list. `.cfg` files go
 * through the legacy importer, everything else is parsed as JSON map config.
 * An "already exists" error surfaces an overwrite confirmation rather than
 * failing outright. Clone pre-fills `<name>_copy` and sanitizes the name as the
 * operator types.
 */
export function useMapImportExport(options: MapImportExportOptions) {
  const { cloneInputEl } = options
  const auth = useAuthStore()
  const mapsStore = useMapsStore()
  const { _t } = usei18n()

  const importConflict = ref<{ name: string; action: () => Promise<unknown> } | null>(null)

  async function importMap(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (!file) return
    try {
      if (file.name.toLowerCase().endsWith('.cfg')) {
        try {
          await mapsApi.importCfg(file, auth.accessToken!, false)
        } catch (e: unknown) {
          if (e instanceof Error && e.message.includes('already exists')) {
            const name = file.name.replace(/\.cfg$/i, '')
            importConflict.value = {
              name,
              action: () => mapsApi.importCfg(file, auth.accessToken!, true)
            }
            return
          } else {
            throw e
          }
        }
      } else {
        const text = await file.text()
        const data: MapConfig = JSON.parse(text)
        try {
          await mapsApi.importMap(data, auth.accessToken!, false)
        } catch (e: unknown) {
          if (e instanceof Error && e.message.includes('already exists')) {
            importConflict.value = {
              name: data.name,
              action: () => mapsApi.importMap(data, auth.accessToken!, true)
            }
            return
          } else {
            throw e
          }
        }
      }
      await mapsStore.fetchMaps()
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
      await mapsStore.fetchMaps()
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : _t('Import failed'))
    }
  }

  async function exportMap(name: string) {
    await mapsApi.exportMap(name, auth.accessToken!)
  }

  const confirmClone = ref<string | null>(null)
  const cloneNewName = ref('')
  const cloneAlias = ref('')
  const cloneError = ref('')

  function cloneMap(map: MapRead) {
    confirmClone.value = map.name
    cloneNewName.value = `${map.name}_copy`
    cloneAlias.value = map.alias ? `${map.alias} (Copy)` : ''
    cloneError.value = ''
    nextTick(() => {
      cloneInputEl.value?.select()
    })
  }

  function onCloneNameInput(e: Event) {
    cloneNewName.value = sanitizeMapName((e.target as HTMLInputElement).value)
  }

  async function doClone() {
    if (!confirmClone.value || !cloneNewName.value) return
    try {
      await mapsApi.clone(
        confirmClone.value,
        {
          new_name: cloneNewName.value,
          ...(cloneAlias.value ? { alias: cloneAlias.value } : {})
        },
        auth.accessToken!
      )
      await mapsStore.fetchMaps()
      confirmClone.value = null
    } catch (e: unknown) {
      cloneError.value = e instanceof Error ? e.message : _t('Clone failed')
    }
  }

  return {
    importConflict,
    importMap,
    confirmImportOverwrite,
    exportMap,
    confirmClone,
    cloneNewName,
    cloneAlias,
    cloneError,
    cloneMap,
    onCloneNameInput,
    doClone
  }
}
