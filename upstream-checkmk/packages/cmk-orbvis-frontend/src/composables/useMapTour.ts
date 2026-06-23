import { type Ref, computed, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import type { TourStep } from '@/types/tour'
import usei18n from '@cmk/lib/i18n'

/**
 * First-run guided tour for a map. Non-admins get the two read-only steps
 * (welcome + canvas); admins additionally get the settings/edit-mode/add-object
 * steps. The step click/back hooks toggle edit mode so the EditPanel-anchored
 * steps have something to point at.
 *
 * The host view owns *when* the tour opens (it sets `showMapTour = true` once
 * per user via localStorage); this composable owns the steps and the edit-mode
 * choreography.
 */
export function useMapTour(editor: { editMode: Ref<boolean>; toggleEditMode: () => void }) {
  const auth = useAuthStore()
  const { _t } = usei18n()

  const showMapTour = ref(false)

  const mapTourSteps = computed<TourStep[]>(() => {
    const base: TourStep[] = [
      {
        selector: null,
        title: _t('Welcome to your map'),
        body: _t(
          'This is where your monitoring landscape comes to life. Objects update in real time.'
        )
      },
      {
        selector: '[data-tour="map-canvas"]',
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
        selector: '[data-tour="map-settings"]',
        title: _t('Map settings'),
        body: _t(
          'Use the gear icon to open map settings — upload a background image, set a name, and configure auto-rotation.'
        )
      },
      {
        selector: '[data-tour="edit-fab"]',
        title: _t('Edit mode'),
        body: _t(
          'Click the pencil to enter edit mode and start placing monitoring objects on the map.'
        )
      },
      {
        selector: '[data-tour="edit-panel"]',
        title: _t('Add objects'),
        body: _t(
          'Choose an object type, configure it, and click "Place on map" to position it on the canvas.'
        )
      }
    ]
  })

  function onMapTourStepClick(step: number): void {
    // Step 4 = FAB — ensure edit mode is ON so EditPanel renders for step 5
    if (auth.isAdmin && step === 4 && !editor.editMode.value) {
      editor.toggleEditMode()
    }
  }

  function onMapTourStepBack(step: number): void {
    // Leaving step 5 backwards — ensure edit mode is OFF
    if (auth.isAdmin && step === 5 && editor.editMode.value) {
      editor.toggleEditMode()
    }
  }

  return { showMapTour, mapTourSteps, onMapTourStepClick, onMapTourStepBack }
}
