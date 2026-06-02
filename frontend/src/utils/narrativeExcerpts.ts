import type { PlayCleaned } from '@/types'

const TYPE_LABELS: Record<string, string> = {
  dialogue: '对白',
  aria: '唱段',
  recitation: '念白',
  stage_direction: '舞台',
  action: '动作',
  combat: '武打',
  scene_heading: '场次',
  plot_summary: '梗概',
  annotation: '注释',
  unknown: '其他',
}

const EXCERPT_TYPES = new Set([
  'dialogue',
  'aria',
  'recitation',
  'stage_direction',
  'action',
  'combat',
])

export interface StageExcerpt {
  block_index: number
  type: string
  typeLabel: string
  speaker?: string
  text: string
}

export function buildStageExcerpts(
  play: PlayCleaned,
  range: [number, number],
  limit = 24,
): { items: StageExcerpt[]; total: number } {
  const [lo, hi] = range
  const nameMap = new Map(
    (play.characters ?? []).map((c) => [c.character_id, c.name]),
  )
  const inRange = (play.blocks ?? [])
    .filter((b) => b.block_index >= lo && b.block_index <= hi)
    .filter((b) => EXCERPT_TYPES.has(b.type) && (b.text?.trim()?.length ?? 0) > 0)
    .sort((a, b) => a.block_index - b.block_index)

  const items = inRange.slice(0, limit).map((b) => ({
    block_index: b.block_index,
    type: b.type,
    typeLabel: TYPE_LABELS[b.type] ?? b.type,
    speaker: b.speaker_id
      ? nameMap.get(b.speaker_id) ?? b.speaker_name_raw ?? undefined
      : b.speaker_name_raw ?? undefined,
    text: b.text.trim(),
  }))
  return { items, total: inRange.length }
}
