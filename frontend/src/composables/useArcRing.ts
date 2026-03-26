import { easeBackOut, easeCubicOut, easeQuadInOut } from 'd3-ease';
import { interpolate, interpolateLab } from 'd3-interpolate';
import { select } from 'd3-selection';
import { arc } from 'd3-shape';
import { transition } from 'd3-transition';
import type { Ref } from 'vue';
import { onMounted, watch } from 'vue';

import { useD3Cleanup } from './useD3Cleanup';

// d3-transition side-effects must be imported for .transition() to work on selections
void transition;

interface ArcRingOptions {
  svgRef: Ref<SVGSVGElement | null>;
  iconSize: Ref<number>;
  pct: Ref<number | null>;
  stateColor: Ref<string>;
  utilColor: Ref<string>;
  enabled: Ref<boolean>;
}

const START_ANGLE = -Math.PI / 2; // 12 o'clock

const STATE_PULSE_COLORS = new Set([
  'rgb(239,68,68)', // DOWN / CRITICAL
  'rgb(249,115,22)', // UNREACHABLE
]);

function buildRing(
  svg: SVGSVGElement,
  iconSize: number,
  pct: number | null,
  stateColor: string,
  utilColor: string,
) {
  const pad = 6;
  const size = iconSize + pad * 2;
  const outerR = iconSize / 2 + pad;
  const ringW = Math.max(3, iconSize * 0.07);
  const innerR = outerR - ringW;

  const root = select(svg);
  root.attr('width', size).attr('height', size);

  let g = root.select<SVGGElement>('g.arc-root');
  if (g.empty()) {
    // pointer-events="none" explicitly on the group so all D3-appended children
    // are guaranteed non-interactive regardless of browser SVG inheritance quirks.
    g = root
      .append('g')
      .attr('class', 'arc-root')
      .attr('pointer-events', 'none')
      .attr('transform', `translate(${size / 2},${size / 2})`);
    // Entrance animation
    g.attr('transform', `translate(${size / 2},${size / 2}) scale(0.6)`)
      .attr('opacity', '0')
      .transition()
      .duration(300)
      .ease(easeBackOut.overshoot(1.4))
      .attr('transform', `translate(${size / 2},${size / 2}) scale(1)`)
      .attr('opacity', '1');
  }

  const arcGen = arc();

  if (pct === null) {
    // No perf_data: simple state-color ring at 35% opacity
    let ring = g.select<SVGPathElement>('path.state-ring');
    if (ring.empty()) {
      ring = g.append('path').attr('class', 'state-ring');
    }
    const d = arcGen({
      innerRadius: innerR,
      outerRadius: outerR,
      startAngle: -Math.PI,
      endAngle: Math.PI,
    })!;
    ring.attr('d', d).attr('fill', stateColor).attr('opacity', '0.35');
    g.select('path.arc-track').remove();
    g.select('path.arc-fg').remove();
    g.select('circle.pulse-ring').remove();
  } else {
    g.select('path.state-ring').remove();

    // Track
    let track = g.select<SVGPathElement>('path.arc-track');
    if (track.empty()) {
      track = g.append('path').attr('class', 'arc-track');
    }
    track
      .attr(
        'd',
        arcGen({
          innerRadius: innerR,
          outerRadius: outerR,
          startAngle: START_ANGLE,
          endAngle: START_ANGLE + 2 * Math.PI,
        })!,
      )
      .attr('fill', 'rgba(255,255,255,0.12)');

    // Progress arc
    const targetAngle = START_ANGLE + (pct / 100) * 2 * Math.PI;
    let fg = g.select<SVGPathElement & { _currentEndAngle?: number }>('path.arc-fg');
    if (fg.empty()) {
      fg = g.append('path').attr('class', 'arc-fg');
      const d = arcGen({
        innerRadius: innerR,
        outerRadius: outerR,
        startAngle: START_ANGLE,
        endAngle: START_ANGLE,
      })!;
      fg.attr('d', d);
      (fg.node() as SVGPathElement & { _currentEndAngle?: number })._currentEndAngle = START_ANGLE;
    }
    const fgNode = fg.node() as SVGPathElement & { _currentEndAngle?: number };
    const fromAngle = fgNode._currentEndAngle ?? START_ANGLE;
    fg.attr('fill', utilColor);
    fg.transition()
      .duration(600)
      .ease(easeQuadInOut)
      .attrTween('d', function () {
        const interp = interpolate(fromAngle, targetAngle);
        return (t: number) => {
          const angle = interp(t);
          fgNode._currentEndAngle = angle;
          return arcGen({
            innerRadius: innerR,
            outerRadius: outerR,
            startAngle: START_ANGLE,
            endAngle: angle,
          })!;
        };
      });
  }

  // Pulse ring for critical states
  g.select('circle.pulse-ring').remove();
}

function addPulse(svg: SVGSVGElement, iconSize: number, stateColor: string) {
  const pad = 6;
  const size = iconSize + pad * 2;
  const outerR = iconSize / 2 + pad;
  const ringW = Math.max(3, iconSize * 0.07);
  const innerR = outerR - ringW;
  const g = select(svg).select<SVGGElement>('g.arc-root');
  if (g.empty()) return;
  g.select('circle.pulse-ring').remove();

  const pulseRing = g
    .append('circle')
    .attr('class', 'pulse-ring')
    .attr('cx', 0)
    .attr('cy', 0)
    .attr('fill', 'none')
    .attr('stroke', stateColor)
    .attr('stroke-width', '1.5');

  function step() {
    pulseRing
      .attr('r', String(innerR))
      .attr('opacity', '0.7')
      .transition()
      .duration(900)
      .ease(easeCubicOut)
      .attr('r', String(outerR + 8))
      .attr('opacity', '0')
      .on('end', step);
  }
  step();
  void size; // suppress unused warning
}

export function useArcRing(opts: ArcRingOptions) {
  function render() {
    const svg = opts.svgRef.value;
    if (!svg || !opts.enabled.value) return;
    buildRing(
      svg,
      opts.iconSize.value,
      opts.pct.value,
      opts.stateColor.value,
      opts.utilColor.value,
    );
  }

  onMounted(render);

  watch([opts.pct, opts.utilColor], render, { flush: 'post' });

  watch(
    opts.stateColor,
    (newColor, oldColor) => {
      const svg = opts.svgRef.value;
      if (!svg || !opts.enabled.value) return;
      const g = select(svg).select<SVGGElement>('g.arc-root');
      if (g.empty()) {
        render();
        return;
      }
      // Animate state ring color if visible
      const ring = g.select<SVGPathElement>('path.state-ring');
      if (!ring.empty()) {
        const interp = interpolateLab(oldColor, newColor);
        ring
          .transition()
          .duration(500)
          .attrTween('fill', () => (t: number) => interp(t));
      }
    },
    { flush: 'post' },
  );

  // Pulse for critical states
  watch(
    opts.stateColor,
    (color) => {
      const svg = opts.svgRef.value;
      if (!svg || !opts.enabled.value) return;
      const g = select(svg).select<SVGGElement>('g.arc-root');
      if (g.empty()) return;
      g.select('circle.pulse-ring').remove();
      if (STATE_PULSE_COLORS.has(color)) {
        addPulse(svg, opts.iconSize.value, color);
      }
    },
    { flush: 'post', immediate: false },
  );

  useD3Cleanup(opts.svgRef);
}
