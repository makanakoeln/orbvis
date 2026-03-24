import { onMounted, onUnmounted, watch } from 'vue'
import type { Ref } from 'vue'
import { select } from 'd3-selection'
import { line, area, curveMonotoneX } from 'd3-shape'
import { scaleLinear } from 'd3-scale'
import { min, max } from 'd3-array'
import { transition } from 'd3-transition'
import { easeQuadInOut } from 'd3-ease'
import type { MetricPoint } from '@/stores/states'
import { utilColor } from '@/utils/perf'

// d3-transition side-effects
void transition

export function useMetricChart(
  svgRef: Ref<SVGSVGElement | null>,
  data: Ref<MetricPoint[]>,
  getWidth: () => number,
  getHeight: () => number,
) {
  const PAD = 4

  function render(animate = false) {
    const svg = svgRef.value
    const pts = data.value
    if (!svg) return

    const W = getWidth()
    const H = getHeight()
    if (W <= 0 || H <= 0) return

    const root = select(svg).attr('width', W).attr('height', H)

    if (pts.length === 0) {
      root.selectAll('*').remove()
      return
    }

    const tsMin = min(pts, d => d.ts) ?? pts[0].ts
    const tsMax = max(pts, d => d.ts) ?? pts[0].ts
    const valMin = min(pts, d => d.value) ?? 0
    const valMax = max(pts, d => d.value) ?? 1
    const range = valMax - valMin || 1

    const latest = pts[pts.length - 1]
    const pct = valMax > 0 ? Math.min(100, (latest.value / valMax) * 100) : 0
    const color = utilColor(pct)

    const xScale = scaleLinear()
      .domain([tsMin, tsMax === tsMin ? tsMin + 1 : tsMax])
      .range([PAD, W - PAD])
    const yScale = scaleLinear()
      .domain([Math.max(0, valMin - range * 0.1), valMax + range * 0.1])
      .range([H - PAD, PAD])

    const lineGen = line<MetricPoint>()
      .x(d => xScale(d.ts))
      .y(d => yScale(d.value))
      .curve(curveMonotoneX)

    const areaGen = area<MetricPoint>()
      .x(d => xScale(d.ts))
      .y0(H - PAD)
      .y1(d => yScale(d.value))
      .curve(curveMonotoneX)

    const pathD = lineGen(pts)!
    const areaD = areaGen(pts)!

    // Area fill
    let areaPath = root.select<SVGPathElement>('path.mc-area')
    if (areaPath.empty()) areaPath = root.append('path').attr('class', 'mc-area')
    areaPath.attr('fill', color).attr('opacity', '0.15')

    // Line
    let linePath = root.select<SVGPathElement>('path.mc-line')
    if (linePath.empty()) {
      linePath = root.append('path').attr('class', 'mc-line')
        .attr('fill', 'none').attr('stroke-width', '1.5').attr('stroke-linecap', 'round')
    }
    linePath.attr('stroke', color)

    if (animate && pts.length > 1) {
      linePath.transition().duration(400).ease(easeQuadInOut).attr('d', pathD)
      areaPath.transition().duration(400).ease(easeQuadInOut).attr('d', areaD)
    } else {
      linePath.attr('d', pathD)
      areaPath.attr('d', areaD)
    }

    // Dot at last point
    let dot = root.select<SVGCircleElement>('circle.mc-dot')
    if (dot.empty()) dot = root.append('circle').attr('class', 'mc-dot').attr('r', '2.5')
    dot.attr('cx', xScale(latest.ts)).attr('cy', yScale(latest.value)).attr('fill', color)

    root.select('circle:not(.mc-dot)').remove()
  }

  onMounted(() => render(false))
  watch(data, () => render(true), { flush: 'post' })
  onUnmounted(() => {
    const svg = svgRef.value
    if (svg) select(svg).selectAll('*').interrupt()
  })
}
