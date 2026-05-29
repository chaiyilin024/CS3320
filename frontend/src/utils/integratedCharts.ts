import type { EChartsOption } from 'echarts'
import type { IntegratedCorrelation, PlayIntegrated, PlayNarrative, PlayNetwork } from '@/types'
import { hangdangColor } from '@/utils/charts'
import { stageColor } from '@/utils/narrativeCharts'
import { topicColor } from '@/utils/themeCharts'

export const CORRELATION_TYPE_LABELS: Record<IntegratedCorrelation['type'], string> = {
  character_theme: '人物 ↔ 主题',
  network_stage: '网络 ↔ 阶段',
  hangdang_narrative: '行当 ↔ 叙事',
  theme_narrative: '主题 ↔ 阶段',
  character_network: '人物 ↔ 网络',
  other: '其他',
}

const CORRELATION_COLORS: Record<IntegratedCorrelation['type'], string> = {
  character_theme: '#8b2500',
  network_stage: '#1565c0',
  hangdang_narrative: '#c9a227',
  theme_narrative: '#6a1b9a',
  character_network: '#2e7d32',
  other: '#9e9e9e',
}

function correlations(data: PlayIntegrated | null): IntegratedCorrelation[] {
  return data?.correlations ?? []
}

function correlationLabel(c: IntegratedCorrelation): string {
  switch (c.type) {
    case 'character_theme':
      return `${c.character_name ?? c.character_id} → ${c.topic_label ?? `T${c.topic_id}`}`
    case 'network_stage':
      return `${c.stage}（Δ${((c.edge_density_delta ?? 0) * 100).toFixed(0)}%）`
    case 'hangdang_narrative':
      return `${c.hangdang} @块${c.peak_block_index}`
    case 'theme_narrative':
      return `${c.topic_label ?? `T${c.topic_id}`} ↔ ${c.stage}`
    case 'character_network':
      return `${c.character_name ?? c.character_id} 核心度`
    default:
      return c.evidence?.slice(0, 24) ?? c.type
  }
}

function empty(title: string): EChartsOption {
  return {
    title: { text: title, left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } },
  }
}

export function buildCorrelationTypePie(data: PlayIntegrated | null): EChartsOption {
  const rows = correlations(data)
  if (!rows.length) return empty('暂无跨维度关联')
  const counts = new Map<IntegratedCorrelation['type'], number>()
  rows.forEach((c) => counts.set(c.type, (counts.get(c.type) ?? 0) + 1))
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 条 ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    series: [{
      type: 'pie',
      radius: ['38%', '68%'],
      center: ['50%', '46%'],
      itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{c}', fontSize: 10 },
      data: [...counts.entries()].map(([type, value]) => ({
        name: CORRELATION_TYPE_LABELS[type],
        value,
        itemStyle: { color: CORRELATION_COLORS[type] },
      })),
    }],
  }
}

export function buildTopCorrelationsBar(data: PlayIntegrated | null, limit = 12): EChartsOption {
  const rows = [...correlations(data)]
    .sort((a, b) => b.strength - a.strength)
    .slice(0, limit)
  if (!rows.length) return empty('暂无关联强度数据')
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = (params as Array<{ dataIndex: number }>)[0]
        const c = rows[item.dataIndex]
        return [
          `<b>${correlationLabel(c)}</b>`,
          `类型：${CORRELATION_TYPE_LABELS[c.type]}`,
          `强度：${c.strength.toFixed(3)}`,
          c.evidence ?? '',
        ].filter(Boolean).join('<br/>')
      },
    },
    grid: { left: 120, right: 24, top: 12, bottom: 24 },
    xAxis: { type: 'value', max: 1, name: '关联强度' },
    yAxis: {
      type: 'category',
      data: rows.map(correlationLabel),
      axisLabel: { fontSize: 10, width: 110, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: rows.map((c) => ({
        value: +c.strength.toFixed(3),
        itemStyle: { color: CORRELATION_COLORS[c.type], borderRadius: [0, 6, 6, 0] },
      })),
      barMaxWidth: 16,
    }],
  }
}

