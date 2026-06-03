import type {
  Catalog,
  NarrativeTemplatesGlobal,
  NetworkCompareGlobal,
  PlayCleaned,
  PlayIntegrated,
  PlayNarrative,
  PlayNetwork,
  PlayRole,
  PlayThemes,
  RoleAnalysisGlobal,
  ThemePatternsGlobal,
  ThemeQualityGlobal,
} from '@/types'

const BASE = '/data'

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`加载失败: ${path} (${res.status})`)
  return res.json() as Promise<T>
}

export const api = {
  catalog: () => getJson<Catalog>('/catalog.json'),
  playRole: (id: string) => getJson<PlayRole>(`/analytics/plays/${id}/role.json`),
  playNetwork: (id: string) => getJson<PlayNetwork>(`/analytics/plays/${id}/network.json`),
  playThemes: (id: string) => getJson<PlayThemes>(`/analytics/plays/${id}/themes.json`),
  playNarrative: (id: string) => getJson<PlayNarrative>(`/analytics/plays/${id}/narrative.json`),
  playCleaned: (id: string) => getJson<PlayCleaned>(`/plays/${id}.json`),
  playIntegrated: (id: string) => getJson<PlayIntegrated>(`/analytics/plays/${id}/integrated.json`),
  globalRole: () => getJson<RoleAnalysisGlobal>('/analytics/global/role_analysis.json'),
  globalNetwork: () => getJson<NetworkCompareGlobal>('/analytics/global/network_compare.json'),
  globalThemes: () => getJson<ThemePatternsGlobal>('/analytics/global/theme_patterns.json'),
  globalThemeQuality: () => getJson<ThemeQualityGlobal>('/analytics/global/theme_quality.json'),
  globalNarrative: () => getJson<NarrativeTemplatesGlobal>('/analytics/global/narrative_templates.json'),
}
