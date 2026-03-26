import { max, min } from 'd3-array';
import { easeQuadInOut } from 'd3-ease';
import { scaleLinear } from 'd3-scale';
import { select } from 'd3-selection';
import { area, curveMonotoneX, line } from 'd3-shape';
import { transition } from 'd3-transition';
import type { Ref } from 'vue';
import { onMounted, watch } from 'vue';

import type { MetricSnapshot } from '@/stores/states';
import { utilColor } from '@/utils/perf';

import { useD3Cleanup } from './useD3Cleanup';

// d3-transition side-effects
void transition;

interface SparklineOptions {
  svgRef: Ref<SVGSVGElement | null>;
  data: Ref<MetricSnapshot[]>;
  width?: number;
  height?: number;
}

export function useSparkline(opts: SparklineOptions) {
  const W = opts.width ?? 120;
  const H = opts.height ?? 40;

  const xScale = scaleLinear().range([4, W - 4]);
  const yScale = scaleLinear()
    .domain([0, 100])
    .range([H - 4, 4]);

  const lineGen = line<MetricSnapshot>()
    .x((d) => xScale(d.ts))
    .y((d) => yScale(d.pct))
    .curve(curveMonotoneX);

  const areaGen = area<MetricSnapshot>()
    .x((d) => xScale(d.ts))
    .y0(H - 4)
    .y1((d) => yScale(d.pct))
    .curve(curveMonotoneX);

  function render(animate = false) {
    const svg = opts.svgRef.value;
    const data = opts.data.value;
    if (!svg) return;

    const root = select(svg);

    if (data.length < 2) {
      root.selectAll('*').remove();
      if (data.length === 1) {
        root
          .append('circle')
          .attr('cx', W / 2)
          .attr('cy', H / 2)
          .attr('r', 3)
          .attr('fill', utilColor(data[0].pct));
      }
      return;
    }

    const tsMin = min(data, (d) => d.ts) ?? data[0].ts;
    const tsMax = max(data, (d) => d.ts) ?? data[0].ts;
    xScale.domain([tsMin, tsMax === tsMin ? tsMin + 1 : tsMax]);

    const color = utilColor(data[data.length - 1].pct);
    const pathD = lineGen(data)!;
    const areaD = areaGen(data)!;

    // Area fill
    let areaPath = root.select<SVGPathElement>('path.spark-area');
    if (areaPath.empty()) {
      areaPath = root.append('path').attr('class', 'spark-area');
    }
    areaPath.attr('d', areaD).attr('fill', color).attr('opacity', '0.15');

    // Line
    let linePath = root.select<SVGPathElement>('path.spark-path');
    if (linePath.empty()) {
      linePath = root
        .append('path')
        .attr('class', 'spark-path')
        .attr('fill', 'none')
        .attr('stroke-width', '1.5')
        .attr('stroke-linecap', 'round');
    }
    linePath.attr('stroke', color);

    if (animate) {
      linePath.transition().duration(400).ease(easeQuadInOut).attr('d', pathD);
      areaPath.transition().duration(400).ease(easeQuadInOut).attr('d', areaD);
    } else {
      linePath.attr('d', pathD);
    }

    // Dot at last point
    const last = data[data.length - 1];
    let dot = root.select<SVGCircleElement>('circle.spark-dot');
    if (dot.empty()) {
      dot = root.append('circle').attr('class', 'spark-dot').attr('r', '2.5');
    }
    dot.attr('cx', xScale(last.ts)).attr('cy', yScale(last.pct)).attr('fill', color);

    root.select('circle:not(.spark-dot)').remove();
  }

  onMounted(() => render(false));

  watch(opts.data, () => render(true), { flush: 'post' });

  useD3Cleanup(opts.svgRef);
}
