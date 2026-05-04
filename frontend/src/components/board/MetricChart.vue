<script lang="ts">
import { LineChart } from 'echarts/charts';
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';

use([CanvasRenderer, LineChart, GridComponent, MarkLineComponent, TooltipComponent]);

export default {};
</script>

<script setup lang="ts">
import type { LineSeriesOption } from 'echarts/charts';
import type {
    GridComponentOption,
    MarkLineComponentOption,
    TooltipComponentOption,
} from 'echarts/components';
import type { ComposeOption } from 'echarts/core';
import { computed } from 'vue';
import VChart from 'vue-echarts';

import {
    baseUnit,
    CHART_PALETTE,
    fmtValueWithUnit,
    normalizeMetricValue,
} from '@/composables/useMetricChart';
import type { MetricPoint } from '@/stores/states';

type EOption = ComposeOption<
    GridComponentOption | LineSeriesOption | MarkLineComponentOption | TooltipComponentOption
>;

interface TooltipParam {
    seriesName: string;
    value: [number, number];
    marker: string;
}

const props = defineProps<{
    data: Record<string, MetricPoint[]>;
    metricKeys: string[];
    windowSecs: number;
    thresholds: { warn: number | null; crit: number | null } | null;
    unit: string | undefined;
    dark: boolean;
}>();

function _fmtTime(ms: number): string {
    const d = new Date(ms);
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

function _hexToRgba(hex: string, alpha: number): string {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r},${g},${b},${alpha})`;
}

function _fmtVal(normalized: number): string {
    return fmtValueWithUnit(normalized, props.unit);
}

function _buildTooltip(rawParams: TooltipParam | TooltipParam[]): string {
    const items = Array.isArray(rawParams) ? rawParams : [rawParams];
    if (!items.length) return '';
    const ts = items[0].value[0];
    const rows = items
        .map(
            (p) =>
                `${p.marker}<span style="font-size:9px"> ${p.seriesName}: <b>${_fmtVal(p.value[1])}</b></span>`,
        )
        .join('<br/>');
    return `<div style="font-size:9px;opacity:0.7;margin-bottom:2px">${_fmtTime(ts)}</div>${rows}`;
}

// Converts perf_data raw value to base unit. Needed because ECharts handles its own
// axis scaling, so all data must be in consistent base units (e.g. bytes not kB).
function _norm(v: number, unitHint?: string): number {
    const u = unitHint ?? props.unit;
    return normalizeMetricValue(v, u);
}

// Y-axis formatter: render the unit inline on every tick so the SI prefix folds into
// the base unit symbol ("60.0 MB/s", not "60.0M" with a separate "B/s" floating in
// the corner). Keeps the tooltip and the axis visually consistent.
function _fmtAxis(v: number): string {
    return fmtValueWithUnit(v, props.unit);
}

const option = computed((): EOption => {
    const dark = props.dark;
    const textColor = dark ? 'rgba(255,255,255,0.60)' : 'rgba(0,0,0,0.55)';
    const gridColor = dark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.15)';
    const axisColor = dark ? 'rgba(255,255,255,0.30)' : 'rgba(0,0,0,0.30)';
    const tooltipBg = dark ? 'rgba(24,24,27,0.96)' : 'rgba(255,255,255,0.96)';
    const tooltipBorder = dark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.12)';
    const multiSeries = props.metricKeys.length > 1;
    const unit = props.unit;

    const now = Date.now();
    const xMin = props.windowSecs > 0 ? now - props.windowSecs * 1000 : undefined;
    const xMax = props.windowSecs > 0 ? now : undefined;

    const series: LineSeriesOption[] = props.metricKeys.map((key, i) => {
        const pts = props.data[key] ?? [];
        const color = CHART_PALETTE[i % CHART_PALETTE.length];

        // Build threshold markLines for single-series charts only
        const markLineItems: NonNullable<NonNullable<LineSeriesOption['markLine']>['data']> = [];
        if (!multiSeries && i === 0 && props.thresholds) {
            if (props.thresholds.warn !== null) {
                markLineItems.push({
                    yAxis: _norm(props.thresholds.warn),
                    lineStyle: { color: 'rgb(255,208,0)', type: 'dashed', width: 1, opacity: 0.75 },
                    label: { show: false },
                });
            }
            if (props.thresholds.crit !== null) {
                markLineItems.push({
                    yAxis: _norm(props.thresholds.crit),
                    lineStyle: {
                        color: 'rgb(248,113,113)',
                        type: 'dashed',
                        width: 1,
                        opacity: 0.75,
                    },
                    label: { show: false },
                });
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
                        { offset: 1, color: _hexToRgba(color, 0.02) },
                    ],
                },
            },
            data: pts.map((p) => [p.ts * 1000, _norm(p.value, p.unit)]),
            ...(markLineItems.length > 0
                ? {
                      markLine: {
                          silent: true,
                          symbol: ['none', 'none'],
                          data: markLineItems,
                      },
                  }
                : {}),
        };
    });

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
                hideOverlap: true,
            },
            splitLine: { show: false },
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
                showMaxLabel: false,
            },
            splitLine: { lineStyle: { color: gridColor } },
            splitNumber: 4,
            min: (extent: { min: number; max: number }): number =>
                Math.max(0, extent.min - (extent.max - extent.min) * 0.15),
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                label: { show: false },
                crossStyle: { color: axisColor },
            },
            backgroundColor: tooltipBg,
            borderColor: tooltipBorder,
            textStyle: { color: textColor, fontSize: 10, fontFamily: 'ui-monospace,monospace' },
            padding: [6, 8],
            formatter: _buildTooltip as (params: unknown) => string,
        },
        series,
    };
});
</script>

<template>
    <v-chart class="w-full h-full" :option="option" :autoresize="true" />
</template>
