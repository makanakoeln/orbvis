import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { BoardConfig, ObjectState } from '@/types/api'

import BoardCanvas from './BoardCanvas.vue'

const sampleConfig: BoardConfig = {
  name: 'test',
  alias: 'Test',
  icon_size: 30,
  connection_id: 'test',
  rotation_interval: 0,
  sort_order: 0,
  click_action: 'link',
  view: { type: 'static' },
  objects: [
    {
      id: '1',
      type: 'host',
      x: 100,
      y: 200,
      host_name: 'localhost',
      label: {
        show: true,
        x: 0,
        y: 0,
        size: 10,
        color: '#ffffff',
        background: 'transparent'
      },
      display: { mode: 'icon' },
      url_target: '_blank',
      z: 1
    }
  ]
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
    stale: false
  }
}

const baseProps = {
  config: sampleConfig,
  states: sampleStates,
  editMode: false,
  placing: false,
  lineDragPositions: {},
  selectedObjectId: null
}

describe('BoardCanvas', () => {
  it('renders without errors', () => {
    const wrapper = mount(BoardCanvas, {
      props: baseProps,
      global: { stubs: { HoverMenu: true, ContextMenu: true, BoardObject: true } }
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('renders the correct number of objects', () => {
    const wrapper = mount(BoardCanvas, {
      props: baseProps,
      global: {
        stubs: { HoverMenu: true, ContextMenu: true, BoardLine: true, BoardObject: true }
      }
    })
    const objects = wrapper.findAllComponents({ name: 'BoardObject' })
    expect(objects).toHaveLength(1)
  })

  it('buckets lines into one z-indexed SVG layer per distinct z', () => {
    const line = (id: string, z: number | null) => ({
      id,
      type: 'line' as const,
      x: 0,
      y: 0,
      x2: 50,
      y2: 50,
      label: { show: false, x: 0, y: 0, size: 10, color: '#fff', background: 'transparent' },
      url_target: '_blank',
      ...(z === null ? {} : { z })
    })
    const wrapper = mount(BoardCanvas, {
      props: {
        ...baseProps,
        // default_z=10 so the z-less line shares a layer with the z=10 line.
        config: {
          ...sampleConfig,
          default_z: 10,
          objects: [line('a', 2), line('b', 20), line('c', null), line('d', 10)]
        }
      },
      global: {
        stubs: { HoverMenu: true, ContextMenu: true, BoardLine: true, BoardObject: true }
      }
    })
    const zLayers = wrapper
      .findAll('svg')
      .map((s) => s.attributes('style') ?? '')
      .filter((style) => style.includes('z-index'))
      .map((style) => parseInt(style.match(/z-index:\s*(\d+)/)?.[1] ?? '', 10))
    // Three distinct buckets (2, 10, 20) sorted ascending; z-less + z=10 merge.
    expect(zLayers).toEqual([2, 10, 20])
  })
})
