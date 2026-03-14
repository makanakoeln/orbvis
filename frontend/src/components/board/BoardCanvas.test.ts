import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BoardCanvas from './BoardCanvas.vue'
import type { BoardConfig, ObjectState } from '@/types/api'

const sampleConfig: BoardConfig = {
  name: 'test',
  alias: 'Test',
  icon_size: 30,
  backend_id: 'test',
  rotation_interval: 0,
  view: { type: 'static' },
  objects: [
    {
      id: '1',
      type: 'host',
      x: 100,
      y: 200,
      host_name: 'localhost',
      label: { show: true, x: 0, y: 0, size: 10, color: '#ffffff', background: 'transparent' },
      display: { mode: 'icon' },
      url_target: '_blank', z: 1,
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
  lineDragPositions: {},
  selectedObjectId: null,
}

describe('BoardCanvas', () => {
  it('renders without errors', () => {
    const wrapper = mount(BoardCanvas, {
      props: baseProps,
      global: { stubs: { HoverMenu: true, ContextMenu: true } },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the correct number of objects', () => {
    const wrapper = mount(BoardCanvas, {
      props: baseProps,
      global: { stubs: { HoverMenu: true, ContextMenu: true, BoardLine: true } },
    })
    const objects = wrapper.findAllComponents({ name: 'BoardObject' })
    expect(objects).toHaveLength(1)
  })
})
