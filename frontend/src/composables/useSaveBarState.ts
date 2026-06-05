/**
 * State machine for a settings-page save bar.
 *
 * Maps the four boolean inputs from a settings view (dirty, saving,
 * savedOk, error) to a single state and the CmkAlertBox variant + heading
 * text the view should render. Keeps the FormSpec-driven views (Global +
 * System settings) from duplicating the same conditionals.
 */
import type { Ref } from 'vue'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

export type SaveBarState = 'clean' | 'dirty' | 'saving' | 'saved' | 'error'
export type SaveBarVariant = 'warning' | 'loading' | 'success' | 'error'

export interface SaveBarSources {
  dirty: Ref<boolean>
  saving: Ref<boolean>
  savedOk: Ref<boolean>
  error: Ref<string>
}

export function useSaveBarState(sources: SaveBarSources) {
  const { t } = useI18n()

  const state = computed<SaveBarState>(() => {
    if (sources.error.value) return 'error'
    if (sources.saving.value) return 'saving'
    if (sources.savedOk.value) return 'saved'
    if (sources.dirty.value) return 'dirty'
    return 'clean'
  })

  // Dirty maps to "warning" because it's an attention state. The other
  // three states map 1:1 to the CmkAlertBox variants.
  const variant = computed<SaveBarVariant>(() => {
    switch (state.value) {
      case 'saving':
        return 'loading'
      case 'saved':
        return 'success'
      case 'error':
        return 'error'
      default:
        return 'warning'
    }
  })

  const hasActions = computed(() => state.value === 'dirty' || state.value === 'error')

  const heading = computed(() => {
    switch (state.value) {
      case 'dirty':
        return t('common.unsavedChanges')
      case 'saving':
        return t('common.saving')
      case 'saved':
        return t('common.saved')
      case 'error':
        return sources.error.value
      default:
        return ''
    }
  })

  return { state, variant, hasActions, heading }
}
