import type { CatalogPlay } from '@/types'

export interface CatalogFilter {
  genre: string | null
  collectionId: string | null
}

export function filterCatalogPlays(plays: CatalogPlay[], f: CatalogFilter): CatalogPlay[] {
  return plays.filter((p) => {
    if (f.genre && (p.tags?.genre_inferred ?? '未知') !== f.genre) return false
    if (f.collectionId && p.collection_id !== f.collectionId) return false
    return true
  })
}

export function uniqueGenres(plays: CatalogPlay[]): string[] {
  const set = new Set(plays.map((p) => p.tags?.genre_inferred ?? '未知'))
  return [...set].sort((a, b) => a.localeCompare(b, 'zh'))
}

export function uniqueCollections(plays: CatalogPlay[]): Array<{ id: string; name: string }> {
  const map = new Map<string, string>()
  plays.forEach((p) => map.set(p.collection_id, p.collection_name))
  return [...map.entries()]
    .map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name, 'zh'))
}
