import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MapCanvas from './MapCanvas.vue'
import type { MapConfig, ObjectState } from '@/types/api'

const sampleConfig: MapConfig = {
  name: 'test',
  globals: { alias: 'Test', icon_size: 22, backend_id: 'test' },
  objects: [
    {
      id: '1',
      type: 'host',
      x: 100,
      y: 200,
      host_name: 'localhost',
      view_type: 'icon',
      label_show: true,
      extra: {},
    },
  ],
}

const sampleStates: Record<string, ObjectState> = {
  '1': {
    object_id: '1',
    type: 'host',
    state: 'UP',
    output: 'PING OK',
    acknowledged: false,
    in_downtime: false,
    stale: false,
  },
}

describe('MapCanvas', () => {
  it('renders without errors', () => {
    const wrapper = mount(MapCanvas, {
      props: { config: sampleConfig, states: sampleStates },
      global: { stubs: { HoverMenu: true, ContextMenu: true } },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the correct number of objects', () => {
    const wrapper = mount(MapCanvas, {
      props: { config: sampleConfig, states: sampleStates },
      global: { stubs: { HoverMenu: true, ContextMenu: true, MapLine: true } },
    })
    // MapObject components rendered (non-line objects)
    const objects = wrapper.findAllComponents({ name: 'MapObject' })
    expect(objects).toHaveLength(1)
  })
})
