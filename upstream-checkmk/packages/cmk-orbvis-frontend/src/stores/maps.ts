import { defineStore } from 'pinia'
import { ref } from 'vue'

import { mapsApi } from '@/api/client'
import type {
  MapBulkDeleteResult,
  MapBulkEditResult,
  MapConfig,
  MapRead,
  RenderMode
} from '@/types/api'

import { useAuthStore } from './auth'

export const useMapsStore = defineStore('maps', () => {
  const maps = ref<MapRead[]>([])
  const currentMap = ref<MapConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const bgRefreshTicks = ref<Record<string, number>>({})

  function bumpBgRefreshTick(name: string) {
    bgRefreshTicks.value[name] = Date.now()
  }

  function token(): string {
    return useAuthStore().accessToken ?? ''
  }

  async function fetchMaps() {
    loading.value = true
    error.value = null
    try {
      maps.value = await mapsApi.list(token())
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load maps'
    } finally {
      loading.value = false
    }
  }

  async function fetchMap(name: string) {
    loading.value = true
    error.value = null
    currentMap.value = null // clear stale data immediately
    try {
      const cfg = await mapsApi.get(name, token())
      // Worldmap maps with auto_source merge transient hosts on top of
      // the persisted set. The merge happens here (not in the editor)
      // so the canvas, drawer and websocket flow all see one object list.
      const wv = cfg.view?.type === 'worldmap' ? cfg.view : null
      if (wv?.auto_source) {
        try {
          const auto = await mapsApi.autoObjects(name, token())
          cfg.objects = [...cfg.objects, ...auto]
        } catch {
          // Auto-source failures shouldn't block the persisted view.
        }
      }
      currentMap.value = cfg
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Failed to load map'
    } finally {
      loading.value = false
    }
  }

  async function createMap(
    name: string,
    alias: string,
    connectionId = 'live_1',
    mapType = 'static',
    iconSize?: number | null,
    renderMode: RenderMode = 'default'
  ) {
    const cfg = await mapsApi.create(
      {
        name,
        alias,
        connection_id: connectionId,
        ...(iconSize !== undefined ? { icon_size: iconSize } : {}),
        view: { type: mapType },
        render_mode: renderMode
      },
      token()
    )
    // In-place append instead of a full re-fetch. MapRead is a projection of
    // MapConfig, so we build the list-shape from the returned config.
    maps.value.push({
      name: cfg.name,
      alias: cfg.alias,
      background_image: cfg.background_image ?? null,
      icon_size: cfg.icon_size,
      connection_id: cfg.connection_id,
      view_type: cfg.view?.type ?? 'static',
      view: cfg.view,
      object_count:
        (cfg.objects?.length ?? 0) +
        (cfg.view?.type === 'presentation' ? (cfg.view.elements?.length ?? 0) : 0),
      rotation_interval: cfg.rotation_interval,
      sort_order: cfg.sort_order,
      click_action: cfg.click_action,
      readonly: cfg.readonly ?? false,
      show_in_lists: true, // MapConfig does not carry this; list endpoint defaults it
      hover_template: cfg.hover_template ?? null,
      context_template: cfg.context_template ?? null,
      render_mode: cfg.render_mode ?? 'default',
      can_edit: true // the creator can always edit their new map
    })
    return cfg
  }

  async function deleteMap(name: string) {
    await mapsApi.delete(name, token())
    maps.value = maps.value.filter((b) => b.name !== name)
  }

  async function bulkDeleteMaps(names: string[]): Promise<MapBulkDeleteResult> {
    const result = await mapsApi.bulkDelete(names, token())
    if (result.deleted.length > 0) {
      const removed = new Set(result.deleted)
      maps.value = maps.value.filter((b) => !removed.has(b.name))
    }
    return result
  }

  async function bulkEditMaps(
    names: string[],
    updates: Record<string, unknown>
  ): Promise<MapBulkEditResult> {
    const result = await mapsApi.bulkEdit(names, updates, token())
    if (result.updated.length > 0) {
      await fetchMaps()
    }
    return result
  }

  async function bulkExportMaps(names: string[]): Promise<void> {
    await mapsApi.bulkExport(names, token())
  }

  return {
    maps,
    currentMap,
    loading,
    error,
    bgRefreshTicks,
    bumpBgRefreshTick,
    fetchMaps,
    fetchMap,
    createMap,
    deleteMap,
    bulkDeleteMaps,
    bulkEditMaps,
    bulkExportMaps
  }
})
