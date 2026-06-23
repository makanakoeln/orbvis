import { ref } from 'vue'

/**
 * "Top-K problem hosts" hint dismissal for the flow map. The hint explains a
 * fixed concept, so once an operator understands it they can banish it for good
 * — persisted across maps/reloads, scoped per user so one operator's
 * dismissal doesn't hide it from another sharing the browser (matches the
 * onboarding-tour key convention).
 */
export function useTopKHint(userId: () => string | number | undefined) {
  const key = `orbvis.flow.topkHintDismissed.${userId() ?? 'anon'}`
  const topKHintDismissed = ref(
    typeof window !== 'undefined' && window.localStorage?.getItem(key) === '1'
  )

  function dismissTopKHint(): void {
    topKHintDismissed.value = true
    try {
      window.localStorage?.setItem(key, '1')
    } catch {
      // Private mode or storage full — the dismissal only lasts this session.
    }
  }

  return { topKHintDismissed, dismissTopKHint }
}
