import type { EChartsOption } from 'echarts'
import type { NetworkCompareGlobal, PlayNetwork } from '@/types'
import { hangdangColor } from '@/utils/charts'

type NetNode = PlayNetwork['nodes'][number]
type NetLink = PlayNetwork['links'][number]

const COMMUNITY_COLORS = [
  '#8b2500', '#1565c0', '#2e7d32', '#c9a227', '#6a1b9a', '#bf360c', '#00838f', '#5d4037',
]

function topNodes(nodes: NetNode[], n: number, key: keyof NetNode = 'weighted_degree'): NetNode[] {
  return [...nodes]
    .sort((a, b) => (Number(b[key] ?? b.degree) || 0) - (Number(a[key] ?? a.degree) || 0))
    .slice(0, n)
}

function norm(values: number[]): number[] {
  const max = Math.max(...values, 1e-9)
  return values.map((v) => Math.round((v / max) * 100))
}

function linkWeightMap(links: NetLink[]): Map<string, number> {
  const m = new Map<string, number>()
  for (const l of links) {
    const k = [l.source, l.target].sort().join('|')
    m.set(k, l.weight)
  }
  return m
}

export function buildForceGraph(
  net: PlayNetwork,
  selectedIds: string[],
): EChartsOption {
  const sel = new Set(selectedIds)
  return {
    tooltip: {
      formatter: (p: { dataType?: string; data?: NetNode & { value?: number }; name?: string }) => {
        if (p.dataType === 'edge') {
          const d = p.data as { value?: number }
          return `关系强度 ${d?.value ?? ''}`
        }
        const n = net.nodes.find((x) => x.name === p.name)
        if (!n) return p.name ?? ''
        return [
          `<b>${n.name}</b>（${n.hangdang}）`,
          `度 ${n.degree} · 加权度 ${(n.weighted_degree ?? 0).toFixed(1)}`,
          `介数 ${(n.betweenness ?? 0).toFixed(3)} · 接近 ${(n.closeness ?? 0).toFixed(3)}`,
          n.is_main ? '主要人物' : '配角',
        ].join('<br/>')
      },
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      data: net.nodes.map((node) => ({
        id: node.id,
        name: node.name,
        symbolSize: Math.max(14, 10 + (node.weighted_degree ?? node.degree) * 0.15),
        itemStyle: {
          color: hangdangColor(node.hangdang),
          borderWidth: sel.has(node.id) ? 3 : node.is_main ? 2 : 0,
          borderColor: sel.has(node.id) ? '#c9a227' : '#fff',
          shadowBlur: sel.has(node.id) ? 12 : 0,
          shadowColor: 'rgba(201, 162, 39, 0.5)',
        },
        label: { show: true, fontSize: 11, fontWeight: node.is_main ? 'bold' : 'normal' },
      })),
      links: net.links.map((l) => ({
        source: l.source,
        target: l.target,
        value: l.weight,
        lineStyle: {
          width: Math.max(1, (l.normalized_weight ?? l.weight / 80) * 6),
          opacity: 0.35 + (l.normalized_weight ?? 0.3) * 0.5,
          curveness: 0.15,
        },
      })),
      force: { repulsion: 280, gravity: 0.08, edgeLength: [60, 140], friction: 0.6 },
      emphasis: { focus: 'adjacency', lineStyle: { width: 6 } },
    }],
  }
}

export function buildCircularCommunityGraph(
  net: PlayNetwork,
  selectedIds: string[],
): EChartsOption {
  const sel = new Set(selectedIds)
  const communities = [...new Set(net.nodes.map((n) => n.community_id ?? 0))]
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'graph',
      layout: 'circular',
      circular: { rotateLabel: true },
      roam: true,
      data: net.nodes.map((node) => {
        const cid = node.community_id ?? 0
        const ci = communities.indexOf(cid)
        return {
          id: node.id,
          name: node.name,
          symbolSize: Math.max(12, 8 + node.degree * 2),
          itemStyle: {
            color: COMMUNITY_COLORS[ci % COMMUNITY_COLORS.length],
            borderWidth: sel.has(node.id) ? 3 : 0,
            borderColor: '#c9a227',
          },
          label: { show: true, fontSize: 10 },
        }
      }),
      links: net.links.map((l) => ({
        source: l.source,
        target: l.target,
        lineStyle: { opacity: 0.25, width: 1 },
      })),
      categories: communities.map((c, i) => ({
        name: `社区 ${c}`,
        itemStyle: { color: COMMUNITY_COLORS[i % COMMUNITY_COLORS.length] },
      })),
    }],
  }
}

