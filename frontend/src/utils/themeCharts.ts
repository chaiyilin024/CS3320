import type { EChartsOption } from 'echarts'
import type { PlayThemes, ThemePatternsGlobal } from '@/types'
import { asChartOption } from './chartOption'

const TOPIC_PALETTE = [
  '#8b2500', '#c9a227', '#1565c0', '#2e7d32', '#6a1b9a', '#d4537a', '#bf360c', '#00838f',
]

export function topicColor(topicId: number): string {
  return TOPIC_PALETTE[topicId % TOPIC_PALETTE.length]
}

function topicData(topics: PlayThemes['topics']) {
  return [...topics]
    .sort((a, b) => b.weight - a.weight)
    .map((t) => ({
      name: t.label,
      value: +(t.weight * 100).toFixed(1),
      topic_id: t.topic_id,
      itemStyle: { color: topicColor(t.topic_id) },
    }))
}

export function buildTopicRose(topics: PlayThemes['topics']): EChartsOption {
  const data = topicData(topics)
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>占比 {c}% ({d}%)' },
    legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
    series: [{
      type: 'pie',
      radius: [24, '68%'],
      center: ['50%', '46%'],
      roseType: 'area',
      itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{c}%', fontSize: 10 },
      data,
    }],
  }
}

export function buildTopicWeightBar(topics: PlayThemes['topics']): EChartsOption {
  const rows = [...topics].sort((a, b) => a.weight - b.weight)
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    grid: { left: 100, right: 24, top: 12, bottom: 24 },
    xAxis: { type: 'value', max: 100, name: '占比%' },
    yAxis: {
      type: 'category',
      data: rows.map((t) => `T${t.topic_id} ${t.label}`),
      axisLabel: { fontSize: 10, width: 90, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: rows.map((t) => ({
        value: +(t.weight * 100).toFixed(1),
        itemStyle: { color: topicColor(t.topic_id), borderRadius: [0, 6, 6, 0] },
      })),
      barMaxWidth: 18,
    }],
  }
}

export function buildKeywordBar(
  topic: PlayThemes['topics'][number] | null,
): EChartsOption {
  if (!topic) {
    return { title: { text: '点击主题卡片查看关键词', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const kws = topic.keywords.slice(0, 12)
  const weights = topic.keyword_weights?.slice(0, 12)
    ?? kws.map((_, i) => kws.length - i)
  const rows = kws.map((k, i) => ({ k, w: weights[i] ?? 1 })).sort((a, b) => b.w - a.w)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 72, right: 16, top: 12, bottom: 24 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: rows.map((r) => r.k), axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: rows.map((r) => ({
        value: +r.w.toFixed(3),
        itemStyle: { color: topicColor(topic.topic_id), borderRadius: [0, 5, 5, 0] },
      })),
      barMaxWidth: 14,
    }],
  }
}

export function buildKeywordHeatmap(topics: PlayThemes['topics']): EChartsOption {
  const ranks = ['1', '2', '3', '4', '5', '6', '7', '8']
  const rows = [...topics].sort((a, b) => b.weight - a.weight)
  const data: [number, number, number][] = []
  rows.forEach((t, yi) => {
    t.keywords.slice(0, 8).forEach((_, xi) => {
      const w = t.keyword_weights?.[xi] ?? (8 - xi)
      data.push([xi, yi, +w.toFixed(3)])
    })
  })
  const max = Math.max(...data.map((d) => d[2]), 1)
  return asChartOption({
    tooltip: {
      position: 'top',
      formatter: (p: unknown) => {
        const row = p as { data?: [number, number, number] }
        const [xi, yi, v] = row.data ?? [0, 0, 0]
        return `${rows[yi].label}<br/>${rows[yi].keywords[xi]} (${v})`
      },
    },
    grid: { left: 100, right: 24, bottom: 48, top: 16 },
    xAxis: { type: 'category', data: ranks.map((r) => `关键词${r}`), axisLabel: { fontSize: 9 } },
    yAxis: {
      type: 'category',
      data: rows.map((t) => t.label),
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
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: true,
        formatter: (p: unknown) => {
          const row = p as { data?: [number, number, number] }
          const data = row.data
          if (!data) return ''
          return rows[data[1]]?.keywords[data[0]] ?? ''
        },
        fontSize: 8,
      },
    }],
  })
}