export function buildCharacterTopicHeatmap(
  matrix: PlayIntegrated['character_topic_matrix'],
): EChartsOption {
  const cells = matrix ?? []
  if (!cells.length) return empty('暂无人物×主题矩阵')
  const charOrder = [...new Set(cells.map((c) => c.character_name ?? c.character_id))]
  const topicOrder = [...new Set(cells.map((c) => c.topic_label ?? `T${c.topic_id}`))]
  const charIdx = new Map(charOrder.map((n, i) => [n, i]))
  const topicIdx = new Map(topicOrder.map((n, i) => [n, i]))
  const data: [number, number, number][] = cells.map((c) => [
    topicIdx.get(c.topic_label ?? `T${c.topic_id}`) ?? 0,
    charIdx.get(c.character_name ?? c.character_id) ?? 0,
    +c.strength.toFixed(3),
  ])
  const max = Math.max(...data.map((d) => d[2]), 0.01)
  return {
    tooltip: {
      position: 'top',
      formatter: (p: unknown) => {
        const row = p as { data: [number, number, number] }
        const [xi, yi, v] = row.data
        return `${charOrder[yi]} × ${topicOrder[xi]}<br/>关联强度 ${v}`
      },
    },
    grid: { left: 72, right: 24, bottom: 56, top: 16 },
    xAxis: {
      type: 'category',
      data: topicOrder,
      splitArea: { show: true },
      axisLabel: { fontSize: 10, rotate: topicOrder.length > 5 ? 25 : 0 },
    },
    yAxis: {
      type: 'category',
      data: charOrder,
      splitArea: { show: true },
      axisLabel: { fontSize: 10 },
    },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#fff8ee', '#c9a227', '#8b2500'] },
      textStyle: { fontSize: 10 },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: true,
        fontSize: 9,
        formatter: (p: unknown) => {
          const row = p as { data: [number, number, number] }
          return String(row.data[2])
        },
      },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.2)' } },
    }],
  }
}

export function buildCharacterTopicSankey(
  matrix: PlayIntegrated['character_topic_matrix'],
): EChartsOption {
  const cells = [...(matrix ?? [])].sort((a, b) => b.strength - a.strength).slice(0, 16)
  if (!cells.length) return empty('暂无人物-主题流向')
  const nodes: { name: string }[] = []
  const links: { source: string; target: string; value: number }[] = []
  const nodeSet = new Set<string>()
  cells.forEach((c) => {
    const char = c.character_name ?? c.character_id
    const topic = c.topic_label ?? `T${c.topic_id}`
    nodeSet.add(char)
    nodeSet.add(topic)
    links.push({ source: char, target: topic, value: Math.max(0.05, c.strength) })
  })
  nodeSet.forEach((n) => nodes.push({ name: n }))
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'sankey',
      emphasis: { focus: 'adjacency' },
      nodeAlign: 'justify',
      lineStyle: { color: 'gradient', curveness: 0.45, opacity: 0.4 },
      label: { fontSize: 10 },
      data: nodes,
      links,
    }],
  } as EChartsOption
}

export function buildStageNetworkEvolution(
  snaps: PlayIntegrated['stage_network_snapshots'],
): EChartsOption {
  const rows = snaps ?? []
  if (!rows.length) return empty('暂无阶段网络快照')
  const stages = rows.map((s) => s.stage)
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 48, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: stages, axisLabel: { fontSize: 11 } },
    yAxis: [
      { type: 'value', name: '网络密度', min: 0, max: 1, axisLabel: { fontSize: 10 } },
      { type: 'value', name: '节点/边数', minInterval: 1, axisLabel: { fontSize: 10 } },
    ],
    series: [
      {
        name: '同场网络密度',
        type: 'line',
        smooth: true,
        symbolSize: 8,
        lineStyle: { width: 3, color: '#8b2500' },
        itemStyle: { color: '#8b2500' },
        areaStyle: { color: 'rgba(139, 37, 0, 0.08)' },
        data: rows.map((s) => +s.edge_density.toFixed(3)),
      },
      {
        name: '活跃人物数',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 28,
        itemStyle: { color: '#1565c0', borderRadius: [4, 4, 0, 0] },
        data: rows.map((s) => s.node_count),
      },
      {
        name: '关系边数',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 28,
        itemStyle: { color: '#c9a227', borderRadius: [4, 4, 0, 0] },
        data: rows.map((s) => s.edge_count ?? 0),
      },
    ],
  }
}

