import 'd3-transition';

import { max, min } from 'd3-array';
import { scaleLinear } from 'd3-scale';
import { select } from 'd3-selection';
import { area, curveMonotoneX, line } from 'd3-shape';
import type { Ref } from 'vue';
import { onMounted, onUnmounted, watch } from 'vue';

import type { MetricPoint } from '@/stores/states';
import { utilColor } from '@/utils/perf';

export const CHART_PALETTE = [
  '#6366f1',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#f97316',
  '#ec4899',
];

// Max series shown in the legend and used for Y-domain calculation
export const MAX_VISIBLE_SERIES = 6;

const TIME_H = 16; // px reserved at bottom for time axis
const PAD_LEFT = 34; // px for y-axis labels
const PAD_RIGHT = 6;
const PAD_Y = 8;

function _fmtTime(ts: number): string {
  const d = new Date(ts * 1000);
  const hh = d.getHours().toString().padStart(2, '0');
  const mm = d.getMinutes().toString().padStart(2, '0');
  const today = new Date();
  const sameDay =
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear();
  if (sameDay) return `${hh}:${mm}`;
  const dd = d.getDate().toString().padStart(2, '0');
  const mo = (d.getMonth() + 1).toString().padStart(2, '0');
  return `${dd}.${mo} ${hh}:${mm}`;
}

// Multiplier for single-char SI prefix units (e.g. "k" = kilobytes in Checkmk perf_data)
const _SI_MULT: Record<string, number> = {
  k: 1e3,
  K: 1e3,
  m: 1e6,
  M: 1e6,
  g: 1e9,
  G: 1e9,
  t: 1e12,
  T: 1e12,
};

// True when the unit is a bare SI magnitude prefix that fmtMetricVal absorbs into its output
export function isSingleCharSIPrefix(unit: string | null | undefined): boolean {
  return !!unit && unit.length === 1 && _SI_MULT[unit] !== undefined;
}

// Returns the base unit after stripping any SI prefix that fmtMetricVal absorbs.
// Examples: "MB" → "B", "k" → "", "%" → "%", "" → ""
export function baseUnit(unit: string | null | undefined): string {
  if (!unit) return '';
  if (isSingleCharSIPrefix(unit)) return '';
  if (/^[kKmMgGtT]/.test(unit) && unit.length > 1) return unit.slice(1);
  return unit;
}

function _fmtMagnitude(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e12) return `${(v / 1e12).toFixed(1)}T`;
  if (a >= 1e9) return `${(v / 1e9).toFixed(1)}G`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return a >= 100 ? v.toFixed(0) : a >= 10 ? v.toFixed(1) : v.toFixed(2);
}

export function fmtMetricVal(v: number, unit?: string): string {
  // Single-char SI prefix units (e.g. "k" = kilobytes): scale to base unit so the
  // magnitude formatting produces the correct combined prefix (116200 k → "116.2M").
  if (isSingleCharSIPrefix(unit)) return _fmtMagnitude(v * _SI_MULT[unit!]);
  if (!unit || !/^[kKmMgGtT]/.test(unit)) return _fmtMagnitude(v);
  // Multi-char prefixed unit (e.g. "MB", "kB"): scale by SI prefix factor so magnitude
  // formatting produces a readable combined value ("116130 MB" → "116.1G" + base "B").
  return _fmtMagnitude(v * (_SI_MULT[unit[0]] ?? 1));
}

