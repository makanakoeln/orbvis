import { type Ref, computed, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import type { TourStep } from '@/types/tour'
import usei18n from '@/vendor/cmk/lib/i18n'

/**
 * First-run guided tour for a board. Non-admins get the two read-only steps
 * (welcome + canvas); admins additionally get the settings/edit-mode/add-object
 * steps. The step click/back hooks toggle edit mode so the EditPanel-anchored
 * steps have something to point at.
 *
 * The host view owns *when* the tour opens (it sets `showBoardTour = true` once
 * per user via localStorage); this composable owns the steps and the edit-mode
 * choreography.
 */
export function useBoardTour(editor: { editMode: Ref<boolean>; toggleEditMode: () => void }) {
  const auth = useAuthStore()
  const { _t } = usei18n()

  const showBoardTour = ref(false)

  const boardTourSteps = computed<TourStep[]>(() => {
    const base: TourStep[] = [
      {
        selector: null,
        title: _t('Welcome to your board'),
        body: _t(
          'This is where your monitoring landscape comes to life. Objects update in real time.'
        )
      },
      {
        selector: '[data-tour="board-canvas"]',
        title: _t('The canvas'),
        body: _t(
          'Each object represents a monitored host, service, or group and shows its current state.'
        )
      }
    ]
    if (!auth.isAdmin) return base
    return [
      ...base,
      {
        selector: '[data-tour="board-settings"]',
        title: _t('Board settings'),
        body: _t(
          'Use the gear icon to open board settings — upload a background image, set a name, and configure auto-rotation.'
        )
      },
      {
        selector: '[data-tour="edit-fab"]',
        title: _t('Edit mode'),
        body: _t(
          'Click the pencil to enter edit mode and start placing monitoring objects on the board.'
        )
      },
      {
        selector: '[data-tour="edit-panel"]',
        title: _t('Add objects'),
        body: _t(
          'Choose an object type, configure it, and click "Place on board" to position it on the canvas.'
        )
      }
    ]
  })

  function onBoardTourStepClick(step: number): void {
    // Step 4 = FAB — ensure edit mode is ON so EditPanel renders for step 5
    if (auth.isAdmin && step === 4 && !editor.editMode.value) {
      editor.toggleEditMode()
    }
  }

  function onBoardTourStepBack(step: number): void {
    // Leaving step 5 backwards — ensure edit mode is OFF
    if (auth.isAdmin && step === 5 && editor.editMode.value) {
      editor.toggleEditMode()
    }
  }

  return { showBoardTour, boardTourSteps, onBoardTourStepClick, onBoardTourStepBack }
}
