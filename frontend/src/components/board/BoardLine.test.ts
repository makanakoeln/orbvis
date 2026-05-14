import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import type { BoardObject, ObjectState } from '@/types/api';

import BoardLine from './BoardLine.vue';

function makeLineObject(overrides: Partial<BoardObject> = {}): BoardObject {
    return {
        id: 'line_1',
        type: 'line',
        x: 100,
        y: 100,
        x2: 250,
        y2: 100,
        line_style: 'plain',
        label: { show: false, x: 0, y: 0, size: 10, color: '#fff', background: 'transparent' },
        url_target: '_blank',
        z: 1,
        ...overrides,
    };
}

const noState: ObjectState = {
    object_id: 'line_1',
    type: 'host',
    state: 'UP',
    output: '',
    perf_data: '',
    acknowledged: false,
    in_downtime: false,
    stale: false,
};

// A weather-coloured line is the orthogonal `line_weather_color: true` flag,
// independent of the chosen shape. These tests pin the gradient render path.
const weatherProps = {
    line_style: 'arrow_inward' as const,
    line_weather_color: true,
    host_name: 'h',
    service_description: 's',
};

describe('BoardLine – weather-color gradient', () => {
    it('renders a <defs> linearGradient when line_weather_color is set', () => {
        const wrapper = mount(BoardLine, {
            props: {
                object: makeLineObject(weatherProps),
                state: noState,
                editMode: false,
            },
        });
        expect(wrapper.find('defs').exists()).toBe(true);
        expect(wrapper.find('linearGradient').exists()).toBe(true);
    });

    it('uses gradientUnits="userSpaceOnUse" (not objectBoundingBox)', () => {
        const wrapper = mount(BoardLine, {
            props: {
                object: makeLineObject(weatherProps),
                state: noState,
                editMode: false,
            },
        });
        const grad = wrapper.find('linearGradient');
        expect(grad.attributes('gradientunits')).toBe('userSpaceOnUse');
    });

    it('binds gradient x1/y1/x2/y2 to line start/end coordinates', () => {
        const obj = makeLineObject({ ...weatherProps, x: 50, y: 80, x2: 300, y2: 200 });
        const wrapper = mount(BoardLine, {
            props: { object: obj, state: noState, editMode: false },
        });
        const grad = wrapper.find('linearGradient');
        expect(grad.attributes('x1')).toBe('50');
        expect(grad.attributes('y1')).toBe('80');
        expect(grad.attributes('x2')).toBe('300');
        expect(grad.attributes('y2')).toBe('200');
    });

    it('gradient id matches the stroke url() reference', () => {
        const wrapper = mount(BoardLine, {
            props: {
                object: makeLineObject(weatherProps),
                state: noState,
                editMode: false,
            },
        });
        const gradId = wrapper.find('linearGradient').attributes('id');
        const lineStroke = wrapper
            .findAll('line')
            .find((l) => l.attributes('stroke')?.startsWith('url('));
        expect(lineStroke).toBeDefined();
        expect(lineStroke!.attributes('stroke')).toBe(`url(#${gradId})`);
    });

    it('does not render a <defs> for non-weather-coloured lines', () => {
        const wrapper = mount(BoardLine, {
            props: {
                object: makeLineObject({ line_style: 'plain' }),
                state: noState,
                editMode: false,
            },
        });
        expect(wrapper.find('defs').exists()).toBe(false);
    });
});

describe('BoardLine – styling regressions', () => {
    it('plain lines do not render a dot at the endpoint', () => {
        const wrapper = mount(BoardLine, {
            props: {
                object: makeLineObject({ line_style: 'plain' }),
                state: noState,
                editMode: false,
            },
        });
        // Only the invisible hit-area + the visible stroke are expected; no
        // decorative <circle> at the endpoint.
        expect(wrapper.findAll('circle').length).toBe(0);
    });

    it('dashed line scales stroke-dasharray with line_width', () => {
        const thin = mount(BoardLine, {
            props: {
                object: makeLineObject({ line_style: 'dashed', line_width: 2 }),
                state: noState,
                editMode: false,
            },
        });
        const thick = mount(BoardLine, {
            props: {
                object: makeLineObject({ line_style: 'dashed', line_width: 15 }),
                state: noState,
                editMode: false,
            },
        });
        const thinDash = thin.findAll('line').at(-1)!.attributes('stroke-dasharray');
        const thickDash = thick.findAll('line').at(-1)!.attributes('stroke-dasharray');
        expect(thinDash).toBeDefined();
        expect(thickDash).toBeDefined();
        // First number of "<gap> <dash>"
        const thinFirst = parseFloat(thinDash!.split(' ')[0]);
        const thickFirst = parseFloat(thickDash!.split(' ')[0]);
        expect(thickFirst).toBeGreaterThan(thinFirst);
    });

    it('arrow_end shortens the stroke so the cap sits behind the arrow tip', () => {
        const wrapper = mount(BoardLine, {
            props: {
                object: makeLineObject({
                    line_style: 'arrow_end',
                    line_width: 15,
                    x: 0,
                    y: 0,
                    x2: 200,
                    y2: 0,
                }),
                state: noState,
                editMode: false,
            },
        });
        const visibleLine = wrapper.findAll('line').at(-1)!;
        const x2 = parseFloat(visibleLine.attributes('x2')!);
        // Stroke must end before the arrow tip (x=200).
        expect(x2).toBeLessThan(200);
        // Arrow polygon's first vertex is the tip — should still anchor at x=200.
        const polygon = wrapper.find('polygon');
        expect(polygon.exists()).toBe(true);
        const tip = polygon.attributes('points')!.split(' ')[0];
        expect(parseFloat(tip.split(',')[0])).toBe(200);
    });

    it('arrow_inward (middle) arrows scale with line_width', () => {
        const thin = mount(BoardLine, {
            props: {
                object: makeLineObject({ line_style: 'arrow_inward', line_width: 2 }),
                state: noState,
                editMode: false,
            },
        });
        const thick = mount(BoardLine, {
            props: {
                object: makeLineObject({ line_style: 'arrow_inward', line_width: 15 }),
                state: noState,
                editMode: false,
            },
        });
        // Both render the two midpoint triangles.
        expect(thin.findAll('polygon').length).toBeGreaterThanOrEqual(2);
        expect(thick.findAll('polygon').length).toBeGreaterThanOrEqual(2);
        // The right triangle's points string encodes a base offset perpendicular
        // to the line — at width=15 the triangle is geometrically larger.
        const thinPoly = thin.findAll('polygon')[0].attributes('points')!;
        const thickPoly = thick.findAll('polygon')[0].attributes('points')!;
        // Compare the spread between the three vertices' x coordinates.
        const xs = (s: string) => s.split(' ').map((p) => parseFloat(p.split(',')[0]));
        const span = (s: string) => Math.max(...xs(s)) - Math.min(...xs(s));
        expect(span(thickPoly)).toBeGreaterThan(span(thinPoly));
    });
});
