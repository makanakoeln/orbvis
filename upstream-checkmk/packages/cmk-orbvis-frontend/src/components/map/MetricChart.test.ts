import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import type { MetricPoint } from '@/stores/states'

import MetricChart from './MetricChart.vue'

vi.mock('vue-echarts', () => ({
  default: { name: 'VChartStub', props: ['option'], render: () => null }
}))

type TooltipParam = { seriesName: string; value: [number, number]; marker: string }
type EchartsOption = {
  series: { name: string; data: [number, number][] }[]
  yAxis: {
    axisLabel: { showMinLabel?: boolean; showMaxLabel?: boolean }
    min: (e: { min: number; max: number }) => number
    max?: (e: { min: number; max: number }) => number
  }
  tooltip: {
    appendToBody?: boolean
    confine?: boolean
    formatter: (params: TooltipParam[]) => string
  }
}

function ramp(values: number[]): MetricPoint[] {
  return values.map((v, i) => ({ ts: 1_700_000_000 + i * 60, value: v, unit: 'bits/s' }))
}

function optionOf(mirroredKeys?: string[], titles?: Record<string, string>): EchartsOption {
  const wrapper = mount(MetricChart, {
    props: {
      data: { if_in_bps: ramp([100, 200]), if_out_bps: ramp([300, 400]) },
      metricKeys: ['if_in_bps', 'if_out_bps'],
      ...(mirroredKeys ? { mirroredKeys } : {}),
      ...(titles ? { titles } : {}),
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

  it('labels tooltip rows with the metric title and renders body-level/confined', () => {
    const opt = optionOf(['if_out_bps'], { if_out_bps: 'Output bandwidth' })
    expect(opt.tooltip.appendToBody).toBe(true)
    expect(opt.tooltip.confine).toBe(true)
    const html = opt.tooltip.formatter([
      { seriesName: 'if_out_bps', value: [1_700_000_000_000, -400], marker: '' }
    ])
    expect(html).toContain('Output bandwidth')
    expect(html).not.toMatch(/>\s*if_out_bps:/)
  })

  it('hides the padded min/max axis extent labels', () => {
    const opt = optionOf(['if_out_bps'])
    expect(opt.yAxis.axisLabel.showMinLabel).toBe(false)
    expect(opt.yAxis.axisLabel.showMaxLabel).toBe(false)
  })
})
