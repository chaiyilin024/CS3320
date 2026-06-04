import type { EChartsOption } from 'echarts'

/** ECharts 配置对象宽松断言，避免 tooltip/series 回调与类型定义不完全一致导致 build 失败 */
export function asChartOption(option: object): EChartsOption {
  return option as EChartsOption
}