export function buildWeightedDegreeBar(nodes: NetNode[]): EChartsOption {
  const rows = topNodes(nodes, 12, 'weighted_degree')
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p: unknown) => {
        const item = (p as { dataIndex: number }[])[0]
        const n = rows[item.dataIndex]
        return `${n.name}<br/>加权度 ${(n.weighted_degree ?? 0).toFixed(1)} · 度 ${n.degree}`
      },
    },
    grid: { left: 72, right: 20, top: 12, bottom: 24 },
    xAxis: { type: 'value', name: '加权度' },
    yAxis: { type: 'category', data: rows.map((n) => n.name), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: rows.map((n) => ({
        value: n.weighted_degree ?? n.degree,
        itemStyle: {
          color: hangdangColor(n.hangdang),
          borderRadius: [0, 6, 6, 0],
        },
      })),
      barMaxWidth: 16,
    }],
  }
}

export function buildCentralityRadar(nodes: NetNode[]): EChartsOption {
  const rows = topNodes(nodes, 5, 'weighted_degree')
  if (!rows.length) {
    return { title: { text: '暂无节点', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const indicators = [
    { name: '度', max: 100 },
    { name: '加权度', max: 100 },
    { name: '介数', max: 100 },
    { name: '接近', max: 100 },
    { name: '特征向量', max: 100 },
  ]
  const series = rows.map((n) => ({
    name: n.name,
    value: norm([
      n.degree,
      n.weighted_degree ?? n.degree,
      n.betweenness ?? 0,
      n.closeness ?? 0,
      n.eigenvector ?? 0,
    ]),
    lineStyle: { width: 2 },
    areaStyle: { opacity: 0.08 },
  }))
  return {
    tooltip: {},
    legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
    radar: {
      indicator: indicators,
      radius: '58%',
      center: ['50%', '48%'],
      splitArea: { areaStyle: { color: ['#fffaf3', '#fff8ee', '#fff3e0'] } },
      axisName: { fontSize: 10 },
    },
    series: [{ type: 'radar', data: series }],
  }
}

export function buildMetricsBar(metrics: PlayNetwork['metrics']): EChartsOption {
  const items = [
    { name: '密度', value: metrics.density * 100 },
    { name: '聚类系数', value: (metrics.avg_clustering ?? 0) * 100 },
    { name: '加权聚类', value: (metrics.avg_weighted_clustering ?? 0) * 100 },
    { name: '模块度', value: Math.max(0, (metrics.modularity ?? 0) * 100) },
    { name: '同配性', value: ((metrics.assortativity_hangdang ?? 0) + 1) * 50 },
  ]
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}' },
    grid: { left: 88, right: 16, top: 12, bottom: 28 },
    xAxis: { type: 'category', data: items.map((i) => i.name), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', max: 100, name: '归一化' },
    series: [{
      type: 'bar',
      data: items.map((i) => ({
        value: +i.value.toFixed(1),
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#c9a227' },
              { offset: 1, color: '#8b2500' },
            ],
          },
          borderRadius: [6, 6, 0, 0],
        },
      })),
      barMaxWidth: 36,
    }],
  }
}

export function buildHangdangNodePie(nodes: NetNode[]): EChartsOption {
  const dist: Record<string, number> = {}
  nodes.forEach((n) => { dist[n.hangdang] = (dist[n.hangdang] ?? 0) + 1 })
  const data = Object.entries(dist).map(([name, value]) => ({
    name,
    value,
    itemStyle: { color: hangdangColor(name) },
  }))
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      center: ['50%', '46%'],
      itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{c}人', fontSize: 10 },
      data,
    }],
  }
}

export function buildRelationTypePie(links: NetLink[]): EChartsOption {
  let both = 0
  let dialogue = 0
  let cooccur = 0
  for (const l of links) {
    const hasD = l.types?.includes('对话')
    const hasS = l.types?.includes('同场')
    if (hasD && hasS) both += 1
    else if (hasD) dialogue += 1
    else if (hasS) cooccur += 1
    else cooccur += 1
  }
  const data = [
    { name: '对话+同场', value: both, itemStyle: { color: '#8b2500' } },
    { name: '仅对话', value: dialogue, itemStyle: { color: '#c9a227' } },
    { name: '仅同场', value: cooccur, itemStyle: { color: '#1565c0' } },
  ].filter((d) => d.value > 0)
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '62%',
      roseType: 'area',
      itemStyle: { borderRadius: 5, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{c}条', fontSize: 10 },
      data,
    }],
  }
}