export function buildNetworkStageDeltaBar(data: PlayIntegrated | null): EChartsOption {
  const rows = correlations(data).filter((c) => c.type === 'network_stage')
  if (!rows.length) return empty('暂无阶段网络变化')
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = (params as Array<{ dataIndex: number }>)[0]
        const c = rows[item.dataIndex]
        return [
          `<b>${c.stage}</b>`,
          `密度变化 ${((c.edge_density_delta ?? 0) * 100).toFixed(1)}%`,
          c.evidence ?? '',
        ].join('<br/>')
      },
    },
    grid: { left: 48, right: 16, top: 16, bottom: 28 },
    xAxis: { type: 'category', data: rows.map((c) => c.stage ?? ''), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '密度变化', axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(0)}%` } },
    series: [{
      type: 'bar',
      data: rows.map((c) => ({
        value: +(c.edge_density_delta ?? 0).toFixed(4),
        itemStyle: {
          color: (c.edge_density_delta ?? 0) >= 0 ? '#2e7d32' : '#8b2500',
          borderRadius: (c.edge_density_delta ?? 0) >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4],
        },
      })),
      barMaxWidth: 36,
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { type: 'dashed', color: '#bbb' },
        data: [{ yAxis: 0 }],
      },
    }],
  }
}

export function buildThemeStageHeatmap(data: PlayIntegrated | null): EChartsOption {
  const rows = correlations(data).filter((c) => c.type === 'theme_narrative')
  const snaps = data?.stage_network_snapshots ?? []
  const stages = snaps.length
    ? snaps.map((s) => s.stage)
    : [...new Set(rows.map((c) => c.stage).filter(Boolean) as string[])]
  const topics = [...new Set(rows.map((c) => c.topic_label ?? `T${c.topic_id}`))]
  if (!stages.length || !topics.length) return empty('暂无主题-阶段关联')
  const stageIdx = new Map(stages.map((s, i) => [s, i]))
  const topicIdx = new Map(topics.map((t, i) => [t, i]))
  const heat: [number, number, number][] = rows.map((c) => [
    stageIdx.get(c.stage ?? '') ?? 0,
    topicIdx.get(c.topic_label ?? `T${c.topic_id}`) ?? 0,
    +c.strength.toFixed(3),
  ])
  const max = Math.max(...heat.map((d) => d[2]), 0.01)
  return {
    tooltip: {
      position: 'top',
      formatter: (p: unknown) => {
        const row = p as { data: [number, number, number] }
        const [xi, yi, v] = row.data
        return `${topics[yi]} × ${stages[xi]}<br/>关联 ${v}`
      },
    },
    grid: { left: 88, right: 24, bottom: 48, top: 16 },
    xAxis: { type: 'category', data: stages, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'category', data: topics, axisLabel: { fontSize: 10 } },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f3e5f5', '#6a1b9a', '#4a148c'] },
      textStyle: { fontSize: 10 },
    },
    series: [{
      type: 'heatmap',
      data: heat,
      label: { show: true, fontSize: 9 },
    }],
  }
}

export function buildHangdangPeakBar(data: PlayIntegrated | null): EChartsOption {
  const rows = correlations(data).filter((c) => c.type === 'hangdang_narrative')
  if (!rows.length) return empty('暂无行当叙事峰值')
  return {
    tooltip: {
      formatter: (p: unknown) => {
        const row = p as { name: string; data: { value: number; block: number } }
        return `${row.name}<br/>情感峰值块 #${row.data.block}<br/>强度 ${row.data.value.toFixed(2)}<br/>${rows.find((r) => r.hangdang === row.name)?.evidence ?? ''}`
      },
    },
    grid: { left: 48, right: 16, top: 16, bottom: 28 },
    xAxis: { type: 'category', data: rows.map((c) => c.hangdang ?? ''), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '峰值块序号' },
    series: [{
      type: 'bar',
      data: rows.map((c) => ({
        value: c.peak_block_index ?? 0,
        block: c.peak_block_index ?? 0,
        itemStyle: { color: hangdangColor(c.hangdang ?? ''), borderRadius: [4, 4, 0, 0] },
      })),
      barMaxWidth: 40,
    }],
  }
}

export function buildRhythmTensionOverlay(
  narrative: PlayNarrative | null,
  snaps: PlayIntegrated['stage_network_snapshots'],
): EChartsOption {
  const series = narrative?.rhythm_series ?? []
  const stages = snaps ?? []
  if (!series.length) return empty('暂无叙事节奏数据')
  const markArea = stages.length
    ? {
        silent: true,
        data: stages.map((s) => [
          {
            name: s.stage,
            itemStyle: {
              color: `${stageColor(s.stage)}33`,
              borderColor: stageColor(s.stage),
              borderWidth: 1,
            },
            label: {
              show: true,
              position: 'insideTop' as const,
              formatter: s.stage,
              fontSize: 10,
              color: stageColor(s.stage),
            },
            coord: [s.block_range[0], 0],
          },
          { coord: [s.block_range[1], 1] },
        ]),
      }
    : undefined
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 48, top: 36, bottom: 28 },
    xAxis: { type: 'value', name: '正文块' },
    yAxis: [
      { type: 'value', name: '张力', max: 1 },
      { type: 'value', name: '网络密度', min: 0, max: 1 },
    ],
    series: [
      {
        name: '叙事张力',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2.5, color: '#8b2500' },
        data: series.map((p) => [p.block_index, p.tension_score ?? 0]),
        markArea,
      },
      {
        name: '阶段网络密度',
        type: 'line',
        yAxisIndex: 1,
        step: 'middle',
        symbolSize: 7,
        lineStyle: { width: 2, color: '#1565c0', type: 'dashed' },
        data: stages.flatMap((s) => {
          const mid = Math.round((s.block_range[0] + s.block_range[1]) / 2)
          return [
            [s.block_range[0], s.edge_density],
            [mid, s.edge_density],
            [s.block_range[1], s.edge_density],
          ]
        }),
      },
    ],
  } as EChartsOption
}

