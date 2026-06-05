/**
 * Routing guard for views with unsaved changes.
 *
 * Returns reactive state for a confirm dialog that the view can render with
 * a Checkmk-native `CmkDialog`, plus a resolver so the dialog buttons can
 * decide whether navigation goes through. Also wires the native
 * `beforeunload` listener for hard-refresh / tab-close.
 */
import type { Ref } from 'vue'
import { onMounted, onUnmounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

export interface UnsavedChangesGuard {
  dialogOpen: Ref<boolean>
  confirmLeave: () => void
  cancelLeave: () => void
}

export function useUnsavedChangesGuard(dirty: Ref<boolean>): UnsavedChangesGuard {
  const dialogOpen = ref(false)
  let pendingResolve: ((leave: boolean) => void) | null = null

  function beforeUnloadHandler(event: BeforeUnloadEvent) {
    if (!dirty.value) return
    event.preventDefault()
    event.returnValue = ''
  }

  onMounted(() => {
    window.addEventListener('beforeunload', beforeUnloadHandler)
  })

  onUnmounted(() => {
    window.removeEventListener('beforeunload', beforeUnloadHandler)
  })

  onBeforeRouteLeave(() => {
    if (!dirty.value) return true
    dialogOpen.value = true
    return new Promise<boolean>((resolve) => {
      pendingResolve = resolve
    })
  })

  function confirmLeave() {
    dialogOpen.value = false
    pendingResolve?.(true)
    pendingResolve = null
  }

  function cancelLeave() {
    dialogOpen.value = false
    pendingResolve?.(false)
    pendingResolve = null
  }

  return { dialogOpen, confirmLeave, cancelLeave }
}
