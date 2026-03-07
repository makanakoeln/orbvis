import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MapCanvas from './MapCanvas.vue'
import type { MapConfig, ObjectState } from '@/types/api'

const sampleConfig: MapConfig = {
  name: 'test',
  globals: {
    alias: 'Test', icon_size: 22, backend_id: 'test',
    map_type: 'regular', worldmap_lat: 0, worldmap_lng: 0, worldmap_zoom: 5,
  },
  objects: [
    {
      id: '1',
      type: 'host',
      x: 100,
      y: 200,
      host_name: 'localhost',
      view_type: 'icon',
      label_show: true,
      label_x: 0, label_y: 0, label_size: 10, label_color: '#ffffff', label_background: 'transparent',
      url_target: '_blank', z: 1,
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
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false,
  },
}

const baseProps = {
  config: sampleConfig,
  states: sampleStates,
  editMode: false,
  placing: false,
  draggingId: null,
  dragPositions: {},
  lineDragPositions: {},
  selectedObjectId: null,
}

describe('MapCanvas', () => {
  it('renders without errors', () => {
    const wrapper = mount(MapCanvas, {
      props: baseProps,
      global: { stubs: { HoverMenu: true, ContextMenu: true } },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the correct number of objects', () => {
    const wrapper = mount(MapCanvas, {
      props: baseProps,
      global: { stubs: { HoverMenu: true, ContextMenu: true, MapLine: true } },
    })
    const objects = wrapper.findAllComponents({ name: 'MapObject' })
    expect(objects).toHaveLength(1)
  })
})
