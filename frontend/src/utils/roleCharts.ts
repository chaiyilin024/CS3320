import type { EChartsOption } from 'echarts'
import type { PlayRole, RoleAnalysisGlobal } from '@/types'
import { coarseColor, hangdangColor } from '@/utils/charts'

type Character = PlayRole['characters'][number]

const CUE_ORDER = ['唱', '念', '做', '打'] as const

function parseFeature(feat: string): { key: string; value: string } | null {
  const i = feat.indexOf('=')
  if (i < 0) return null
  return { key: feat.slice(0, i), value: feat.slice(i + 1) }
}

function lineBucketScore(char: Character): number {
  const bucket = char.top_features?.find((f) => f.startsWith('line_count_bucket='))?.split('=')[1]
  if (bucket === 'high') return 100
  if (bucket === 'mid') return 60
  if (bucket === 'low') return 30
  return 50
}

function cuePresence(char: Character, cue: string): number {
  const fromDerived = char.traits_derived?.performance_cues?.includes(cue) ? 1 : 0
  const fromFeat = char.top_features?.some((f) => f === `cue=${cue}`) ? 1 : 0
  return Math.max(fromDerived, fromFeat) * 100
}

export function buildHangdangPie(dist: Record<string, number>): EChartsOption {
  const data = Object.entries(dist)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({
      name,
      value,
      itemStyle: { color: hangdangColor(name) },
    }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 人 ({d}%)' },
    legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['46%', '72%'],
      center: ['50%', '46%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 8, borderColor: '#fffcf7', borderWidth: 2 },
      label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 },
      data,
    }],
  }
}

export function buildCoarseRose(dist: Record<string, number>): EChartsOption {
  const order = ['生', '旦', '净', '丑', '未知', '其他']
  const data = order
    .filter((k) => (dist[k] ?? 0) > 0)
    .map((name) => ({
      name,
      value: dist[name],
      itemStyle: { color: coarseColor(name) },
    }))
  return {
    tooltip: { trigger: 'item' },
    polar: { radius: [20, '78%'] },
    angleAxis: { type: 'category', data: data.map((d) => d.name), axisLabel: { fontSize: 12 } },
    radiusAxis: { min: 0 },
    series: [{
      type: 'bar',
      coordinateSystem: 'polar',
      data: data.map((d) => ({
        value: d.value,
        itemStyle: d.itemStyle,
      })),
      barCategoryGap: '20%',
    }],
  }
}

export function buildSourcePie(
  labeled: number,
  inferred: number,
  total: number,
): EChartsOption {
  const other = Math.max(0, total - labeled - inferred)
  const data = [
    { name: '戏考标注', value: labeled, itemStyle: { color: '#8b2500' } },
    { name: '规则推断', value: inferred, itemStyle: { color: '#c9a227' } },
    { name: '未确定', value: other, itemStyle: { color: '#bdbdbd' } },
  ].filter((d) => d.value > 0)
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '68%',
      center: ['50%', '50%'],
      roseType: 'radius',
      itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{c}人', fontSize: 11 },
      data,
    }],
  }
}

export function buildConfidenceBar(chars: Character[]): EChartsOption {
  const rows = [...chars].sort((a, b) => b.confidence - a.confidence)
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p: unknown) => {
        const item = (p as { dataIndex: number }[])[0]
        const c = rows[item.dataIndex]
        return `${c.name}<br/>${c.hangdang_final} · 置信度 ${(c.confidence * 100).toFixed(0)}%`
      },
    },
    grid: { left: 72, right: 24, top: 12, bottom: 24 },
    xAxis: { type: 'value', max: 100, name: '置信度%', nameGap: 8 },
    yAxis: {
      type: 'category',
      data: rows.map((c) => c.name),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: rows.map((c) => ({
        value: Math.round(c.confidence * 100),
        itemStyle: {
          color: hangdangColor(c.hangdang_final),
          borderRadius: [0, 6, 6, 0],
        },
      })),
      barMaxWidth: 16,
    }],
  }
}

export function buildCueStacked(chars: Character[]): EChartsOption {
  const hangdangs = [...new Set(chars.map((c) => c.hangdang_final))]
  const cueColors: Record<string, string> = {
    唱: '#8b2500',
    念: '#c9a227',
    做: '#1565c0',
    打: '#2e7d32',
  }
  const series = CUE_ORDER.map((cue) => ({
    name: cue,
    type: 'bar' as const,
    stack: 'cue',
    emphasis: { focus: 'series' as const },
    itemStyle: { color: cueColors[cue] },
    data: hangdangs.map((hd) =>
      chars.filter((c) => c.hangdang_final === hd).filter((c) => cuePresence(c, cue) > 0).length,
    ),
  }))
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: hangdangs, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '人物数', minInterval: 1 },
    series,
  }
}

export function buildIdentityBar(chars: Character[]): EChartsOption {
  const counts = new Map<string, number>()
  for (const c of chars) {
    const id =
      c.traits_derived?.identity
      ?? parseFeature(c.top_features?.find((f) => f.startsWith('identity=')) ?? '')?.value
    if (id) counts.set(id, (counts.get(id) ?? 0) + 1)
  }
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1])
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 72, right: 16, top: 12, bottom: 24 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: rows.map(([k]) => k), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: rows.map(([, v]) => ({
        value: v,
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#c9a227' },
              { offset: 1, color: '#8b2500' },
            ],
          },
          borderRadius: [0, 6, 6, 0],
        },
      })),
      barMaxWidth: 18,
    }],
  }
}

