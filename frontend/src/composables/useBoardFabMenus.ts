import { computed, ref, watch } from 'vue'

import type { useBoardEditor } from '@/composables/useBoardEditor'
import { useSettingsStore } from '@/stores/settings'
import type { ObjectType } from '@/types/api'
import { placeableObjectTypes } from '@/utils/dropdownOptions'
import usei18n from '@/vendor/cmk/lib/i18n'

type BoardEditor = ReturnType<typeof useBoardEditor>

/**
 * The two edit-mode FAB popup menus on a board:
 *  - the "add object" type picker (anchored above the "+" FAB)
 *  - the grid-snap size menu
 *
 * Both are pure UI-state holders driven by the shared board editor. The
 * `v-click-outside` directives in the template call `closeAddPicker` /
 * `closeGridMenu`; the global Escape handler closes the add picker via the
 * returned `addPickerOpen` ref.
 */
export function useBoardFabMenus(editor: BoardEditor) {
  const settingsStore = useSettingsStore()
  const { _t } = usei18n()

  // ---- Add-object type picker ----
  const addPickerOpen = ref(false)
  const placeableTypeOptions = computed(() =>
    placeableObjectTypes(_t, settingsStore.system.enable_graph_objects)
  )

  function chooseAddType(type: ObjectType): void {
    editor.draft.type = type
    addPickerOpen.value = false
  }

  function onAddFabClick(): void {
    if (editor.draft.type) {
      editor.resetDraft()
      addPickerOpen.value = true
    } else {
      addPickerOpen.value = !addPickerOpen.value
    }
  }

  function closeAddPicker(): void {
    addPickerOpen.value = false
  }

  // Leaving edit mode dismisses the picker so it can't linger over a read-only board.
  watch(
    () => editor.editMode.value,
    (on) => {
      if (!on) addPickerOpen.value = false
    }
  )

  // ---- Grid-snap menu ----
  const gridMenuOpen = ref(false)
  const gridSnapActive = computed(() => editor.snapGrid.value > 0)
  const gridSizeOptions = computed(() => [
    { value: 0, label: _t('Off') },
    { value: 10, label: '10 px' },
    { value: 20, label: '20 px' },
    { value: 50, label: '50 px' }
  ])

  function pickGrid(value: number): void {
    editor.snapGrid.value = value
    gridMenuOpen.value = false
  }

  function closeGridMenu(): void {
    gridMenuOpen.value = false
  }

  return {
    addPickerOpen,
    placeableTypeOptions,
    chooseAddType,
    onAddFabClick,
    closeAddPicker,
    gridMenuOpen,
    gridSnapActive,
    gridSizeOptions,
    pickGrid,
    closeGridMenu
  }
}
