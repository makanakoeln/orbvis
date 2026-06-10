import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, defineComponent, ref } from 'vue'

import type { BoardRead } from '@/types/api'

import { useBoardRotation } from './useBoardRotation'

const { push, store } = vi.hoisted(() => ({
  push: vi.fn(),
  store: {
    boards: [] as BoardRead[],
    fetchBoards: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/stores/boards', () => ({ useBoardsStore: () => store }))

function board(name: string, rotationInterval: number): BoardRead {
  return { name, alias: name, rotation_interval: rotationInterval } as BoardRead
}

function mountRotation(boardName: Ref<string>, editMode: Ref<boolean> = ref(false)) {
  let api!: ReturnType<typeof useBoardRotation>
  const Host = defineComponent({
    setup() {
      api = useBoardRotation(boardName, editMode)
      return () => null
    }
  })
  const wrapper = mount(Host)
  return { api, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  store.boards = []
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useBoardRotation — rotation', () => {
  it('counts down once per second and navigates to the next rotating board', async () => {
    store.boards = [board('a', 3), board('b', 5), board('static', 0)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(3)
    expect(api.rotationCountdown.value).toBe(3)

    await vi.advanceTimersByTimeAsync(2000)
    expect(api.rotationCountdown.value).toBe(1)
    expect(push).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1000)
    expect(push).toHaveBeenCalledWith({ name: 'board', params: { name: 'b' } })
    expect(api.rotationCountdown.value).toBe(0)
  })

  it('wraps from the last rotating board back to the first', async () => {
    store.boards = [board('a', 3), board('b', 3)]
    const { api } = mountRotation(ref('b'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(push).toHaveBeenCalledWith({ name: 'board', params: { name: 'a' } })
  })

  it('fetches boards on demand when the store is empty', async () => {
    store.fetchBoards.mockImplementationOnce(async () => {
      store.boards = [board('a', 3), board('b', 3)]
    })
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(store.fetchBoards).toHaveBeenCalledOnce()
    expect(push).toHaveBeenCalledWith({ name: 'board', params: { name: 'b' } })
  })

  it('does not navigate when fewer than two boards rotate', async () => {
    store.boards = [board('a', 3), board('static', 0)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(push).not.toHaveBeenCalled()
  })

  it('does not start a countdown for a non-positive interval', async () => {
    store.boards = [board('a', 3), board('b', 3)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(0)
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(push).not.toHaveBeenCalled()
  })
})

describe('useBoardRotation — pause and edit mode', () => {
  it('freezes the countdown while paused and resumes after unpausing', async () => {
    store.boards = [board('a', 2), board('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)

    api.toggleRotationPause()
    expect(api.rotationPaused.value).toBe(true)
    await vi.advanceTimersByTimeAsync(5000)
    expect(api.rotationCountdown.value).toBe(2)
    expect(push).not.toHaveBeenCalled()

    api.toggleRotationPause()
    await vi.advanceTimersByTimeAsync(2000)
    expect(push).toHaveBeenCalledWith({ name: 'board', params: { name: 'b' } })
  })

  it('does not start rotating while in edit mode', async () => {
    store.boards = [board('a', 2), board('b', 2)]
    const { api } = mountRotation(ref('a'), ref(true))
    api.scheduleRotation(2)
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(push).not.toHaveBeenCalled()
  })

  it('suspends a running countdown when edit mode is entered', async () => {
    store.boards = [board('a', 2), board('b', 2)]
    const editMode = ref(false)
    const { api } = mountRotation(ref('a'), editMode)
    api.scheduleRotation(2)

    editMode.value = true
    await vi.advanceTimersByTimeAsync(5000)
    expect(api.rotationCountdown.value).toBe(2)
    expect(push).not.toHaveBeenCalled()

    editMode.value = false
    await vi.advanceTimersByTimeAsync(2000)
    expect(push).toHaveBeenCalled()
  })
})

describe('useBoardRotation — teardown', () => {
  it('stopRotation cancels the pending navigation and resets the countdown', async () => {
    store.boards = [board('a', 2), board('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    api.stopRotation()
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(push).not.toHaveBeenCalled()
  })

  it('rescheduling replaces the previous timer instead of stacking it', async () => {
    store.boards = [board('a', 2), board('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    await vi.advanceTimersByTimeAsync(1000)
    api.scheduleRotation(5)
    expect(api.rotationCountdown.value).toBe(5)

    // Were the old timer still alive, navigation would fire after 1 more second.
    await vi.advanceTimersByTimeAsync(1000)
    expect(push).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(4000)
    expect(push).toHaveBeenCalledOnce()
  })

  it('clears the timer on unmount', async () => {
    store.boards = [board('a', 2), board('b', 2)]
    const { api, wrapper } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    wrapper.unmount()
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(push).not.toHaveBeenCalled()
  })
})