export function renderMetricChart(
  svgEl: SVGSVGElement,
  data: Record<string, MetricPoint[]>,
  width: number,
  height: number,
  windowSecs?: number,
  thresholds?: { warn: number | null; crit: number | null } | null,
  unit?: string,
  fill?: boolean,
): void {
  // Use actual rendered dimensions so the chart fits the available flex space exactly.
  // Fall back to the passed values only before the element has been laid out.
  const W = svgEl.clientWidth || width;
  const H = svgEl.clientHeight || height;
  if (W <= 0 || H <= 0) return;

  const dark = document.documentElement.classList.contains('dark');
  const c = dark
    ? {
        grid: 'rgba(255,255,255,0.18)',
        axis: 'rgba(255,255,255,0.30)',
        tick: 'rgba(255,255,255,0.40)',
        label: 'rgba(255,255,255,0.60)',
        sep: 'rgba(255,255,255,0.20)',
        timeTick: 'rgba(255,255,255,0.35)',
        timeLabel: 'rgba(255,255,255,0.60)',
      }
    : {
        grid: 'rgba(0,0,0,0.15)',
        axis: 'rgba(0,0,0,0.30)',
        tick: 'rgba(0,0,0,0.35)',
        label: 'rgba(0,0,0,0.55)',
        sep: 'rgba(0,0,0,0.18)',
        timeTick: 'rgba(0,0,0,0.28)',
        timeLabel: 'rgba(0,0,0,0.55)',
      };

  const root = select(svgEl).attr('width', W).attr('height', H);
  const labels = Object.keys(data);

  if (labels.length === 0) {
    root.selectAll('*').remove();
    return;
  }

  // Only visible labels contribute to Y-domain in multi-series mode so that
  // hidden metrics with extreme values (e.g. mem_total) don't collapse the visible range.
  const multiSeries = labels.length > 1;
  const domainLabels = multiSeries ? labels.slice(0, MAX_VISIBLE_SERIES) : labels;
  const allPts = domainLabels.flatMap((l) => data[l]);
  if (allPts.length === 0) {
    root.selectAll('*').remove();
    return;
  }

  const now = Date.now() / 1000;
  const ws = windowSecs ?? 0;
  const tsDataMin = min(allPts, (d) => d.ts) ?? now;
  const tsDataMax = max(allPts, (d) => d.ts) ?? now;
  // Use full configured window for X domain so empty leading time is visible
  const tsMin = ws > 0 ? Math.min(tsDataMin, now - ws) : tsDataMin;
  const tsMax = ws > 0 ? Math.max(tsDataMax, now) : tsDataMax;

  const valMin = min(allPts, (d) => d.value) ?? 0;
  const valMax = max(allPts, (d) => d.value) ?? 1;
  const range = valMax - valMin || 1;

  const HC = H - TIME_H; // chart area height (reserve bottom for time axis)

  const xScale = scaleLinear()
    .domain([tsMin, tsMax === tsMin ? tsMin + 1 : tsMax])
    .range([PAD_LEFT, W - PAD_RIGHT]);

  // Extend Y-domain upward so threshold lines are always visible in the chart.
  // Only applies to single-series: multi-series charts don't draw threshold lines
  // so including threshold values (e.g. warn=80 for CPU load) would collapse the
  // visible data range to near-zero.
  const resolvedThresholds = !multiSeries ? (thresholds ?? null) : null;
  const tVals = multiSeries
    ? []
    : (resolvedThresholds ? [resolvedThresholds.warn, resolvedThresholds.crit] : []).filter(
        (v): v is number => v !== null,
      );
  const yHiRaw = valMax + range * 0.15;
  const yHi = tVals.length > 0 ? Math.max(yHiRaw, ...tVals) : yHiRaw;
  const yScale = scaleLinear()
    .domain([valMin - range * 0.15, yHi])
    .range([HC - PAD_Y, PAD_Y]);

  // Defs: gradient for single-series area fill
  let defs = root.select<SVGDefsElement>('defs');
  if (defs.empty()) defs = root.insert('defs', ':first-child');
  const gradId = 'mc-area-grad';
  let grad = defs.select<SVGLinearGradientElement>(`#${gradId}`);
  if (grad.empty()) {
    grad = defs
      .append<SVGLinearGradientElement>('linearGradient')
      .attr('id', gradId)
      .attr('x1', '0')
      .attr('x2', '0')
      .attr('y1', '0')
      .attr('y2', '1');
    grad.append('stop').attr('offset', '0%').attr('stop-opacity', '0.25');
    grad.append('stop').attr('offset', '100%').attr('stop-opacity', '0.02');
  }

  // Y-axis labels + grid lines
  const [yDomLo, yDomHi] = yScale.domain();
  const yTickVals = [0.0, 0.25, 0.5, 0.75, 1.0].map((f) => yDomLo + (yDomHi - yDomLo) * f);
  let gridG = root.select<SVGGElement>('g.mc-grid');
  if (gridG.empty()) gridG = root.insert('g', 'g.mc-series').attr('class', 'mc-grid');

  // Horizontal grid lines
  gridG
    .selectAll<SVGLineElement, number>('line.mc-hline')
    .data(yTickVals)
    .join('line')
    .attr('class', 'mc-hline')
    .attr('x1', PAD_LEFT)
    .attr('x2', W - PAD_RIGHT)
    .attr('y1', (d) => yScale(d))
    .attr('y2', (d) => yScale(d))
    .attr('stroke', c.grid);

  // Y-axis vertical separator line
  gridG
    .selectAll<SVGLineElement, number>('line.mc-yaxis')
    .data([0])
    .join('line')
    .attr('class', 'mc-yaxis')
    .attr('x1', PAD_LEFT)
    .attr('x2', PAD_LEFT)
    .attr('y1', PAD_Y)
    .attr('y2', HC - PAD_Y)
    .attr('stroke', c.axis);

  // Y-axis tick marks
  gridG
    .selectAll<SVGLineElement, number>('line.mc-ytick')
    .data(yTickVals)
    .join('line')
    .attr('class', 'mc-ytick')
    .attr('x1', PAD_LEFT - 3)
    .attr('x2', PAD_LEFT)
    .attr('y1', (d) => yScale(d))
    .attr('y2', (d) => yScale(d))
    .attr('stroke', c.tick);

  gridG
    .selectAll<SVGTextElement, number>('text.mc-ylabel')
    .data(yTickVals)
    .join('text')
    .attr('class', 'mc-ylabel')
    .attr('x', PAD_LEFT - 5)
    .attr('y', (d) => yScale(d) + 3)
    .attr('text-anchor', 'end')
    .attr('fill', c.label)
    .attr('font-size', '8')
    .attr('font-family', 'ui-monospace,monospace')
    .text((d) => fmtMetricVal(d));

  // Y-axis unit label (e.g. "B", "%") above the top tick
  const unitLabel = baseUnit(unit);
  gridG
    .selectAll<SVGTextElement, string>('text.mc-yunit')
    .data(unitLabel ? [unitLabel] : [])
    .join('text')
    .attr('class', 'mc-yunit')
    .attr('x', PAD_LEFT - 5)
    .attr('y', PAD_Y - 2)
    .attr('text-anchor', 'end')
    .attr('fill', c.label)
    .attr('font-size', '8')
    .attr('font-family', 'ui-monospace,monospace')
    .text((d) => d);

  // Threshold lines (warn/crit from perf_data, single-series only)
  let threshG = root.select<SVGGElement>('g.mc-thresholds');
  if (threshG.empty()) threshG = root.insert('g', 'g.mc-series').attr('class', 'mc-thresholds');

  const warnData: number[] =
    !multiSeries && resolvedThresholds?.warn != null ? [resolvedThresholds.warn] : [];
  const critData: number[] =
    !multiSeries && resolvedThresholds?.crit != null ? [resolvedThresholds.crit] : [];

  threshG
    .selectAll<SVGLineElement, number>('line.mc-warn')
    .data(warnData)
    .join('line')
    .attr('class', 'mc-warn')
    .attr('x1', PAD_LEFT)
    .attr('x2', W - PAD_RIGHT)
    .attr('y1', (d) => yScale(d))
    .attr('y2', (d) => yScale(d))
    .attr('stroke', 'rgb(255,208,0)')
    .attr('stroke-width', '1')
    .attr('stroke-dasharray', '4 3')
    .attr('opacity', '0.75');

  threshG
    .selectAll<SVGLineElement, number>('line.mc-crit')
    .data(critData)
    .join('line')
    .attr('class', 'mc-crit')
    .attr('x1', PAD_LEFT)
    .attr('x2', W - PAD_RIGHT)
    .attr('y1', (d) => yScale(d))
    .attr('y2', (d) => yScale(d))
    .attr('stroke', 'rgb(248,113,113)')
    .attr('stroke-width', '1')
    .attr('stroke-dasharray', '4 3')
    .attr('opacity', '0.75');

  const lineGen = line<MetricPoint>()
    .x((d) => xScale(d.ts))
    .y((d) => yScale(d.value))
    .curve(curveMonotoneX);

  // Data join for series groups
  const merged = root
    .selectAll<SVGGElement, string>('g.mc-series')
    .data(labels, (d) => d)
    .join((enter) => {
      const g = enter.append('g').attr('class', 'mc-series');
      g.append('path').attr('class', 'mc-area');
      g.append('path')
        .attr('class', 'mc-line')
        .attr('fill', 'none')
        .attr('stroke-width', '2')
        .attr('stroke-linecap', 'round')
        .attr('stroke-linejoin', 'round');
      g.append('circle')
        .attr('class', 'mc-dot-ring')
        .attr('r', '5')
        .attr('fill', 'none')
        .attr('stroke-width', '1.5');
      g.append('circle').attr('class', 'mc-dot').attr('r', '3');
      return g;
    });

  merged.each(function (label, i) {
    const g = select(this);
    const pts = data[label];
    if (!pts || pts.length === 0) return;

    const latest = pts[pts.length - 1];
    const color = multiSeries
      ? CHART_PALETTE[i % CHART_PALETTE.length]
      : utilColor(valMax > 0 ? Math.min(100, (latest.value / valMax) * 100) : 0);

    const pathD = lineGen(pts)!;

    const areaEl = g.select<SVGPathElement>('.mc-area');
    if (!multiSeries) {
      const areaGen = area<MetricPoint>()
        .x((d) => xScale(d.ts))
        .y0(HC - PAD_Y)
        .y1((d) => yScale(d.value))
        .curve(curveMonotoneX);
      const areaD = areaGen(pts)!;
      defs.select(`#${gradId} stop:first-child`).attr('stop-color', color);
      defs.select(`#${gradId} stop:last-child`).attr('stop-color', color);
      areaEl.attr('fill', `url(#${gradId})`).attr('display', null).attr('d', areaD);
    } else if (fill) {
      const seriesGradId = `mc-area-grad-${i}`;
      let seriesGrad = defs.select<SVGLinearGradientElement>(`#${seriesGradId}`);
      if (seriesGrad.empty()) {
        seriesGrad = defs
          .append<SVGLinearGradientElement>('linearGradient')
          .attr('id', seriesGradId)
          .attr('x1', '0')
          .attr('x2', '0')
          .attr('y1', '0')
          .attr('y2', '1');
        seriesGrad.append('stop').attr('offset', '0%').attr('stop-opacity', '0.28');
        seriesGrad.append('stop').attr('offset', '100%').attr('stop-opacity', '0.02');
      }
      defs.select(`#${seriesGradId} stop:first-child`).attr('stop-color', color);
      defs.select(`#${seriesGradId} stop:last-child`).attr('stop-color', color);
      const areaGen = area<MetricPoint>()
        .x((d) => xScale(d.ts))
        .y0(HC - PAD_Y)
        .y1((d) => yScale(d.value))
        .curve(curveMonotoneX);
      areaEl.attr('fill', `url(#${seriesGradId})`).attr('display', null).attr('d', areaGen(pts)!);
    } else {
      areaEl.attr('display', 'none');
    }

    g.select<SVGPathElement>('.mc-line').attr('stroke', color).attr('d', pathD);
    g.select<SVGCircleElement>('.mc-dot-ring')
      .attr('cx', xScale(latest.ts))
      .attr('cy', yScale(latest.value))
      .attr('stroke', color)
      .attr('opacity', '0.35');
    g.select<SVGCircleElement>('.mc-dot')
      .attr('cx', xScale(latest.ts))
      .attr('cy', yScale(latest.value))
      .attr('fill', color);
  });

  // Time axis separator
  root
    .selectAll<SVGLineElement, number>('line.mc-t-sep')
    .data([0])
    .join('line')
    .attr('class', 'mc-t-sep')
    .attr('x1', PAD_LEFT)
    .attr('x2', W - PAD_RIGHT)
    .attr('y1', HC + 1)
    .attr('y2', HC + 1)
    .attr('stroke', c.sep);

  // Tick marks + labels: left edge, middle, right edge
  type TickDatum = { x: number; label: string; anchor: string };
  const hasRange = tsMax - tsMin > 1;
  const tsMid = (tsMin + tsMax) / 2;
  const ticks: TickDatum[] = hasRange
    ? [
        { x: PAD_LEFT, label: _fmtTime(tsMin), anchor: 'start' },
        { x: (PAD_LEFT + W - PAD_RIGHT) / 2, label: _fmtTime(tsMid), anchor: 'middle' },
        { x: W - PAD_RIGHT, label: _fmtTime(tsMax), anchor: 'end' },
      ]
    : [{ x: W - PAD_RIGHT, label: _fmtTime(tsMax), anchor: 'end' }];

  root
    .selectAll<SVGLineElement, TickDatum>('line.mc-tick')
    .data(ticks, (d) => d.label)
    .join('line')
    .attr('class', 'mc-tick')
    .attr('x1', (d) => d.x)
    .attr('x2', (d) => d.x)
    .attr('y1', HC + 1)
    .attr('y2', HC + 4)
    .attr('stroke', c.timeTick);

  root
    .selectAll<SVGTextElement, TickDatum>('text.mc-t-tick')
    .data(ticks, (d) => d.label)
    .join('text')
    .attr('class', 'mc-t-tick')
    .attr('x', (d) => d.x)
    .attr('y', H - 2)
    .attr('text-anchor', (d) => d.anchor)
    .attr('fill', c.timeLabel)
    .attr('font-size', '9')
    .attr('font-family', 'ui-monospace,monospace')
    .text((d) => d.label);
}

export function useMetricChart(
  svgRef: Ref<SVGSVGElement | null>,
  data: Ref<Record<string, MetricPoint[]>>,
  getWidth: () => number,
  getHeight: () => number,
  getWindowSecs?: () => number,
  getThresholds?: () => { warn: number | null; crit: number | null } | null,
  getUnit?: () => string | undefined,
) {
  function render() {
    if (!svgRef.value) return;
    renderMetricChart(
      svgRef.value,
      data.value,
      getWidth(),
      getHeight(),
      getWindowSecs?.(),
      getThresholds?.(),
      getUnit?.(),
    );
  }

  onMounted(render);
  watch(data, render, { flush: 'post' });
  onUnmounted(() => {
    if (svgRef.value) select(svgRef.value).selectAll('*').interrupt();
  });
}
