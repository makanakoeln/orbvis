import { computed, ref } from 'vue'

// Snapshot-based undo/redo. The owner holds the live state and asks this stack
// to record a snapshot *before* each committed change; undo/redo hand back the
// snapshot to apply. State is serialised so snapshots are immutable copies.
export function useHistory<T>(
  serialize: (v: T) => string,
  deserialize: (s: string) => T,
  limit = 100
) {
  const past = ref<string[]>([])
  const future = ref<string[]>([])

  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)

  function record(current: T): void {
    past.value.push(serialize(current))
    if (past.value.length > limit) past.value.shift()
    future.value = []
  }

  function undo(current: T): T | null {
    if (past.value.length === 0) return null
    future.value.push(serialize(current))
    return deserialize(past.value.pop() as string)
  }

  function redo(current: T): T | null {
    if (future.value.length === 0) return null
    past.value.push(serialize(current))
    return deserialize(future.value.pop() as string)
  }

  function reset(): void {
    past.value = []
    future.value = []
  }

  return { canUndo, canRedo, record, undo, redo, reset }
}
