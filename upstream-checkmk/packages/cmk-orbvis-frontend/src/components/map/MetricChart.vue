<script lang="ts">
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'

use([CanvasRenderer, LineChart, GridComponent, MarkLineComponent, TooltipComponent])

export default {}
</script>

<script setup lang="ts">
import type { LineSeriesOption } from 'echarts/charts'
import type {
  GridComponentOption,
  MarkLineComponentOption,
  TooltipComponentOption
} from 'echarts/components'
import type { ComposeOption } from 'echarts/core'
import { computed } from 'vue'
import VChart from 'vue-echarts'

import { CHART_PALETTE, normalizeMetricValue } from '@/composables/useMetricChart'
import type { MetricPoint } from '@/stores/states'
import type { MetricUnitMap } from '@/types/api'
import { renderMetricValue } from '@/utils/metricFormat'

type EOption = ComposeOption<
  GridComponentOption | LineSeriesOption | MarkLineComponentOption | TooltipComponentOption
>

interface TooltipParam {
  seriesName: string
  value: [number, number]
  marker: string
}

const props = defineProps<{
  data: Record<string, MetricPoint[]>
  metricKeys: string[]
  mirroredKeys?: string[]
  // Checkmk's registered display unit per metric (label → spec). Carries the
  // translation scale (e.g. interface octets ×8 → bits/s) and the unit symbol,
  // so the chart reads exactly like Checkmk's own graph instead of raw counts.
  unitMap?: MetricUnitMap
  // Display title per metric key (e.g. in → "Input bandwidth") for the tooltip.
  titles?: Record<string, string>
  windowSecs: number
  thresholds: { warn: number | null; crit: number | null } | null
  unit: string | undefined
  dark: boolean
}>()

// Metrics CMK draws below the x-axis (a Bidirectional graph's lower half, e.g.
// interface out vs. in): negate their values and centre the axis on zero.
const mirroredSet = computed(() => new Set(props.mirroredKeys ?? []))
const hasMirrored = computed(() => props.metricKeys.some((k) => mirroredSet.value.has(k)))

function _fmtTime(ms: number): string {
  const d = new Date(ms)
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  const today = new Date()
  const sameDay =
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear()
  if (sameDay) return `${hh}:${mm}`
  const dd = d.getDate().toString().padStart(2, '0')
  const mo = (d.getMonth() + 1).toString().padStart(2, '0')
  return `${dd}.${mo} ${hh}:${mm}`
}

function _hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

// Plotted value: apply the metric's registered translation scale so the data is
// in Checkmk's canonical unit (e.g. interface octets ×8 → bits/s); fall back to
// the raw-perfdata SI normalisation when the metric isn't registered.
function _plot(rawValue: number, key: string, pointUnit?: string): number {
  const scale = props.unitMap?.[key]?.scale
  return scale !== undefined
    ? rawValue * scale
    : normalizeMetricValue(rawValue, pointUnit ?? props.unit)
}

// Format an already-scaled (canonical) value through Checkmk's own unit-format
// library — the data is pre-scaled by `_plot`, so format with scale 1 to avoid
// scaling twice. Mirrored series carry a negated value; show its magnitude.
function _fmt(canonicalValue: number, key: string): string {
  const v = hasMirrored.value ? Math.abs(canonicalValue) : canonicalValue
  const spec = props.unitMap?.[key]
  return renderMetricValue(v, spec ? { ...spec, scale: 1 } : null, props.unit ?? '')
}

function _buildTooltip(rawParams: TooltipParam | TooltipParam[]): string {
  const items = Array.isArray(rawParams) ? rawParams : [rawParams]
  const head = items[0]
  if (head === undefined) return ''
  const ts = head.value[0]
  const rows = items
    .map((p) => {
      const name = props.titles?.[p.seriesName] ?? p.seriesName
      return `${p.marker}<span style="font-size:9px"> ${name}: <b>${_fmt(p.value[1], p.seriesName)}</b></span>`
    })
    .join('<br/>')
  return `<div style="font-size:9px;opacity:0.7;margin-bottom:2px">${_fmtTime(ts)}</div>${rows}`
}

// Y-axis formatter: render the unit inline on every tick. All series of a graph
// share a unit, so the first metric's spec drives the axis.
function _fmtAxis(v: number): string {
  return _fmt(v, props.metricKeys[0] ?? '')
}

