import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import type { MetricPoint } from '@/stores/states'

import MetricChart from './MetricChart.vue'

vi.mock('vue-echarts', () => ({
  default: { name: 'VChartStub', props: ['option'], render: () => null }
}))

type EchartsOption = {
  series: { name: string; data: [number, number][] }[]
  yAxis: {
    min: (e: { min: number; max: number }) => number
    max?: (e: { min: number; max: number }) => number
  }
}

function ramp(values: number[]): MetricPoint[] {
  return values.map((v, i) => ({ ts: 1_700_000_000 + i * 60, value: v, unit: 'bits/s' }))
}

function optionOf(mirroredKeys: string[] | undefined): EchartsOption {
  const wrapper = mount(MetricChart, {
    props: {
      data: { if_in_bps: ramp([100, 200]), if_out_bps: ramp([300, 400]) },
      metricKeys: ['if_in_bps', 'if_out_bps'],
      ...(mirroredKeys ? { mirroredKeys } : {}),
      windowSecs: 3600,
      thresholds: null,
      unit: 'bits/s',
      dark: true
    }
  })
  return wrapper.findComponent({ name: 'VChartStub' }).props('option') as EchartsOption
}

describe('MetricChart bidirectional (mirrored) rendering', () => {
  it('negates the mirrored series and centres the axis on zero', () => {
    const opt = optionOf(['if_out_bps'])
    const inSeries = opt.series.find((s) => s.name === 'if_in_bps')!
    const outSeries = opt.series.find((s) => s.name === 'if_out_bps')!

    // Upper half (in) stays positive, lower half (out) is drawn below zero.
    expect(inSeries.data.map((d) => d[1])).toEqual([100, 200])
    expect(outSeries.data.map((d) => d[1])).toEqual([-300, -400])

    // Axis is symmetric around zero so the x-axis sits in the middle.
    const min = opt.yAxis.min({ min: -400, max: 200 })
    const max = opt.yAxis.max!({ min: -400, max: 200 })
    expect(min).toBeLessThan(0)
    expect(max).toBeGreaterThan(0)
    expect(min).toBeCloseTo(-max)
  })

  it('leaves a non-mirrored chart positive with a zero-floored axis', () => {
    const opt = optionOf(undefined)
    const outSeries = opt.series.find((s) => s.name === 'if_out_bps')!
    expect(outSeries.data.map((d) => d[1])).toEqual([300, 400])
    // No mirrored metrics → axis floor never drops below zero, no symmetric max.
    expect(opt.yAxis.min({ min: 100, max: 400 })).toBeGreaterThanOrEqual(0)
    expect(opt.yAxis.max).toBeUndefined()
  })
})
