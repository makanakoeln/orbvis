import { computed, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import type { BoardListView } from '@/types/api'
import usei18n from '@/vendor/cmk/lib/i18n'

/**
 * Cards-vs-table choice for the board list. A per-user override is persisted in
 * localStorage (keyed by user id) and read synchronously at setup so the first
 * render honours it; the global `board_list_view` setting is only the default.
 * Falls back gracefully when localStorage is unavailable (private mode).
 */
export function useBoardListViewMode() {
  const auth = useAuthStore()
  const settingsStore = useSettingsStore()
  const { _t } = usei18n()

  function viewModeStorageKey(): string {
    return `orbvis_board_list_view_${auth.user?.user_id ?? 'anon'}`
  }
  function readStoredViewMode(): BoardListView | null {
    const v = localStorage.getItem(viewModeStorageKey())
    return v === 'table' || v === 'cards' ? v : null
  }
  const localViewMode = ref<BoardListView | null>(readStoredViewMode())

  const viewMode = computed<BoardListView>(
    () =>
      localViewMode.value ??
      (settingsStore.settings.board_list_view === 'table' ? 'table' : 'cards')
  )
  const viewModeOptions = computed(() => [
    { label: _t('Cards'), value: 'cards' },
    { label: _t('Table'), value: 'table' }
  ])

  function setViewMode(value: string) {
    const next: BoardListView = value === 'table' ? 'table' : 'cards'
    if (viewMode.value === next) return
    localViewMode.value = next
    try {
      localStorage.setItem(viewModeStorageKey(), next)
    } catch {
      // localStorage unavailable (e.g. private mode); the in-memory ref still applies.
    }
  }

  return { viewMode, viewModeOptions, setViewMode }
}
