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

const TIME_H = 16  // px reserved at bottom for time axis
const PAD_LEFT = 34 // px for y-axis labels
const PAD_RIGHT = 6
const PAD_Y = 8

function _fmtTime(ts: number): string {
  const d = new Date(ts * 1000)
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  const today = new Date()
  const sameDay = d.getDate() === today.getDate() && d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear()
  if (sameDay) return `${hh}:${mm}`
  const dd = d.getDate().toString().padStart(2, '0')
  const mo = (d.getMonth() + 1).toString().padStart(2, '0')
  return `${dd}.${mo} ${hh}:${mm}`
}

function _fmtVal(v: number): string {
  if (Math.abs(v) >= 1000) return `${(v / 1000).toFixed(1)}k`
  if (Math.abs(v) >= 100) return v.toFixed(0)
  if (Math.abs(v) >= 10) return v.toFixed(1)
  return v.toFixed(2)
}

export function useMetricChart(
  svgRef: Ref<SVGSVGElement | null>,
  data: Ref<Record<string, MetricPoint[]>>,
  getWidth: () => number,
  getHeight: () => number,
  getWindowSecs?: () => number,
) {
  function render(animate = false) {
    const svg = svgRef.value
    const series = data.value
    if (!svg) return

    // Use actual rendered dimensions so the chart fits the available flex space exactly.
    // Fall back to the computed values only before the element has been laid out.
    const W = svg.clientWidth || getWidth()
    const H = svg.clientHeight || getHeight()
    if (W <= 0 || H <= 0) return

    const root = select(svg).attr('width', W).attr('height', H)
    const labels = Object.keys(series)

    if (labels.length === 0) {
      root.selectAll('*').remove()
      return
    }

    const allPts = labels.flatMap(l => series[l])
    if (allPts.length === 0) { root.selectAll('*').remove(); return }

    const now = Date.now() / 1000
    const windowSecs = getWindowSecs?.() ?? 0
    const tsDataMin = min(allPts, d => d.ts) ?? now
    const tsDataMax = max(allPts, d => d.ts) ?? now
    // Use full configured window for X domain so empty leading time is visible
    const tsMin = windowSecs > 0 ? Math.min(tsDataMin, now - windowSecs) : tsDataMin
    const tsMax = windowSecs > 0 ? Math.max(tsDataMax, now) : tsDataMax

    const valMin = min(allPts, d => d.value) ?? 0
    const valMax = max(allPts, d => d.value) ?? 1
    const range = valMax - valMin || 1

    const HC = H - TIME_H  // chart area height (reserve bottom for time axis)

    const xScale = scaleLinear()
      .domain([tsMin, tsMax === tsMin ? tsMin + 1 : tsMax])
      .range([PAD_LEFT, W - PAD_RIGHT])
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

    // Y-axis labels + grid lines
    const [yLo, yHi] = yScale.domain()
    const yTickVals = [0.0, 0.5, 1.0].map(f => yLo + (yHi - yLo) * f)
    let gridG = root.select<SVGGElement>('g.mc-grid')
    if (gridG.empty()) gridG = root.insert('g', 'g.mc-series').attr('class', 'mc-grid')

    // Horizontal grid lines — solid, slightly visible
    const gridLines = gridG.selectAll<SVGLineElement, number>('line.mc-hline').data(yTickVals)
    gridLines.enter().append('line').attr('class', 'mc-hline')
      .merge(gridLines as any)
      .attr('x1', PAD_LEFT).attr('x2', W - PAD_RIGHT)
      .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
      .attr('stroke', 'rgba(255,255,255,0.09)')
    gridLines.exit().remove()

    // Y-axis vertical separator line
    gridG.selectAll<SVGLineElement, number>('line.mc-yaxis').data([0])
      .join('line').attr('class', 'mc-yaxis')
      .attr('x1', PAD_LEFT).attr('x2', PAD_LEFT)
      .attr('y1', PAD_Y).attr('y2', HC - PAD_Y)
      .attr('stroke', 'rgba(255,255,255,0.15)')

    // Y-axis tick marks
    const yTicks = gridG.selectAll<SVGLineElement, number>('line.mc-ytick').data(yTickVals)
    yTicks.enter().append('line').attr('class', 'mc-ytick')
      .merge(yTicks as any)
      .attr('x1', PAD_LEFT - 3).attr('x2', PAD_LEFT)
      .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
      .attr('stroke', 'rgba(255,255,255,0.25)')
    yTicks.exit().remove()

    const yLabels = gridG.selectAll<SVGTextElement, number>('text.mc-ylabel').data(yTickVals)
    yLabels.enter().append('text').attr('class', 'mc-ylabel')
      .merge(yLabels as any)
      .attr('x', PAD_LEFT - 5)
      .attr('y', d => yScale(d) + 3)
      .attr('text-anchor', 'end')
      .attr('fill', 'rgba(255,255,255,0.40)')
      .attr('font-size', '8')
      .attr('font-family', 'ui-monospace,monospace')
      .text(d => _fmtVal(d))
    yLabels.exit().remove()

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

    // Time axis separator
    root.selectAll<SVGLineElement, number>('line.mc-t-sep').data([0])
      .join('line').attr('class', 'mc-t-sep')
      .attr('x1', PAD_LEFT).attr('x2', W - PAD_RIGHT)
      .attr('y1', HC + 1).attr('y2', HC + 1)
      .attr('stroke', 'rgba(255,255,255,0.10)')

    // Tick marks + labels: left edge, middle, right edge
    type TickDatum = { x: number; label: string; anchor: string }
    const hasRange = tsMax - tsMin > 1
    const tsMid = (tsMin + tsMax) / 2
    const ticks: TickDatum[] = hasRange ? [
      { x: PAD_LEFT,         label: _fmtTime(tsMin),  anchor: 'start' },
      { x: (PAD_LEFT + W - PAD_RIGHT) / 2, label: _fmtTime(tsMid), anchor: 'middle' },
      { x: W - PAD_RIGHT,   label: _fmtTime(tsMax),  anchor: 'end' },
    ] : [
      { x: W - PAD_RIGHT,   label: _fmtTime(tsMax),  anchor: 'end' },
    ]

    root.selectAll<SVGLineElement, TickDatum>('line.mc-tick')
      .data(ticks, d => d.label)
      .join('line').attr('class', 'mc-tick')
      .attr('x1', d => d.x).attr('x2', d => d.x)
      .attr('y1', HC + 1).attr('y2', HC + 4)
      .attr('stroke', 'rgba(255,255,255,0.18)')

    root.selectAll<SVGTextElement, TickDatum>('text.mc-t-tick')
      .data(ticks, d => d.label)
      .join('text').attr('class', 'mc-t-tick')
      .attr('x', d => d.x).attr('y', H - 2)
      .attr('text-anchor', d => d.anchor)
      .attr('fill', 'rgba(255,255,255,0.40)').attr('font-size', '9')
      .attr('font-family', 'ui-monospace,monospace')
      .text(d => d.label)
  }

  onMounted(() => render(false))
  watch(data, () => render(true), { flush: 'post' })
  onUnmounted(() => {
    const svg = svgRef.value
    if (svg) select(svg).selectAll('*').interrupt()
  })
}
