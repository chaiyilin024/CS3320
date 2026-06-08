import * as echarts from 'echarts/core'
import {
  BarChart,
  BoxplotChart,
  GraphChart,
  HeatmapChart,
  LineChart,
  PieChart,
  SankeyChart,
  ScatterChart,
  TreemapChart,
  RadarChart,
} from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  PolarComponent,
  RadarComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  PieChart,
  BarChart,
  BoxplotChart,
  LineChart,
  GraphChart,
  HeatmapChart,
  SankeyChart,
  ScatterChart,
  TreemapChart,
  RadarChart,
  GridComponent,
  PolarComponent,
  RadarComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  VisualMapComponent,
  DataZoomComponent,
  MarkAreaComponent,
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

export const GENRE_COLORS: Record<string, string> = {
  历史剧: '#8b2500',
  家庭剧: '#c9a227',
  爱情剧: '#d4537a',
  侠义剧: '#1565c0',
  公案剧: '#2e7d32',
  神话剧: '#6a1b9a',
  战争剧: '#bf360c',
  其他: '#9e9e9e',
  未知: '#bdbdbd',
}

export function genreColor(g: string): string {
  return GENRE_COLORS[g] ?? '#888'
}

export const COARSE_COLORS: Record<string, string> = {
  生: '#8b4513',
  旦: '#d4537a',
  净: '#1565c0',
  丑: '#ff8f00',
  未知: '#9e9e9e',
  其他: '#757575',
}

export function coarseColor(c: string): string {
  return COARSE_COLORS[c] ?? '#888'
}
