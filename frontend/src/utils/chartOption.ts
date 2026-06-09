import type { EChartsOption } from 'echarts'

/** Loose cast for ECharts option objects; avoids build failures when tooltip/series callbacks don't match types exactly */
export function asChartOption(option: object): EChartsOption {
  return option as EChartsOption
}
