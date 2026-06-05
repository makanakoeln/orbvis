import { onMounted, onUnmounted } from 'vue'

/**
 * Bind Escape on the window to a close callback for the lifetime of the
 * calling component. Modals across OrbVis used to swallow Escape because
 * each one rolled its own backdrop click but no keyboard fallback —
 * operators reaching for the key got stuck. This composable centralises
 * the behaviour so every modal closes the same way.
 */
export function useEscapeClose(close: () => void): void {
  function onKey(e: KeyboardEvent): void {
    if (e.key === 'Escape') close()
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onUnmounted(() => window.removeEventListener('keydown', onKey))
}
