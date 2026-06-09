import { type Ref, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useBoardsStore } from '@/stores/boards'

/**
 * Auto-rotation for boards with a positive `rotation_interval`: counts down
 * once per second and navigates to the next rotating board when it reaches
 * zero. Pausing freezes the countdown; edit mode suspends rotation entirely.
 *
 * Wire-up per host view:
 *   const rotation = useBoardRotation(boardName, editor.editMode)
 *   rotation.scheduleRotation(cfg?.rotation_interval ?? 0)  // on board load
 *   rotation.stopRotation()                                  // before reload
 *
 * The countdown timer is cleared automatically on unmount.
 */
export function useBoardRotation(boardName: Ref<string>, editMode: Ref<boolean>) {
  const router = useRouter()
  const boardsStore = useBoardsStore()

  let rotationTimer: ReturnType<typeof setInterval> | null = null
  const rotationCountdown = ref(0)
  const rotationPaused = ref(false)

  function stopRotation(): void {
    if (rotationTimer !== null) {
      clearInterval(rotationTimer)
      rotationTimer = null
    }
    rotationCountdown.value = 0
  }

  async function goToNextBoard(): Promise<void> {
    if (boardsStore.boards.length === 0) await boardsStore.fetchBoards()
    const pool = boardsStore.boards.filter((b) => (b.rotation_interval ?? 0) > 0)
    if (pool.length < 2) return
    const idx = pool.findIndex((b) => b.name === boardName.value)
    const next = pool[(idx + 1) % pool.length]
    if (!next) return
    router.push({ name: 'board', params: { name: next.name } })
  }

  function scheduleRotation(intervalSeconds: number): void {
    stopRotation()
    rotationPaused.value = false
    if (intervalSeconds <= 0 || editMode.value) return
    rotationCountdown.value = intervalSeconds
    rotationTimer = setInterval(() => {
      if (rotationPaused.value || editMode.value) return
      rotationCountdown.value--
      if (rotationCountdown.value <= 0) {
        stopRotation()
        goToNextBoard()
      }
    }, 1000)
  }

  function toggleRotationPause(): void {
    rotationPaused.value = !rotationPaused.value
  }

  onUnmounted(stopRotation)

  return { rotationCountdown, rotationPaused, stopRotation, scheduleRotation, toggleRotationPause }
}