export function buildCharacterCentralityBar(
  data: PlayIntegrated | null,
  net: PlayNetwork | null,
): EChartsOption {
  const fromCorr = correlations(data)
    .filter((c) => c.type === 'character_network')
    .sort((a, b) => b.strength - a.strength)
  const nodes = [...(net?.nodes ?? [])]
    .sort((a, b) => (b.weighted_degree ?? b.degree) - (a.weighted_degree ?? a.degree))
    .slice(0, 10)
  if (!nodes.length && !fromCorr.length) return empty('暂无人物中心性')
  const names = nodes.length
    ? nodes.map((n) => n.name)
    : fromCorr.map((c) => c.character_name ?? c.character_id ?? '')
  const values = nodes.length
    ? nodes.map((n) => n.weighted_degree ?? n.degree)
    : fromCorr.map((c) => c.strength * 100)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const item = (params as Array<{ dataIndex: number; value: number }>)[0]
        const n = nodes[item.dataIndex]
        if (!n) return `${names[item.dataIndex]}: ${item.value}`
        return [
          `<b>${n.name}</b>（${n.hangdang}）`,
          `加权度 ${(n.weighted_degree ?? n.degree).toFixed(1)}`,
          `介数 ${(n.betweenness ?? 0).toFixed(3)}`,
        ].join('<br/>')
      },
    },
    grid: { left: 72, right: 16, top: 12, bottom: 28 },
    xAxis: { type: 'value', name: nodes.length ? '加权度' : '关联强度' },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 10 } },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: +v.toFixed(2),
        itemStyle: {
          color: hangdangColor(nodes[i]?.hangdang ?? ''),
          borderRadius: [0, 5, 5, 0],
        },
      })),
      barMaxWidth: 16,
    }],
  }
}

export function buildTopicWeightMini(topics: Array<{ topic_id: number; label: string; weight: number }>): EChartsOption {
  if (!topics.length) return empty('暂无主题数据')
  const rows = [...topics].sort((a, b) => b.weight - a.weight)
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: 88, right: 16, top: 8, bottom: 24 },
    xAxis: { type: 'value', max: 100, name: '%' },
    yAxis: {
      type: 'category',
      data: rows.map((t) => t.label),
      axisLabel: { fontSize: 10 },
    },
    series: [{
      type: 'bar',
      data: rows.map((t) => ({
        value: +(t.weight * 100).toFixed(1),
        itemStyle: { color: topicColor(t.topic_id), borderRadius: [0, 5, 5, 0] },
      })),
      barMaxWidth: 14,
    }],
  }
}

export interface IntegratedKpi {
  label: string
  value: string
  hint?: string
}

export function buildKpis(
  data: PlayIntegrated | null,
  net: PlayNetwork | null,
  narrative: PlayNarrative | null,
): IntegratedKpi[] {
  if (!data) return []
  const corrCount = data.correlations?.length ?? 0
  const charCount = net?.metrics?.node_count ?? net?.nodes?.length ?? 0
  const density = net?.metrics?.density
  const stageCount = narrative?.plot_stages?.length ?? data.stage_network_snapshots?.length ?? 0
  const matrixCells = data.character_topic_matrix?.length ?? 0
  return [
    { label: '跨维关联', value: String(corrCount), hint: '自动挖掘的关联规则' },
    { label: '主要人物', value: String(charCount), hint: '关系网络节点' },
    { label: '网络密度', value: density != null ? density.toFixed(2) : '—', hint: '全剧同场关系紧密度' },
    { label: '叙事阶段', value: String(stageCount), hint: '情节结构划分' },
    { label: '人物×主题', value: String(matrixCells), hint: '矩阵关联格数' },
  ]
}
