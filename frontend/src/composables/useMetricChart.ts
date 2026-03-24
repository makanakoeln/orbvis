import { onMounted, onUnmounted, watch } from 'vue'
import type { Ref } from 'vue'
import { select } from 'd3-selection'
import { line, area, curveMonotoneX } from 'd3-shape'
import { scaleLinear } from 'd3-scale'
import { min, max } from 'd3-array'
import 'd3-transition'
import { easeQuadInOut } from 'd3-ease'
import type { MetricPoint } from '@/stores/states'
import { utilColor } from '@/utils/perf'

export const CHART_PALETTE = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#06b6d4', '#f97316', '#ec4899',
]

const TIME_H = 14  // px reserved at bottom for time axis
const PAD_X = 6
const PAD_Y = 8

function _fmtRelTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  if (m === 0) return `-${s}s`
  if (s === 0) return `-${m}m`
  return `-${m}m ${s}s`
}

export function useMetricChart(
  svgRef: Ref<SVGSVGElement | null>,
  data: Ref<Record<string, MetricPoint[]>>,
  getWidth: () => number,
  getHeight: () => number,
) {
  function render(animate = false) {
    const svg = svgRef.value
    const series = data.value
    if (!svg) return

    const W = getWidth()
    const H = getHeight()
    if (W <= 0 || H <= 0) return

    const root = select(svg).attr('width', W).attr('height', H)
    const labels = Object.keys(series)

    if (labels.length === 0) {
      root.selectAll('*').remove()
      return
    }

    const allPts = labels.flatMap(l => series[l])
    if (allPts.length === 0) { root.selectAll('*').remove(); return }

    const tsMin = min(allPts, d => d.ts) ?? 0
    const tsMax = max(allPts, d => d.ts) ?? 1
    const valMin = min(allPts, d => d.value) ?? 0
    const valMax = max(allPts, d => d.value) ?? 1
    const range = valMax - valMin || 1

    const HC = H - TIME_H  // chart area height (reserve bottom for time axis)

    const xScale = scaleLinear()
      .domain([tsMin, tsMax === tsMin ? tsMin + 1 : tsMax])
      .range([PAD_X, W - PAD_X])
    const yScale = scaleLinear()
      .domain([Math.max(0, valMin - range * 0.15), valMax + range * 0.15])
      .range([HC - PAD_Y, PAD_Y])

    const multiSeries = labels.length > 1

    // Defs: gradient for single-series area fill
    let defs = root.select<SVGDefsElement>('defs')
    if (defs.empty()) defs = root.insert('defs', ':first-child')
    const gradId = 'mc-area-grad'
    let grad = defs.select<SVGLinearGradientElement>(`#${gradId}`)
    if (grad.empty()) {
      grad = defs.append<SVGLinearGradientElement>('linearGradient')
        .attr('id', gradId)
        .attr('x1', '0').attr('x2', '0').attr('y1', '0').attr('y2', '1')
      grad.append('stop').attr('offset', '0%').attr('stop-opacity', '0.25')
      grad.append('stop').attr('offset', '100%').attr('stop-opacity', '0.02')
    }

    // Subtle horizontal grid lines
    const [yLo, yHi] = yScale.domain()
    const gridVals = [0.25, 0.5, 0.75].map(f => yLo + (yHi - yLo) * f)
    let gridG = root.select<SVGGElement>('g.mc-grid')
    if (gridG.empty()) gridG = root.insert('g', 'g.mc-series').attr('class', 'mc-grid')
    const gridLines = gridG.selectAll<SVGLineElement, number>('line').data(gridVals)
    gridLines.enter().append('line')
      .merge(gridLines as any)
      .attr('x1', PAD_X).attr('x2', W - PAD_X)
      .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
      .attr('stroke', 'rgba(255,255,255,0.06)')
      .attr('stroke-dasharray', '2,4')
    gridLines.exit().remove()

    const lineGen = line<MetricPoint>()
      .x(d => xScale(d.ts))
      .y(d => yScale(d.value))
      .curve(curveMonotoneX)

    // Data join for series groups
    const groups = root.selectAll<SVGGElement, string>('g.mc-series')
      .data(labels, d => d)

    const entered = groups.enter().append('g').attr('class', 'mc-series')
    entered.append('path').attr('class', 'mc-area')
    entered.append('path').attr('class', 'mc-line')
      .attr('fill', 'none').attr('stroke-width', '2').attr('stroke-linecap', 'round').attr('stroke-linejoin', 'round')
    entered.append('circle').attr('class', 'mc-dot-ring').attr('r', '5').attr('fill', 'none').attr('stroke-width', '1.5')
    entered.append('circle').attr('class', 'mc-dot').attr('r', '3')

    groups.exit().remove()

    const merged = entered.merge(groups as any)

    merged.each(function (label, i) {
      const g = select(this)
      const pts = series[label]
      if (!pts || pts.length === 0) return

      const latest = pts[pts.length - 1]
      const color = multiSeries
        ? CHART_PALETTE[i % CHART_PALETTE.length]
        : utilColor(valMax > 0 ? Math.min(100, (latest.value / valMax) * 100) : 0)

      const pathD = lineGen(pts)!

      const areaEl = g.select<SVGPathElement>('.mc-area')
      if (!multiSeries) {
        const areaGen = area<MetricPoint>()
          .x(d => xScale(d.ts))
          .y0(HC - PAD_Y)
          .y1(d => yScale(d.value))
          .curve(curveMonotoneX)
        const areaD = areaGen(pts)!
        defs.select(`#${gradId} stop:first-child`).attr('stop-color', color)
        defs.select(`#${gradId} stop:last-child`).attr('stop-color', color)
        areaEl.attr('fill', `url(#${gradId})`).attr('display', null)
        if (animate && pts.length > 1) {
          areaEl.transition().duration(400).ease(easeQuadInOut).attr('d', areaD)
        } else {
          areaEl.attr('d', areaD)
        }
      } else {
        areaEl.attr('display', 'none')
      }

      g.select<SVGPathElement>('.mc-line').attr('stroke', color)
      g.select<SVGCircleElement>('.mc-dot-ring')
        .attr('cx', xScale(latest.ts)).attr('cy', yScale(latest.value))
        .attr('stroke', color).attr('opacity', '0.35')
      g.select<SVGCircleElement>('.mc-dot')
        .attr('cx', xScale(latest.ts)).attr('cy', yScale(latest.value))
        .attr('fill', color)

      if (animate && pts.length > 1) {
        g.select<SVGPathElement>('.mc-line').transition().duration(400).ease(easeQuadInOut).attr('d', pathD)
      } else {
        g.select<SVGPathElement>('.mc-line').attr('d', pathD)
      }
    })

    // Time axis
    const timeDiffSec = tsMax - tsMin
    const hasRange = timeDiffSec > 1

    root.selectAll<SVGLineElement, number>('line.mc-t-sep').data([0])
      .join('line').attr('class', 'mc-t-sep')
      .attr('x1', PAD_X).attr('x2', W - PAD_X)
      .attr('y1', HC + 1).attr('y2', HC + 1)
      .attr('stroke', 'rgba(255,255,255,0.07)')

    root.selectAll<SVGTextElement, string>('text.mc-t-left')
      .data(hasRange ? [_fmtRelTime(timeDiffSec)] : [''])
      .join('text').attr('class', 'mc-t-left')
      .attr('x', PAD_X).attr('y', H - 3)
      .attr('fill', 'rgba(255,255,255,0.28)').attr('font-size', '9')
      .attr('font-family', 'ui-monospace,monospace')
      .text(d => d)

    root.selectAll<SVGTextElement, string>('text.mc-t-right')
      .data(['now'])
      .join('text').attr('class', 'mc-t-right')
      .attr('x', W - PAD_X).attr('y', H - 3)
      .attr('text-anchor', 'end')
      .attr('fill', 'rgba(255,255,255,0.28)').attr('font-size', '9')
      .attr('font-family', 'ui-monospace,monospace')
      .text('now')
  }

  onMounted(() => render(false))
  watch(data, () => render(true), { flush: 'post' })
  onUnmounted(() => {
    const svg = svgRef.value
    if (svg) select(svg).selectAll('*').interrupt()
  })
}