const option = computed((): EOption => {
  const dark = props.dark
  const textColor = dark ? 'rgba(255,255,255,0.60)' : 'rgba(0,0,0,0.55)'
  const gridColor = dark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.15)'
  const axisColor = dark ? 'rgba(255,255,255,0.30)' : 'rgba(0,0,0,0.30)'
  const tooltipBg = dark ? 'rgba(24,24,27,0.96)' : 'rgba(255,255,255,0.96)'
  const tooltipBorder = dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)'
  const multiSeries = props.metricKeys.length > 1

  const now = Date.now()
  const xMin = props.windowSecs > 0 ? now - props.windowSecs * 1000 : undefined
  const xMax = props.windowSecs > 0 ? now : undefined

  const series: LineSeriesOption[] = props.metricKeys.map((key, i) => {
    const pts = props.data[key] ?? []
    // CHART_PALETTE is a non-empty constant, so `i % length` is always in bounds.
    const color = CHART_PALETTE[i % CHART_PALETTE.length]!
    const sign = mirroredSet.value.has(key) ? -1 : 1

    // Build threshold markLines for single-series charts only
    const markLineItems: NonNullable<NonNullable<LineSeriesOption['markLine']>['data']> = []
    if (!multiSeries && i === 0 && props.thresholds) {
      if (props.thresholds.warn !== null) {
        markLineItems.push({
          yAxis: _plot(props.thresholds.warn, key) * sign,
          lineStyle: { color: 'rgb(255,208,0)', type: 'dashed', width: 1, opacity: 0.75 },
          label: { show: false }
        })
      }
      if (props.thresholds.crit !== null) {
        markLineItems.push({
          yAxis: _plot(props.thresholds.crit, key) * sign,
          lineStyle: {
            color: 'rgb(248,113,113)',
            type: 'dashed',
            width: 1,
            opacity: 0.75
          },
          label: { show: false }
        })
      }
    }

    return {
      name: key,
      type: 'line',
      smooth: 0.4,
      symbol: 'none',
      lineStyle: { color, width: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: _hexToRgba(color, 0.28) },
            { offset: 1, color: _hexToRgba(color, 0.02) }
          ]
        }
      },
      data: pts.map((p) => [p.ts * 1000, _plot(p.value, key, p.unit) * sign]),
      ...(markLineItems.length > 0
        ? {
            markLine: {
              silent: true,
              symbol: ['none', 'none'],
              data: markLineItems
            }
          }
        : {})
    }
  })

  return {
    backgroundColor: 'transparent',
    animation: false,
    grid: { top: 8, right: 6, bottom: 20, left: 52, containLabel: false },
    xAxis: {
      type: 'time',
      ...(xMin !== undefined ? { min: xMin } : {}),
      ...(xMax !== undefined ? { max: xMax } : {}),
      axisLine: { lineStyle: { color: axisColor } },
      axisTick: { lineStyle: { color: axisColor } },
      axisLabel: {
        color: textColor,
        fontSize: 9,
        fontFamily: 'ui-monospace,monospace',
        formatter: (val: number) => _fmtTime(val),
        showMaxLabel: true,
        showMinLabel: true,
        hideOverlap: true
      },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: true, lineStyle: { color: axisColor } },
      axisTick: { lineStyle: { color: axisColor } },
      axisLabel: {
        color: textColor,
        fontSize: 8,
        fontFamily: 'ui-monospace,monospace',
        formatter: _fmtAxis,
        // Hide the padded min/max extents (e.g. the −4.58 Mbit/s headroom edge);
        // the round interior ticks read cleanly.
        showMaxLabel: false,
        showMinLabel: false
      },
      splitLine: { lineStyle: { color: gridColor } },
      splitNumber: 4,
      min: (extent: { min: number; max: number }): number =>
        hasMirrored.value
          ? -Math.max(Math.abs(extent.min), Math.abs(extent.max)) * 1.1
          : Math.max(0, extent.min - (extent.max - extent.min) * 0.15),
      ...(hasMirrored.value
        ? {
            max: (extent: { min: number; max: number }): number =>
              Math.max(Math.abs(extent.min), Math.abs(extent.max)) * 1.1
          }
        : {})
    },
    tooltip: {
      trigger: 'axis',
      // Render at body level and keep on screen so a tall multi-series tooltip
      // isn't clipped by the small graph container.
      appendToBody: true,
      confine: true,
      axisPointer: {
        type: 'cross',
        label: { show: false },
        crossStyle: { color: axisColor }
      },
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: { color: textColor, fontSize: 10, fontFamily: 'ui-monospace,monospace' },
      padding: [6, 8],
      formatter: _buildTooltip as (params: unknown) => string
    },
    series
  }
})
</script>

<template>
  <v-chart class="orb-metric-chart" :option="option" :autoresize="true" />
</template>

<style scoped>
.orb-metric-chart {
  width: 100%;
  height: 100%;
}
</style>
