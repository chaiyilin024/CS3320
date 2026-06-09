import type { EChartsOption } from 'echarts'
import type { PlayIntegrated, PlayNarrative, PlayNetwork } from '@/types'
import { asChartOption } from './chartOption'
import { buildForceGraph } from './networkCharts'

type MatrixCell = NonNullable<PlayIntegrated['character_topic_matrix']>[number]
type Snapshot = NonNullable<PlayIntegrated['stage_network_snapshots']>[number]

function avgTensionInRange(
  narrative: PlayNarrative,
  range: [number, number],
): number {
  const pts = (narrative.rhythm_series ?? []).filter(
    (p) => p.block_index >= range[0] && p.block_index <= range[1],
  )
  if (!pts.length) return 0
  const sum = pts.reduce((a, p) => a + (p.tension_score ?? 0), 0)
  return sum / pts.length
}

export function pivotCharacterTopicMatrix(matrix: MatrixCell[]) {
  const chars = [...new Map(matrix.map((c) => [c.character_id, c.character_name ?? c.character_id])).entries()]
    .sort((a, b) => {
      const sa = matrix.find((x) => x.character_id === a[0])?.strength ?? 0
      const sb = matrix.find((x) => x.character_id === b[0])?.strength ?? 0
      return sb - sa
    })
    .slice(0, 12)

  const topicMap = new Map<number, string>()
  matrix.forEach((c) => topicMap.set(c.topic_id, c.topic_label ?? `T${c.topic_id}`))
  const topics = [...topicMap.entries()].sort((a, b) => a[0] - b[0])
  return { chars, topics }
}

export function buildCharacterTopicHeatmap(matrix: MatrixCell[]): EChartsOption {
  if (!matrix.length) {
    return asChartOption({
      title: { text: '暂无人物×主题数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } },
    })
  }

  const { chars, topics } = pivotCharacterTopicMatrix(matrix)

  const data: [number, number, number][] = []
  chars.forEach(([cid], yi) => {
    topics.forEach(([tid], xi) => {
      const cell = matrix.find((c) => c.character_id === cid && c.topic_id === tid)
      data.push([xi, yi, cell ? cell.strength : 0])
    })
  })

  const max = Math.max(...data.map((d) => d[2]), 0.01)

  return asChartOption({
    tooltip: {
      position: 'top',
      formatter: (p: unknown) => {
        const item = p as { data?: [number, number, number] }
        const [xi, yi, v] = item.data ?? [0, 0, 0]
        return `${chars[yi]?.[1]} × ${topics[xi]?.[1]}<br/>关联 ${v.toFixed(2)}`
      },
    },
    grid: { left: 72, right: 16, top: 12, bottom: 56 },
    xAxis: {
      type: 'category',
      data: topics.map(([, label]) => label),
      axisLabel: { rotate: 28, fontSize: 10 },
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: chars.map(([, name]) => name),
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemHeight: 80,
      inRange: { color: ['#f5f0e8', '#c9a227', '#8b2500'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: true,
        formatter: (p: unknown) => {
          const v = (p as { data?: [number, number, number] }).data?.[2] ?? 0
          return v >= 0.15 ? v.toFixed(2) : ''
        },
        fontSize: 9,
      },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.2)' } },
    }],
  })
}

export function buildTensionDensityOverlay(
  narrative: PlayNarrative,
  snapshots: Snapshot[],
): EChartsOption {
  if (!snapshots.length) {
    return asChartOption({
      title: { text: '暂无阶段网络数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } },
    })
  }

  const stages = snapshots.map((s) => s.stage)
  const tensions = snapshots.map((s) =>
    +avgTensionInRange(narrative, s.block_range).toFixed(3),
  )
  const densities = snapshots.map((s) => s.edge_density)

  return asChartOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['阶段平均张力', '网络边密度'], bottom: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 48, top: 28, bottom: 40 },
    xAxis: { type: 'category', data: stages },
    yAxis: [
      {
        type: 'value',
        name: '张力',
        max: 1,
        splitLine: { lineStyle: { type: 'dashed', opacity: 0.35 } },
      },
      {
        type: 'value',
        name: '密度',
        max: Math.max(...densities, 0.1) * 1.2,
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '阶段平均张力',
        type: 'line',
        smooth: true,
        yAxisIndex: 0,
        lineStyle: { width: 2, color: '#6a1b9a' },
        itemStyle: { color: '#6a1b9a' },
        data: tensions,
      },
      {
        name: '网络边密度',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 36,
        itemStyle: { color: '#1565c0', opacity: 0.75 },
        data: densities,
      },
    ],
  })
}

export function buildMiniStageGraph(
  net: PlayNetwork,
  nodes: PlayNetwork['nodes'],
  links: PlayNetwork['links'],
  selectedIds: string[],
): EChartsOption {
  const opt = buildForceGraph(net, selectedIds, { nodes, links })
  const series = (opt.series as Array<Record<string, unknown>>)?.[0]
  if (series) {
    series.roam = false
    series.force = { ...(series.force as object), repulsion: 120, edgeLength: [40, 90] }
    series.label = { show: true, fontSize: 9, position: 'right' }
  }
  return opt
}

export const CORRELATION_TYPE_LABELS: Record<string, string> = {
  character_theme: '人物—主题',
  network_stage: '网络—阶段',
  theme_narrative: '主题—叙事',
  hangdang_narrative: '行当—叙事',
  character_network: '人物—网络',
  other: '其他',
}
