import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, defineComponent, ref } from 'vue'

import type { MapRead } from '@/types/api'

import { useMapRotation } from './useMapRotation'

const { push, store } = vi.hoisted(() => ({
  push: vi.fn(),
  store: {
    maps: [] as MapRead[],
    fetchMaps: vi.fn().mockResolvedValue(undefined)
  }
}))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('@/stores/maps', () => ({ useMapsStore: () => store }))

function map(name: string, rotationInterval: number): MapRead {
  return { name, alias: name, rotation_interval: rotationInterval } as MapRead
}

function mountRotation(mapName: Ref<string>, editMode: Ref<boolean> = ref(false)) {
  let api!: ReturnType<typeof useMapRotation>
  const Host = defineComponent({
    setup() {
      api = useMapRotation(mapName, editMode)
      return () => null
    }
  })
  const wrapper = mount(Host)
  return { api, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  store.maps = []
})

afterEach(() => {
  vi.useRealTimers()
})

describe('useMapRotation — rotation', () => {
  it('counts down once per second and navigates to the next rotating map', async () => {
    store.maps = [map('a', 3), map('b', 5), map('static', 0)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(3)
    expect(api.rotationCountdown.value).toBe(3)

    await vi.advanceTimersByTimeAsync(2000)
    expect(api.rotationCountdown.value).toBe(1)
    expect(push).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(1000)
    expect(push).toHaveBeenCalledWith({ name: 'map', params: { name: 'b' } })
    expect(api.rotationCountdown.value).toBe(0)
  })

  it('wraps from the last rotating map back to the first', async () => {
    store.maps = [map('a', 3), map('b', 3)]
    const { api } = mountRotation(ref('b'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(push).toHaveBeenCalledWith({ name: 'map', params: { name: 'a' } })
  })

  it('fetches maps on demand when the store is empty', async () => {
    store.fetchMaps.mockImplementationOnce(async () => {
      store.maps = [map('a', 3), map('b', 3)]
    })
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(store.fetchMaps).toHaveBeenCalledOnce()
    expect(push).toHaveBeenCalledWith({ name: 'map', params: { name: 'b' } })
  })

  it('does not navigate when fewer than two maps rotate', async () => {
    store.maps = [map('a', 3), map('static', 0)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(push).not.toHaveBeenCalled()
  })

  it('does not start a countdown for a non-positive interval', async () => {
    store.maps = [map('a', 3), map('b', 3)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(0)
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(10_000)
    expect(push).not.toHaveBeenCalled()
  })
})

describe('useMapRotation — pause and edit mode', () => {
  it('freezes the countdown while paused and resumes after unpausing', async () => {
    store.maps = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)

    api.toggleRotationPause()
    expect(api.rotationPaused.value).toBe(true)
    await vi.advanceTimersByTimeAsync(5000)
    expect(api.rotationCountdown.value).toBe(2)
    expect(push).not.toHaveBeenCalled()

    api.toggleRotationPause()
    await vi.advanceTimersByTimeAsync(2000)
    expect(push).toHaveBeenCalledWith({ name: 'map', params: { name: 'b' } })
  })

  it('does not start rotating while in edit mode', async () => {
    store.maps = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'), ref(true))
    api.scheduleRotation(2)
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(push).not.toHaveBeenCalled()
  })

  it('suspends a running countdown when edit mode is entered', async () => {
    store.maps = [map('a', 2), map('b', 2)]
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

describe('useMapRotation — teardown', () => {
  it('stopRotation cancels the pending navigation and resets the countdown', async () => {
    store.maps = [map('a', 2), map('b', 2)]
    const { api } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    api.stopRotation()
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(push).not.toHaveBeenCalled()
  })

  it('rescheduling replaces the previous timer instead of stacking it', async () => {
    store.maps = [map('a', 2), map('b', 2)]
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
    store.maps = [map('a', 2), map('b', 2)]
    const { api, wrapper } = mountRotation(ref('a'))
    api.scheduleRotation(2)
    wrapper.unmount()
    expect(api.rotationCountdown.value).toBe(0)
    await vi.advanceTimersByTimeAsync(5000)
    expect(push).not.toHaveBeenCalled()
  })
})