export function buildTraitSankey(
  links: Array<{ trait: string; hangdang: string; count: number }>,
): EChartsOption {
  if (!links.length) {
    return { title: { text: '暂无特征关联数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const top = links.slice(0, 24)
  const nodeNames = new Set<string>()
  top.forEach((l) => {
    nodeNames.add(l.trait)
    nodeNames.add(l.hangdang)
  })
  const nodes = [...nodeNames].map((name) => ({
    name,
    itemStyle: {
      color: hangdangColor(name) !== '#888' ? hangdangColor(name) : '#b8956a',
    },
  }))
  return {
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: [{
      type: 'sankey',
      layout: 'none',
      emphasis: { focus: 'adjacency' },
      nodeAlign: 'left',
      lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.35 },
      label: { fontSize: 10 },
      data: nodes,
      links: top.map((l) => ({
        source: l.trait,
        target: l.hangdang,
        value: l.count,
      })),
    }],
  }
}

export function buildGlobalHeatmap(
  cells: RoleAnalysisGlobal['global_feature_hangdang_matrix'],
): EChartsOption {
  if (!cells?.length) {
    return { title: { text: '暂无全局数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const hangdangs = [...new Set(cells.map((c) => c.hangdang))]
  const features = [...new Set(cells.map((c) => c.feature))]
    .sort((a, b) => {
      const ca = cells.filter((x) => x.feature === a).reduce((s, x) => s + x.count, 0)
      const cb = cells.filter((x) => x.feature === b).reduce((s, x) => s + x.count, 0)
      return cb - ca
    })
    .slice(0, 14)
  const data: [number, number, number][] = []
  cells.forEach((c) => {
    const xi = features.indexOf(c.feature)
    const yi = hangdangs.indexOf(c.hangdang)
    if (xi >= 0 && yi >= 0) data.push([xi, yi, c.count])
  })
  const max = Math.max(...data.map((d) => d[2]), 1)
  return {
    tooltip: {
      position: 'top',
      formatter: (p: { data: [number, number, number] }) => {
        const [xi, yi, v] = p.data
        return `${features[xi]} → ${hangdangs[yi]}<br/>共现 ${v} 次`
      },
    },
    grid: { left: 88, right: 24, bottom: 72, top: 16 },
    xAxis: {
      type: 'category',
      data: features,
      axisLabel: { rotate: 40, fontSize: 9, interval: 0 },
    },
    yAxis: { type: 'category', data: hangdangs, axisLabel: { fontSize: 11 } },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#fff8ee', '#c9a227', '#8b2500'] },
    },
    series: [{
      type: 'heatmap',
      data,
      label: { show: max <= 30, fontSize: 9 },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.2)' } },
    }],
  }
}

export function buildCharacterRadar(char: Character | null): EChartsOption {
  if (!char) {
    return { title: { text: '点击人物表查看多维画像', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const indicators = [
    { name: '唱', max: 100 },
    { name: '念', max: 100 },
    { name: '做', max: 100 },
    { name: '打', max: 100 },
    { name: '台词量', max: 100 },
    { name: '置信度', max: 100 },
  ]
  const values = [
    cuePresence(char, '唱'),
    cuePresence(char, '念'),
    cuePresence(char, '做'),
    cuePresence(char, '打'),
    lineBucketScore(char),
    Math.round(char.confidence * 100),
  ]
  return {
    tooltip: {},
    radar: {
      indicator: indicators,
      radius: '62%',
      splitArea: { areaStyle: { color: ['#fffaf3', '#fff8ee', '#fff3e0', '#ffecb3'] } },
      axisName: { color: '#6d5c52', fontSize: 11 },
    },
    series: [{
      type: 'radar',
      data: [{
        name: char.name,
        value: values,
        areaStyle: { color: 'rgba(139, 37, 0, 0.25)' },
        lineStyle: { color: hangdangColor(char.hangdang_final), width: 2 },
        itemStyle: { color: hangdangColor(char.hangdang_final) },
      }],
    }],
  }
}

export function buildPersonalityBar(chars: Character[]): EChartsOption {
  const counts = new Map<string, number>()
  for (const c of chars) {
    const list = c.traits_derived?.personality ?? []
    for (const p of list) counts.set(p, (counts.get(p) ?? 0) + 1)
    for (const f of c.top_features ?? []) {
      const parsed = parseFeature(f)
      if (parsed?.key === 'personality') counts.set(parsed.value, (counts.get(parsed.value) ?? 0) + 1)
    }
  }
  const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10)
  if (!rows.length) {
    return { title: { text: '暂无性格标签', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 56, right: 16, top: 12, bottom: 48 },
    xAxis: {
      type: 'category',
      data: rows.map(([k]) => k),
      axisLabel: { rotate: 30, fontSize: 10 },
    },
    yAxis: { type: 'value', minInterval: 1, name: '出现次数' },
    series: [{
      type: 'bar',
      data: rows.map(([, v]) => v),
      itemStyle: {
        color: '#d4537a',
        borderRadius: [6, 6, 0, 0],
      },
    }],
  }
}
