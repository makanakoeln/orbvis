import { select } from 'd3';
import type { Ref } from 'vue';
import { onUnmounted } from 'vue';

/** Cancels all pending D3 transitions on the given SVG element when the component unmounts. */
export function useD3Cleanup(svgRef: Ref<SVGSVGElement | null>): void {
  onUnmounted(() => {
    const svg = svgRef.value;
    if (svg) select(svg).selectAll('*').interrupt();
  });
}