export function buildWeightHistogram(links: NetLink[]): EChartsOption {
  const edges = [0, 5, 15, 30, 60, Infinity]
  const labels = ['<5', '5–15', '15–30', '30–60', '60+']
  const counts = new Array(labels.length).fill(0)
  for (const l of links) {
    for (let i = 0; i < edges.length - 1; i += 1) {
      if (l.weight >= edges[i] && l.weight < edges[i + 1]) {
        counts[i] += 1
        break
      }
    }
  }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 44, right: 16, top: 20, bottom: 32 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value', name: '边数', minInterval: 1 },
    series: [{
      type: 'bar',
      data: counts,
      itemStyle: { color: '#1565c0', borderRadius: [5, 5, 0, 0] },
    }],
  }
}

export function buildAdjacencyHeatmap(net: PlayNetwork): EChartsOption {
  const nodes = topNodes(net.nodes, 10, 'weighted_degree')
  if (nodes.length < 2) {
    return { title: { text: '节点不足', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const names = nodes.map((n) => n.name)
  const weights = linkWeightMap(net.links)
  const data: [number, number, number][] = []
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = 0; j < nodes.length; j += 1) {
      const k = [nodes[i].id, nodes[j].id].sort().join('|')
      const w = i === j ? 0 : (weights.get(k) ?? 0)
      data.push([j, i, w])
    }
  }
  const max = Math.max(...data.map((d) => d[2]), 1)
  return {
    tooltip: {
      position: 'top',
      formatter: (p: { data: [number, number, number] }) => {
        const [xi, yi, v] = p.data
        return `${names[yi]} ↔ ${names[xi]}<br/>强度 ${v}`
      },
    },
    grid: { left: 72, right: 24, bottom: 72, top: 16 },
    xAxis: { type: 'category', data: names, axisLabel: { rotate: 40, fontSize: 9 } },
    yAxis: { type: 'category', data: names, axisLabel: { fontSize: 9 } },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f7f3ed', '#c9a227', '#8b2500'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: { show: max < 50, fontSize: 8 },
      emphasis: { itemStyle: { shadowBlur: 6 } },
    }],
  }
}

export function buildCentralityScatter(nodes: NetNode[]): EChartsOption {
  const byHd = new Map<string, NetNode[]>()
  nodes.forEach((n) => {
    const list = byHd.get(n.hangdang) ?? []
    list.push(n)
    byHd.set(n.hangdang, list)
  })
  return {
    tooltip: {
      formatter: (p: { data: NetNode & { value: [number, number] } }) => {
        const n = p.data
        return `${n.name}<br/>度 ${n.degree} · 介数 ${(n.betweenness ?? 0).toFixed(3)}`
      },
    },
    legend: { top: 0, textStyle: { fontSize: 10 }, data: [...byHd.keys()] },
    grid: { left: 48, right: 16, top: 36, bottom: 40 },
    xAxis: { name: '度', splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } } },
    yAxis: { name: '介数中心性', splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } } },
    series: [...byHd.entries()].map(([hd, pts]) => ({
      name: hd,
      type: 'scatter',
      itemStyle: { color: hangdangColor(hd), opacity: 0.8 },
      data: pts.map((n) => ({
        ...n,
        value: [n.degree, n.betweenness ?? 0],
        symbolSize: Math.max(8, 6 + (n.weighted_degree ?? n.degree) * 0.12),
      })),
    })),
  }
}

export function buildMainVsSupportPie(nodes: NetNode[]): EChartsOption {
  const main = nodes.filter((n) => n.is_main).length
  const support = nodes.length - main
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['44%', '68%'],
      data: [
        { name: '主要人物', value: main, itemStyle: { color: '#8b2500' } },
        { name: '配角', value: support, itemStyle: { color: '#bdbdbd' } },
      ],
      label: { formatter: '{b}\n{c}人', fontSize: 11 },
      itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
    }],
  }
}

export function buildGenreCompareBar(
  net: PlayNetwork,
  global: NetworkCompareGlobal | null,
): EChartsOption {
  const genre = net.genre
  const group = global?.by_genre?.find((g) => g.group_label === genre)
  if (!group) {
    return { title: { text: '暂无同体裁对比数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const keys = ['density', 'avg_clustering', 'avg_degree'] as const
  const labels = ['密度', '聚类系数', '平均度']
  const cur = net.metrics
  const means = keys.map((k) => group.metrics[k]?.mean ?? 0)
  const curVals = [
    cur.density,
    cur.avg_clustering ?? 0,
    cur.avg_degree ?? 0,
  ]
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [
      { name: '本剧', type: 'bar', data: curVals.map((v) => +v.toFixed(3)), itemStyle: { color: '#8b2500' } },
      { name: `${genre}均值`, type: 'bar', data: means.map((v) => +v.toFixed(3)), itemStyle: { color: '#c9a227' } },
    ],
  }
}
