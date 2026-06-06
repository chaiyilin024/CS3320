import type { EChartsOption } from 'echarts'
import type { NarrativeTemplatesGlobal, PlayNarrative } from '@/types'
import { topicColor } from '@/utils/themeCharts'
import { asChartOption } from './chartOption'

export const STAGE_COLORS: Record<string, string> = {
  铺垫: '#c9a227',
  发展: '#1565c0',
  冲突: '#8b2500',
  高潮: '#bf360c',
  结局: '#2e7d32',
  其他: '#9e9e9e',
}

export function stageColor(stage: string): string {
  return STAGE_COLORS[stage] ?? '#888'
}

function stageColorRgba(stage: string, alpha: number): string {
  const hex = stageColor(stage).replace('#', '')
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function stageLengths(plotStages: PlayNarrative['plot_stages']) {
  return plotStages.map((st) => {
    const len = Math.max(0, st.block_range[1] - st.block_range[0] + 1)
    return { stage: st.stage, label: st.label, length: len }
  })
}

function avgInRange(
  series: PlayNarrative['rhythm_series'],
  range: [number, number] | null,
  key: keyof PlayNarrative['rhythm_series'][number],
): number {
  const pts = range
    ? series.filter((p) => p.block_index >= range[0] && p.block_index <= range[1])
    : series
  if (!pts.length) return 0
  const sum = pts.reduce((s, p) => s + (Number(p[key]) || 0), 0)
  return sum / pts.length
}

export function buildRhythmLine(
  narrative: PlayNarrative,
  selectedRange: [number, number] | null,
  selectedStage: string | null,
  selectedTopicIds: number[] = [],
  enableBrush = true,
): EChartsOption {
  const s = narrative.rhythm_series ?? []
  if (!s.length) {
    return asChartOption({ title: { text: '暂无节奏数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } })
  }
  const markArea = selectedRange
    ? {
        silent: true,
        itemStyle: {
          color: stageColorRgba(selectedStage ?? '', 0.2),
          borderWidth: 1,
          borderColor: stageColor(selectedStage ?? ''),
        },
        label: {
          show: !!selectedStage,
          position: 'insideTop' as const,
          formatter: selectedStage ?? '',
          color: stageColor(selectedStage ?? ''),
          fontSize: 11,
        },
        data: [[
          { coord: [selectedRange[0], 0] },
          { coord: [selectedRange[1], 1] },
        ]],
      }
    : undefined

  const series = [
    { name: '对白密度', key: 'dialogue_density' as const, color: '#8b2500' },
    { name: '唱段占比', key: 'aria_ratio' as const, color: '#c9a227' },
    { name: '动作强度', key: 'action_intensity' as const, color: '#1565c0' },
    { name: '情感', key: 'emotion_score' as const, color: '#d4537a' },
    { name: '张力', key: 'tension_score' as const, color: '#6a1b9a' },
  ]

  const topicMarks = (narrative.block_annotations ?? [])
    .filter((a) => selectedTopicIds.length === 0 || selectedTopicIds.includes(a.dominant_topic_id ?? -1))
    .filter((a) => a.dominant_topic_id != null)
    .map((a) => ({
      coord: [a.block_index, 0] as [number, number],
      symbol: 'pin',
      symbolSize: 28,
      itemStyle: { color: topicColor(a.dominant_topic_id!) },
      label: { show: false },
    }))

  return asChartOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const items = params as Array<{ seriesName: string; data: [number, number]; axisValue: number }>
        if (!items.length) return ''
        const block = items[0].data?.[0] ?? items[0].axisValue
        const lines = [`块 #${block}`]
        items.forEach((it) => {
          const v = Array.isArray(it.data) ? it.data[1] : it.data
          lines.push(`${it.seriesName}: ${Number(v).toFixed(3)}`)
        })
        return lines.join('<br/>')
      },
    },
    legend: { data: series.map((x) => x.name), bottom: enableBrush ? 36 : 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 20, top: 28, bottom: enableBrush ? 88 : 52 },
    xAxis: { type: 'value', name: '正文块序号', splitLine: { show: false } },
    yAxis: { type: 'value', max: 1, splitLine: { lineStyle: { type: 'dashed', opacity: 0.35 } } },
    dataZoom: enableBrush
      ? [
          { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
          { type: 'slider', xAxisIndex: 0, height: 22, bottom: 8, filterMode: 'none' },
        ]
      : undefined,
    series: [
      ...series.map((cfg, i) => ({
        name: cfg.name,
        type: 'line' as const,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: i === 0 ? 2.5 : 1.5, color: cfg.color },
        itemStyle: { color: cfg.color },
        data: s.map((p) => [p.block_index, p[cfg.key] ?? 0]),
        markArea: i === 0 ? markArea : undefined,
      })),
      ...(selectedTopicIds.length && topicMarks.length
        ? [{
            name: '主题标记',
            type: 'scatter' as const,
            symbol: 'pin',
            symbolSize: 22,
            data: topicMarks.map((m) => {
              const ann = narrative.block_annotations?.find((a) => a.block_index === m.coord[0])
              return [m.coord[0], ann?.emotion_score ?? 0.5]
            }),
            itemStyle: { color: '#6a1b9a' },
          }]
        : []),
    ],
  })
}