export function buildTopicTimeline(
  topics: PlayThemes['topics'],
  blocks: PlayThemes['representative_blocks'],
): EChartsOption {
  if (!blocks?.length) {
    return { title: { text: '暂无代表片段位置数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const labelMap = new Map(topics.map((t) => [t.topic_id, t.label]))
  const byTopic = new Map<number, typeof blocks>()
  blocks.forEach((b) => {
    const list = byTopic.get(b.topic_id) ?? []
    list.push(b)
    byTopic.set(b.topic_id, list)
  })
  return asChartOption({
    tooltip: {
      formatter: (p: unknown) => {
        const row = p as { data?: { block_index: number; snippet: string; speaker?: string } }
        const data = row.data
        if (!data) return ''
        return `块 #${data.block_index}<br/>${data.speaker ?? ''}<br/>${data.snippet}`
      },
    },
    legend: { top: 0, textStyle: { fontSize: 10 }, data: [...byTopic.keys()].map((id) => labelMap.get(id) ?? `T${id}`) },
    grid: { left: 48, right: 16, top: 40, bottom: 40 },
    xAxis: { name: '正文块序号', splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } } },
    yAxis: { show: false, min: -1, max: 1 },
    series: [...byTopic.entries()].map(([tid, pts]) => ({
      name: labelMap.get(tid) ?? `T${tid}`,
      type: 'scatter',
      symbolSize: (val: number[]) => Math.max(10, (val[2] ?? 0.5) * 22),
      itemStyle: { color: topicColor(tid), opacity: 0.85 },
      data: pts
        .filter((b) => b.block_index != null)
        .map((b) => ({
          value: [b.block_index, 0, b.score ?? 0.5],
          block_index: b.block_index,
          snippet: b.text_snippet,
          speaker: b.speaker_name,
        })),
    })),
  })
}

export function buildSpeakerTopicBar(
  blocks: PlayThemes['representative_blocks'],
  topics: PlayThemes['topics'],
): EChartsOption {
  if (!blocks?.length) {
    return { title: { text: '暂无说话人数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const labelMap = new Map(topics.map((t) => [t.topic_id, t.label]))
  const counts = new Map<string, number>()
  blocks.forEach((b) => {
    const sp = b.speaker_name ?? '未知'
    const key = `${sp}|${b.topic_id}`
    counts.set(key, (counts.get(key) ?? 0) + 1)
  })
  const speakers = [...new Set(blocks.map((b) => b.speaker_name ?? '未知'))]
  const topicIds = [...new Set(blocks.map((b) => b.topic_id))]
  const series = topicIds.map((tid) => ({
    name: labelMap.get(tid) ?? `T${tid}`,
    type: 'bar' as const,
    stack: 'sp',
    itemStyle: { color: topicColor(tid) },
    data: speakers.map((sp) => {
      const k = `${sp}|${tid}`
      return counts.get(k) ?? 0
    }),
  }))
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 56, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: speakers, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '片段数', minInterval: 1 },
    series,
  }
}

export function buildSnippetScoreBar(
  blocks: PlayThemes['representative_blocks'],
  topics: PlayThemes['topics'],
): EChartsOption {
  if (!blocks?.length) {
    return { title: { text: '暂无代表片段', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const rows = [...blocks]
    .filter((b) => b.score != null)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, 12)
  const labelMap = new Map(topics.map((t) => [t.topic_id, t.label]))
  return {
    tooltip: {
      formatter: (p: unknown) => {
        const i = (p as { dataIndex: number }).dataIndex
        const b = rows[i]
        return `${b.speaker_name ?? ''} · ${labelMap.get(b.topic_id)}<br/>${b.text_snippet}`
      },
    },
    grid: { left: 48, right: 16, top: 12, bottom: 64 },
    xAxis: {
      type: 'category',
      data: rows.map((b) => `#${b.block_index ?? '?'}`),
      axisLabel: { rotate: 30, fontSize: 9 },
    },
    yAxis: { type: 'value', name: '主题得分', max: 1 },
    series: [{
      type: 'bar',
      data: rows.map((b) => ({
        value: +(b.score ?? 0).toFixed(3),
        itemStyle: { color: topicColor(b.topic_id), borderRadius: [5, 5, 0, 0] },
      })),
      barMaxWidth: 28,
    }],
  }
}

export function resolveGlobalHeatmapRows(
  patterns: ThemePatternsGlobal | null,
  highlightScriptId?: string | null,
  maxRows = 48,
): ThemePatternsGlobal['play_topic_matrix'] {
  if (!patterns?.play_topic_matrix.length) return []
  let rows = [...patterns.play_topic_matrix]
  if (rows.length <= maxRows) return rows
  const hi = highlightScriptId
    ? rows.find((r) => r.script_id === highlightScriptId)
    : null
  const scored = rows.map((r) => ({
    row: r,
    score: r.weights.reduce((s, w) => s + w * w, 0),
  }))
  scored.sort((a, b) => b.score - a.score)
  const picked = scored.slice(0, maxRows - (hi ? 1 : 0)).map((x) => x.row)
  if (hi && !picked.some((r) => r.script_id === hi.script_id)) {
    picked.pop()
    picked.unshift(hi)
  }
  return picked
}

export function buildGlobalPlayHeatmap(
  patterns: ThemePatternsGlobal | null,
  highlightScriptId?: string | null,
  maxRows = 48,
): EChartsOption {
  if (!patterns?.play_topic_matrix.length) {
    return { title: { text: '暂无跨剧数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const labels = patterns.topic_labels.map((l) => l.label)
  const rows = resolveGlobalHeatmapRows(patterns, highlightScriptId, maxRows)
  const vals = rows.flatMap((r) => r.weights)
  const max = Math.max(...vals, 0.01)
  return asChartOption({
    tooltip: {
      position: 'top',
      formatter: (p: unknown) => {
        const row = p as { data?: [number, number, number] }
        const [xi, yi, v] = row.data ?? [0, 0, 0]
        return `${rows[yi].title ?? rows[yi].script_id}<br/>${labels[xi]}: ${(v * 100).toFixed(1)}%`
      },
    },
    grid: { left: 100, right: 24, bottom: 72, top: 16 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 35, fontSize: 9 } },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.title ?? r.script_id),
      axisLabel: { fontSize: 9 },
    },
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
      data: rows.flatMap((row, yi) =>
        row.weights.map((w, xi) => [xi, yi, w] as [number, number, number]),
      ),
      emphasis: { itemStyle: { shadowBlur: 6 } },
    }],
  })
}

export function buildCooccurrenceHeatmap(patterns: ThemePatternsGlobal | null): EChartsOption {
  const co = patterns?.topic_cooccurrence ?? []
  if (!co.length) {
    return { title: { text: '暂无主题共现数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const ids = [...new Set(co.flatMap((c) => [c.topic_a, c.topic_b]))].sort((a, b) => a - b)
  const labelMap = new Map(patterns?.topic_labels.map((l) => [l.topic_id, l.label]))
  const data: [number, number, number][] = []
  const mat = new Map<string, number>()
  co.forEach((c) => {
    mat.set(`${c.topic_a}|${c.topic_b}`, c.count)
    mat.set(`${c.topic_b}|${c.topic_a}`, c.count)
  })
  ids.forEach((a, i) => {
    ids.forEach((b, j) => {
      data.push([j, i, mat.get(`${a}|${b}`) ?? (a === b ? 0 : 0)])
    })
  })
  const max = Math.max(...data.map((d) => d[2]), 1)
  return asChartOption({
    tooltip: {
      formatter: (p: unknown) => {
        const row = p as { data?: [number, number, number] }
        const [xi, yi, v] = row.data ?? [0, 0, 0]
        if (!v) return ''
        return `${labelMap.get(ids[yi])} ↔ ${labelMap.get(ids[xi])}<br/>共现 ${v}`
      },
    },
    grid: { left: 88, right: 16, bottom: 56, top: 16 },
    xAxis: {
      type: 'category',
      data: ids.map((id) => labelMap.get(id) ?? `T${id}`),
      axisLabel: { rotate: 35, fontSize: 9 },
    },
    yAxis: {
      type: 'category',
      data: ids.map((id) => labelMap.get(id) ?? `T${id}`),
      axisLabel: { fontSize: 9 },
    },
    visualMap: {
      min: 0,
      max,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f7f3ed', '#6a1b9a', '#3e0069'] },
    },
    series: [{ type: 'heatmap', data: data.filter((d) => d[2] > 0), label: { show: true, fontSize: 9 } }],
  })
}

export function buildPlayVsGlobalRadar(
  themes: PlayThemes,
  patterns: ThemePatternsGlobal | null,
): EChartsOption {
  if (!patterns?.play_topic_matrix.length) {
    return { title: { text: '暂无全库对比', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const k = patterns.topic_labels.length
  const means = new Array(k).fill(0)
  patterns.play_topic_matrix.forEach((row) => {
    row.weights.forEach((w, i) => { means[i] += w })
  })
  const n = patterns.play_topic_matrix.length
  means.forEach((_, i) => { means[i] /= n })

  const playRow = patterns.play_topic_matrix.find((r) => r.script_id === themes.script_id)
  const playWeights = playRow?.weights ?? themes.topic_composition

  const indicators = patterns.topic_labels.map((l) => ({
    name: l.label.length > 6 ? `${l.label.slice(0, 6)}…` : l.label,
    max: Math.max(...means, ...playWeights, 0.01) * 1.1,
  }))

  return {
    tooltip: {},
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    radar: {
      indicator: indicators,
      radius: '58%',
      center: ['50%', '46%'],
      splitArea: { areaStyle: { color: ['#fffaf3', '#fff8ee'] } },
      axisName: { fontSize: 9 },
    },
    series: [{
      type: 'radar',
      data: [
        {
          name: '本剧',
          value: playWeights.map((v) => +v.toFixed(4)),
          areaStyle: { color: 'rgba(139, 37, 0, 0.2)' },
          lineStyle: { color: '#8b2500' },
        },
        {
          name: '全库均值',
          value: means.map((v) => +v.toFixed(4)),
          areaStyle: { color: 'rgba(201, 162, 39, 0.15)' },
          lineStyle: { color: '#c9a227' },
        },
      ],
    }],
  }
}

export function buildTopicSankey(topics: PlayThemes['topics']): EChartsOption {
  const nodes: { name: string }[] = []
  const links: { source: string; target: string; value: number }[] = []
  const nodeSet = new Set<string>()
  topics.forEach((t) => {
    const topicName = `T${t.topic_id}:${t.label}`
    nodeSet.add(topicName)
    t.keywords.slice(0, 5).forEach((kw) => {
      nodeSet.add(kw)
      links.push({ source: kw, target: topicName, value: +(t.weight * 10 + 0.1).toFixed(2) })
    })
  })
  nodeSet.forEach((n) => nodes.push({ name: n }))
  return asChartOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'sankey',
      emphasis: { focus: 'adjacency' },
      nodeAlign: 'left',
      lineStyle: { color: 'gradient', curveness: 0.5, opacity: 0.35 },
      label: { fontSize: 9 },
      data: nodes,
      links,
    }],
  })
}

export function matchPlaysForPattern(
  patterns: ThemePatternsGlobal | null,
  labels: string[],
  minWeight = 0.08,
): Array<{ script_id: string; title?: string }> {
  if (!patterns?.play_topic_matrix.length || !labels.length) return []
  const labelToIdx = new Map(patterns.topic_labels.map((l) => [l.label, l.topic_id]))
  const idxs = labels.map((lb) => labelToIdx.get(lb)).filter((i): i is number => i != null)
  if (!idxs.length) return []
  return patterns.play_topic_matrix
    .filter((row) => idxs.every((i) => (row.weights[i] ?? 0) >= minWeight))
    .map((row) => ({ script_id: row.script_id, title: row.title }))
    .slice(0, 24)
}

export function buildCommonPatternsBar(patterns: ThemePatternsGlobal | null): EChartsOption {
  const rows = [...(patterns?.common_patterns ?? [])].sort((a, b) => b.support - a.support).slice(0, 12)
  if (!rows.length) {
    return { title: { text: '暂无主题组合模式', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p: unknown) => {
        const item = (p as { dataIndex: number }[])[0]
        const r = rows[item.dataIndex]
        return [
          r.labels.join(' + '),
          `支持度 ${(r.support * 100).toFixed(1)}%`,
          `剧本数 ${r.play_count}`,
        ].join('<br/>')
      },
    },
    grid: { left: 140, right: 24, top: 12, bottom: 24 },
    xAxis: { type: 'value', name: '支持度', max: 1 },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.labels.join(' · ')),
      axisLabel: { fontSize: 9, width: 130, overflow: 'truncate' },
    },
    series: [{
      type: 'bar',
      data: rows.map((r) => ({
        value: +r.support.toFixed(3),
        itemStyle: { color: '#6a1b9a', borderRadius: [0, 6, 6, 0] },
      })),
      barMaxWidth: 16,
    }],
  }
}
