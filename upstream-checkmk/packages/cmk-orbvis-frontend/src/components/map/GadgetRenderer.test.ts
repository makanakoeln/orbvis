import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { MetricUnitMap, ObjectState } from '@/types/api'

import GadgetRenderer from './GadgetRenderer.vue'

function makeState(overrides: Partial<ObjectState> = {}): ObjectState {
  return {
    object_id: 'srv-01;Memory',
    type: 'service',
    state: 'OK',
    output: 'Memory OK',
    perf_data: 'mem_used=8927830016B;;;0;17179869184',
    acknowledged: false,
    in_downtime: false,
    stale: false,
    ...overrides
  }
}

const units: MetricUnitMap = {
  mem_used: { notation: 'iec', symbol: 'B', precision: { type: 'auto', digits: 2 }, scale: 1 }
}

describe('GadgetRenderer value gadget', () => {
  it('renders the registry-formatted reading in the state colour', () => {
    const wrapper = mount(GadgetRenderer, {
      props: {
        type: 'value',
        state: makeState({ state: 'CRITICAL' }),
        size: 60,
        metricUnits: units
      }
    })

    const raw = wrapper.find('.orb-gadget__raw')
    expect(raw.text()).toBe('8.31 GiB')
    // CRITICAL red from the canonical state palette.
    expect(raw.attributes('style')).toContain('color: rgb(248, 113, 113)')
  })

  it('falls back to the SI heuristic without a registry entry', () => {
    const wrapper = mount(GadgetRenderer, {
      props: { type: 'value', state: makeState(), size: 60 }
    })
    expect(wrapper.find('.orb-gadget__raw').text()).toBe('8.93 GB')
  })

  it('renders a dash when the state carries no metrics', () => {
    const wrapper = mount(GadgetRenderer, {
      props: { type: 'value', state: makeState({ perf_data: '' }), size: 60 }
    })
    expect(wrapper.find('.orb-gadget__raw').text()).toBe('—')
  })

  it('picks the requested metric out of multi-metric perfdata', () => {
    const wrapper = mount(GadgetRenderer, {
      props: {
        type: 'value',
        metric: 'mem_used',
        state: makeState({ perf_data: 'pagefile=1234B;;;; mem_used=8927830016B;;;;' }),
        size: 60,
        metricUnits: units
      }
    })
    expect(wrapper.find('.orb-gadget__raw').text()).toBe('8.31 GiB')
  })
})

describe('GadgetRenderer gauge readout', () => {
  // CPU load's load1 carries a `max` (the core count) purely to scale the bar —
  // Checkmk shows it as the absolute load, never a percent. The gauge readout
  // must echo the CMK-formatted value, not fabricate "27%" from value/max.
  it('shows the absolute value for a max-bearing non-% metric', () => {
    const wrapper = mount(GadgetRenderer, {
      props: {
        type: 'gauge',
        metric: 'load1',
        state: makeState({ perf_data: 'load1=1.09;;;0;4', state: 'OK' }),
        size: 120,
        metricUnits: {
          load1: {
            notation: 'decimal',
            symbol: '',
            precision: { type: 'strict', digits: 2 },
            scale: 1
          }
        }
      }
    })
    const text = wrapper.find('text').text()
    expect(text).toBe('1.09')
    expect(text).not.toContain('%')
  })

  // A genuine % unit still reads as a percent — the value already carries it.
  it('keeps the percent for a real % metric', () => {
    const wrapper = mount(GadgetRenderer, {
      props: {
        type: 'gauge',
        metric: 'util',
        state: makeState({ perf_data: 'util=8.54%;;;0;100', state: 'OK' }),
        size: 120,
        metricUnits: {
          util: {
            notation: 'decimal',
            symbol: '%',
            precision: { type: 'auto', digits: 2 },
            scale: 1
          }
        }
      }
    })
    expect(wrapper.find('text').text()).toBe('8.54%')
  })
})

describe('GadgetRenderer existing gadgets', () => {
  it.each([
    ['trafficlight', '.orb-gadget__traffic'],
    ['bar', '.orb-gadget__track'],
    ['gauge', 'svg']
  ])('still renders the %s branch', (type, selector) => {
    const wrapper = mount(GadgetRenderer, {
      props: { type, state: makeState(), size: 60 }
    })
    expect(wrapper.find(selector).exists()).toBe(true)
    expect(wrapper.find('.orb-gadget__raw').exists()).toBe(false)
  })
})