export function buildStageProportionPie(plotStages: PlayNarrative['plot_stages']): EChartsOption {
  const rows = stageLengths(plotStages)
  return {
    tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 块 ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '46%'],
      itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{d}%', fontSize: 10 },
      data: rows.map((r) => ({
        name: r.stage,
        value: r.length,
        itemStyle: { color: stageColor(r.stage) },
      })),
    }],
  }
}

export function buildPerformanceStacked(
  byStage: PlayNarrative['performance_by_stage'],
): EChartsOption {
  const rows = byStage ?? []
  const cues = ['唱', '念', '做', '打']
  const cueColors: Record<string, string> = {
    唱: '#8b2500', 念: '#c9a227', 做: '#1565c0', 打: '#2e7d32',
  }
  if (!rows.length) {
    return { title: { text: '暂无分阶段表演数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: rows.map((r) => r.stage), axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '标记次数', minInterval: 1 },
    series: cues.map((cue) => ({
      name: cue,
      type: 'bar',
      stack: 'perf',
      itemStyle: { color: cueColors[cue] },
      data: rows.map((r) => r.distribution[cue] ?? 0),
    })),
  }
}

export function buildStageRadar(
  narrative: PlayNarrative,
  selectedStage: string | null,
): EChartsOption {
  const stages = narrative.plot_stages ?? []
  if (!stages.length) {
    return { title: { text: '暂无阶段数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const indicators = [
    { name: '对白密度', max: 1 },
    { name: '唱段占比', max: 1 },
    { name: '动作强度', max: 1 },
    { name: '情感', max: 1 },
    { name: '张力', max: 1 },
  ]
  const series = stages.map((st) => ({
    name: st.stage,
    value: [
      avgInRange(narrative.rhythm_series, st.block_range, 'dialogue_density'),
      avgInRange(narrative.rhythm_series, st.block_range, 'aria_ratio'),
      avgInRange(narrative.rhythm_series, st.block_range, 'action_intensity'),
      avgInRange(narrative.rhythm_series, st.block_range, 'emotion_score'),
      avgInRange(narrative.rhythm_series, st.block_range, 'tension_score'),
    ].map((v) => +v.toFixed(3)),
    lineStyle: {
      width: selectedStage === st.stage ? 3 : 1,
      color: stageColor(st.stage),
    },
    areaStyle: { opacity: selectedStage === st.stage ? 0.2 : 0.05 },
    itemStyle: { color: stageColor(st.stage) },
  }))
  return {
    tooltip: {},
    legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
    radar: {
      indicator: indicators,
      radius: '58%',
      center: ['50%', '48%'],
      splitArea: { areaStyle: { color: ['#fffaf3', '#fff8ee'] } },
      axisName: { fontSize: 10 },
    },
    series: [{ type: 'radar', data: series }],
  }
}

export function buildEmotionTimeline(
  annotations: PlayNarrative['block_annotations'],
  selectedRange: [number, number] | null,
): EChartsOption {
  const rows = (annotations ?? []).filter((a) => a.emotion_score != null)
  if (!rows.length) {
    return { title: { text: '暂无块级情感标注', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const markArea = selectedRange
    ? {
        silent: true,
        itemStyle: { color: 'rgba(201, 162, 39, 0.18)' },
        data: [[
          { coord: [selectedRange[0], 0] },
          { coord: [selectedRange[1], 1] },
        ]],
      }
    : undefined
  return asChartOption({
    tooltip: {
      formatter: (p: unknown) => {
        const row = p as { data?: [number, number, string] }
        const data = row.data
        if (!data) return ''
        const [x, y, stage] = data
        return `块 #${x}<br/>${stage}<br/>情感 ${y.toFixed(3)}`
      },
    },
    grid: { left: 48, right: 16, top: 16, bottom: 40 },
    xAxis: { type: 'value', name: '正文块' },
    yAxis: { type: 'value', name: '情感得分', max: 1 },
    visualMap: {
      min: 0,
      max: 1,
      dimension: 1,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#e3f2fd', '#d4537a', '#8b2500'] },
      show: false,
    },
    series: [{
      type: 'scatter',
      symbolSize: 7,
      data: rows.map((a) => [a.block_index, a.emotion_score ?? 0, a.stage ?? '']),
      markArea,
    }],
  })
}

export function buildGlobalStageCompare(
  narrative: PlayNarrative,
  global: NarrativeTemplatesGlobal | null,
): EChartsOption {
  const cur = stageLengths(narrative.plot_stages)
  const total = cur.reduce((s, r) => s + r.length, 0) || 1
  const curProps = Object.fromEntries(
    cur.map((r) => [r.stage, +(r.length / total).toFixed(4)]),
  )
  const classic = global?.templates.find((t) => t.template_id === 'classic_five_act')
  const globalProps = classic?.stage_proportions ?? {}
  const stages = [...new Set([...Object.keys(curProps), ...Object.keys(globalProps)])]
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: stages, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '阶段占比', max: 1 },
    series: [
      {
        name: '本剧',
        type: 'bar',
        data: stages.map((st) => curProps[st] ?? 0),
        itemStyle: { color: '#8b2500', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '全库均值（起承转合型）',
        type: 'bar',
        data: stages.map((st) => globalProps[st] ?? 0),
        itemStyle: { color: '#c9a227', borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
}

export function buildPerformancePie(dist: Record<string, number>): EChartsOption {
  const order = ['唱', '念', '做', '打', 'unknown']
  const labels: Record<string, string> = { unknown: '其他' }
  const colors: Record<string, string> = {
    唱: '#8b2500', 念: '#c9a227', 做: '#1565c0', 打: '#2e7d32', unknown: '#bdbdbd',
  }
  const data = order
    .filter((k) => (dist[k] ?? 0) > 0)
    .map((k) => ({
      name: labels[k] ?? k,
      value: dist[k],
      itemStyle: { color: colors[k] ?? '#888' },
    }))
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '62%',
      roseType: 'radius',
      itemStyle: { borderRadius: 5, borderColor: '#fffcf7', borderWidth: 2 },
      label: { formatter: '{b}\n{c}', fontSize: 10 },
      data,
    }],
  }
}

export function rangesEqual(a: [number, number] | null, b: [number, number]): boolean {
  return !!a && a[0] === b[0] && a[1] === b[1]
}

export function buildBlockStrip(
  narrative: PlayNarrative,
  selectedRange: [number, number] | null,
): EChartsOption {
  const rows = narrative.block_annotations ?? []
  if (!rows.length) {
    return { title: { text: '暂无块级条带数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const markArea = selectedRange
    ? {
        silent: true,
        itemStyle: { color: 'rgba(201, 162, 39, 0.15)' },
        data: [[{ xAxis: selectedRange[0] }, { xAxis: selectedRange[1] }]],
      }
    : undefined
  return asChartOption({
    tooltip: {
      formatter: (p: unknown) => {
        const d = (p as { data?: [number, number, string] }).data
        if (!d) return ''
        return `块 #${d[0]}<br/>阶段 ${d[2]}`
      },
    },
    grid: { left: 48, right: 16, top: 8, bottom: 28 },
    xAxis: { type: 'value', name: '正文块', min: 'dataMin', max: 'dataMax' },
    yAxis: { type: 'category', data: ['阶段'], show: false },
    series: [{
      type: 'scatter',
      symbolSize: 6,
      data: rows.map((a) => [a.block_index, 0, a.stage ?? '']),
      itemStyle: {
        color: (p: unknown) => stageColor((p as { data?: [number, number, string] }).data?.[2] ?? ''),
      },
      markArea,
    }],
  })
}

export function buildTemplateStageCompare(
  narrative: PlayNarrative,
  global: NarrativeTemplatesGlobal | null,
  templateId: string,
): EChartsOption {
  const tpl = global?.templates.find((t) => t.template_id === templateId)
  if (!tpl?.stage_proportions) {
    return { title: { text: '暂无模板数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const cur = stageLengths(narrative.plot_stages)
  const total = cur.reduce((s, r) => s + r.length, 0) || 1
  const curProps = Object.fromEntries(cur.map((r) => [r.stage, +(r.length / total).toFixed(4)]))
  const stages = [...new Set([...Object.keys(curProps), ...Object.keys(tpl.stage_proportions)])]
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: stages, axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', name: '阶段占比', max: 1 },
    series: [
      { name: '本剧', type: 'bar', data: stages.map((st) => curProps[st] ?? 0), itemStyle: { color: '#8b2500' } },
      { name: tpl.label, type: 'bar', data: stages.map((st) => tpl.stage_proportions?.[st] ?? 0), itemStyle: { color: '#c9a227' } },
    ],
  }
}

export function buildGenreRhythmOverlay(
  narrative: PlayNarrative,
  global: NarrativeTemplatesGlobal | null,
  genre: string | null | undefined,
): EChartsOption {
  const cur = narrative.rhythm_series ?? []
  const gRow = global?.by_genre?.find((g) => g.genre === genre)
  const ref = gRow?.avg_rhythm_curve ?? []
  if (!cur.length) {
    return { title: { text: '暂无节奏数据', left: 'center', top: 'middle', textStyle: { color: '#999', fontSize: 13 } } }
  }
  const metric = 'tension_score' as const
  return asChartOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { fontSize: 10 } },
    grid: { left: 48, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'value', name: '叙事进度%' },
    yAxis: { type: 'value', max: 1, name: '张力' },
    series: [
      {
        name: '本剧',
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#8b2500', width: 2.5 },
        data: cur.map((p, idx) => [idx / Math.max(cur.length - 1, 1) * 100, p[metric] ?? 0]),
      },
      {
        name: `${genre ?? '同体裁'}均值`,
        type: 'line',
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#c9a227', width: 2, type: 'dashed' },
        data: ref.map((p, idx) => [idx / Math.max(ref.length - 1, 1) * 100, p[metric] ?? 0]),
      },
    ],
  })
}
