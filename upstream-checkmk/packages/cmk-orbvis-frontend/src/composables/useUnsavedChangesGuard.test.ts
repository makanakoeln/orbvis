import { type VueWrapper, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { type Ref, defineComponent, ref } from 'vue'

import { type UnsavedChangesGuard, useUnsavedChangesGuard } from './useUnsavedChangesGuard'

type RouteLeaveGuard = () => boolean | Promise<boolean> | undefined

const { routeLeaveGuards } = vi.hoisted(() => ({
  routeLeaveGuards: [] as RouteLeaveGuard[]
}))

vi.mock('vue-router', () => ({
  onBeforeRouteLeave: (guard: RouteLeaveGuard) => {
    routeLeaveGuards.push(guard)
  }
}))

const mountedWrappers: VueWrapper[] = []

function mountGuard(dirty: Ref<boolean>) {
  let api!: UnsavedChangesGuard
  const Host = defineComponent({
    setup() {
      api = useUnsavedChangesGuard(dirty)
      return () => null
    }
  })
  const wrapper = mount(Host)
  mountedWrappers.push(wrapper)
  const routeGuard = routeLeaveGuards[routeLeaveGuards.length - 1]!
  return { api, wrapper, routeGuard }
}

function dispatchBeforeUnload(): Event {
  // jsdom has no BeforeUnloadEvent constructor; a cancelable plain Event
  // exercises the same preventDefault path.
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event
}

beforeEach(() => {
  routeLeaveGuards.length = 0
})

afterEach(() => {
  // Unmount every host so leftover beforeunload listeners cannot leak into
  // the next test's window.
  mountedWrappers.splice(0).forEach((wrapper) => wrapper.unmount())
})

describe('useUnsavedChangesGuard — beforeunload', () => {
  it('does not block unload while clean', () => {
    mountGuard(ref(false))
    expect(dispatchBeforeUnload().defaultPrevented).toBe(false)
  })

  it('blocks unload while dirty', () => {
    mountGuard(ref(true))
    expect(dispatchBeforeUnload().defaultPrevented).toBe(true)
  })

  it('reacts to the dirty flag changing after mount', () => {
    const dirty = ref(false)
    mountGuard(dirty)
    dirty.value = true
    expect(dispatchBeforeUnload().defaultPrevented).toBe(true)
  })

  it('removes the listener on unmount so unload is no longer blocked', () => {
    const { wrapper } = mountGuard(ref(true))
    wrapper.unmount()
    expect(dispatchBeforeUnload().defaultPrevented).toBe(false)
  })
})

describe('useUnsavedChangesGuard — route-leave guard', () => {
  it('allows navigation immediately while clean, without opening the dialog', () => {
    const { api, routeGuard } = mountGuard(ref(false))
    expect(routeGuard()).toBe(true)
    expect(api.dialogOpen.value).toBe(false)
  })

  it('opens the dialog while dirty and resolves true on confirmLeave', async () => {
    const { api, routeGuard } = mountGuard(ref(true))
    const decision = routeGuard()
    expect(decision).toBeInstanceOf(Promise)
    expect(api.dialogOpen.value).toBe(true)
    api.confirmLeave()
    expect(api.dialogOpen.value).toBe(false)
    await expect(decision).resolves.toBe(true)
  })

  it('resolves false on cancelLeave so navigation is blocked', async () => {
    const { api, routeGuard } = mountGuard(ref(true))
    const decision = routeGuard()
    api.cancelLeave()
    expect(api.dialogOpen.value).toBe(false)
    await expect(decision).resolves.toBe(false)
  })

  it('handles a second navigation attempt after a cancelled one', async () => {
    const { api, routeGuard } = mountGuard(ref(true))
    const first = routeGuard()
    api.cancelLeave()
    await expect(first).resolves.toBe(false)

    const second = routeGuard()
    expect(api.dialogOpen.value).toBe(true)
    api.confirmLeave()
    await expect(second).resolves.toBe(true)
  })
})
