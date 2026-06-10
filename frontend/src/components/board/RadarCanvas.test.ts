import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { ObjectState } from '@/types/api'

import RadarCanvas from './RadarCanvas.vue'

function makeState(overrides: Partial<ObjectState> & { object_id: string }): ObjectState {
  return {
    type: 'host',
    state: 'UP',
    output: '',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false,
    ...overrides
  }
}

const sampleStates: Record<string, ObjectState> = {
  'web-01': makeState({ object_id: 'web-01', state: 'UP', output: 'PING OK' }),
  'db-01;Disk usage': makeState({
    object_id: 'db-01;Disk usage',
    type: 'service',
    state: 'CRITICAL',
    output: 'Disk full'
  }),
  'app-01': makeState({ object_id: 'app-01', state: 'WARNING', output: 'Load high' })
}

describe('RadarCanvas', () => {
  it('renders one card per state, worst state first', () => {
    const wrapper = mount(RadarCanvas, { props: { states: sampleStates } })

    const cards = wrapper.findAll('.orb-radar__card')
    expect(cards).toHaveLength(3)
    // Severity sort: CRITICAL before WARNING before UP.
    expect(cards[0]!.classes()).toContain('orb-radar__card--crit')
    expect(cards[0]!.text()).toContain('db-01 · Disk usage')
    expect(cards[1]!.classes()).toContain('orb-radar__card--warn')
    expect(cards[2]!.classes()).toContain('orb-radar__card--ok')
    expect(wrapper.find('.orb-radar__count').text()).toContain('3 objects')
  })

  it('shows the summary legend with per-state counts', () => {
    const wrapper = mount(RadarCanvas, { props: { states: sampleStates } })

    const legend = wrapper.findAll('.orb-radar__sum').map((s) => s.text())
    expect(legend).toEqual(['1 CRITICAL', '1 WARNING', '1 UP'])
  })

  it('renders the empty state when no objects match', () => {
    const wrapper = mount(RadarCanvas, { props: { states: {} } })

    expect(wrapper.findAll('.orb-radar__card')).toHaveLength(0)
    expect(wrapper.find('.orb-radar__empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('No objects found')
  })

  it('emits object-click with a synthesized board object', async () => {
    const wrapper = mount(RadarCanvas, { props: { states: sampleStates } })

    await wrapper.findAll('.orb-radar__card')[0]!.trigger('click')
    const emitted = wrapper.emitted('object-click')
    expect(emitted).toHaveLength(1)
    expect(emitted![0]![0]).toMatchObject({
      type: 'service',
      host_name: 'db-01',
      service_description: 'Disk usage'
    })
  })
})
