import type { CatalogPlay } from '@/types'

export interface DashboardKpis {
  plays: number
  characters: number
  blocks: number
  scenes: number
  collections: number
  avgParseQuality: number
}

export interface CountItem {
  name: string
  value: number
}

export interface ScatterPoint {
  script_id: string
  title: string
  collection_name: string
  genre: string
  block_count: number
  character_count: number
  scene_count: number
  parse_quality: number
}

export interface BinItem {
  label: string
  value: number
}

export interface DashboardStats {
  kpis: DashboardKpis
  genres: CountItem[]
  collections: CountItem[]
  eras: CountItem[]
  blockBins: BinItem[]
  qualityBins: BinItem[]
  scatter: ScatterPoint[]
}

function topWithOther(items: CountItem[], limit: number): CountItem[] {
  const sorted = [...items].sort((a, b) => b.value - a.value)
  if (sorted.length <= limit) return sorted
  const head = sorted.slice(0, limit)
  const rest = sorted.slice(limit).reduce((s, x) => s + x.value, 0)
  if (rest > 0) head.push({ name: '其他', value: rest })
  return head
}

function binNumeric(values: number[], edges: number[], labels: string[]): BinItem[] {
  const counts = new Array(edges.length - 1).fill(0)
  for (const v of values) {
    for (let i = 0; i < edges.length - 1; i += 1) {
      const inLast = i === edges.length - 2
      if (v >= edges[i] && (inLast ? v <= edges[i + 1] : v < edges[i + 1])) {
        counts[i] += 1
        break
      }
    }
  }
  return labels.map((label, i) => ({ label, value: counts[i] }))
}

export function aggregateCatalog(plays: CatalogPlay[]): DashboardStats {
  const genreMap = new Map<string, number>()
  const collectionMap = new Map<string, number>()
  const eraMap = new Map<string, number>()

  let characters = 0
  let blocks = 0
  let scenes = 0
  let qualitySum = 0
  let qualityCount = 0
  const blockValues: number[] = []
  const qualityValues: number[] = []

  const scatter: ScatterPoint[] = plays.map((p) => {
    const genre = p.tags?.genre_inferred ?? '未知'
    const era = p.tags?.era_inferred ?? '未知'
    genreMap.set(genre, (genreMap.get(genre) ?? 0) + 1)
    collectionMap.set(p.collection_name, (collectionMap.get(p.collection_name) ?? 0) + 1)
    eraMap.set(era, (eraMap.get(era) ?? 0) + 1)

    const bc = p.block_count ?? 0
    const cc = p.character_count ?? 0
    const sc = p.scene_count ?? 0
    characters += cc
    blocks += bc
    scenes += sc
    blockValues.push(bc)
    if (p.parse_quality != null) {
      qualitySum += p.parse_quality
      qualityCount += 1
      qualityValues.push(p.parse_quality)
    }

    return {
      script_id: p.script_id,
      title: p.title,
      collection_name: p.collection_name,
      genre,
      block_count: bc,
      character_count: cc,
      scene_count: sc,
      parse_quality: p.parse_quality ?? 0,
    }
  })

  return {
    kpis: {
      plays: plays.length,
      characters,
      blocks,
      scenes,
      collections: collectionMap.size,
      avgParseQuality: qualityCount ? qualitySum / qualityCount : 0,
    },
    genres: [...genreMap.entries()].map(([name, value]) => ({ name, value })),
    collections: topWithOther(
      [...collectionMap.entries()].map(([name, value]) => ({ name, value })),
      12,
    ),
    eras: topWithOther(
      [...eraMap.entries()].map(([name, value]) => ({ name, value })),
      10,
    ),
    blockBins: binNumeric(
      blockValues,
      [0, 150, 300, 450, 600, 800, Infinity],
      ['<150', '150–300', '300–450', '450–600', '600–800', '800+'],
    ),
    qualityBins: binNumeric(
      qualityValues,
      [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.001],
      ['0.70–0.75', '0.75–0.80', '0.80–0.85', '0.85–0.90', '0.90–0.95', '0.95–1.00'],
    ),
    scatter,
  }
}

export function filterPlays(plays: CatalogPlay[], query: string): CatalogPlay[] {
  const q = query.trim().toLowerCase()
  if (!q) return []
  return plays
    .filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.script_id.includes(q) ||
        p.collection_name.toLowerCase().includes(q),
    )
    .slice(0, 12)
}
