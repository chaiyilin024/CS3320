import * as echarts from 'echarts/core'
import { BarChart, GraphChart, HeatmapChart, LineChart, PieChart, SankeyChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  PieChart,
  BarChart,
  LineChart,
  GraphChart,
  HeatmapChart,
  SankeyChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  VisualMapComponent,
  CanvasRenderer,
])

export { echarts }

export const HANGDANG_COLORS: Record<string, string> = {
  老生: '#8b4513',
  小生: '#c97b63',
  武生: '#b8860b',
  红生: '#a0522d',
  青衣: '#e91e8c',
  花旦: '#f48fb1',
  刀马旦: '#ad1457',
  老旦: '#6d4c41',
  净: '#1565c0',
  丑: '#ff8f00',
  文武丑: '#ffb300',
  未知: '#9e9e9e',
  其他: '#757575',
}

export function hangdangColor(h: string): string {
  return HANGDANG_COLORS[h] ?? '#888'
}
