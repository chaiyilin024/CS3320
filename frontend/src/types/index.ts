export interface CatalogPlay {
  script_id: string
  title: string
  collection_id: string
  collection_name: string
  character_count?: number
  block_count?: number
  scene_count?: number
  char_count?: number
  page_count?: number
  parse_quality?: number
  tags?: { genre_inferred?: string; era_inferred?: string }
}

export interface Catalog {
  version: string
  plays: CatalogPlay[]
}

export interface PlayRole {
  script_id: string
  hangdang_distribution: Record<string, number>
  hangdang_coarse_distribution?: Record<string, number>
  labeled_count?: number
  inferred_count?: number
  characters: Array<{
    character_id: string
    name: string
    hangdang_labeled?: string | null
    hangdang_inferred?: string | null
    hangdang_final: string
    confidence: number
    top_features?: string[]
    traits_derived?: {
      gender?: string
      age?: string
      identity?: string
      personality?: string[]
      performance_cues?: string[]
    }
  }>
  trait_summary?: Array<{ trait: string; hangdang: string; count: number }>
}

export interface PlayNetwork {
  script_id: string
  title?: string
  genre?: string
  nodes: Array<{
    id: string
    name: string
    hangdang: string
    hangdang_coarse?: string
    degree: number
    weighted_degree?: number
    betweenness?: number
    weighted_betweenness?: number
    closeness?: number
    eigenvector?: number
    community_id?: number
    is_main?: boolean
  }>
  links: Array<{
    source: string
    target: string
    weight: number
    types?: string[]
    dialogue_count?: number
    normalized_weight?: number
  }>
  metrics: {
    node_count: number
    edge_count: number
    density: number
    avg_clustering?: number
    avg_weighted_clustering?: number
    avg_degree?: number
    avg_weighted_degree?: number
    modularity?: number
    assortativity_hangdang?: number
    component_count?: number
    main_subgraph?: {
      node_count: number
      edge_count: number
      density?: number
      avg_clustering?: number
      modularity?: number
    }
  }
}

export interface ThemeTopicAssessment {
  topic_id: number
  label: string
  tier: 'strong' | 'weak' | 'fallback' | 'noise'
  label_score: number
  keyword_signal: number
  weight: number
  issues?: string[]
}

export interface PlayThemeQuality {
  score: number
  labeled_weight: number
  fallback_weight: number
  keyword_signal_avg?: number
  tier_counts?: Record<string, number>
  method?: string
  issues?: string[]
  topic_assessments?: ThemeTopicAssessment[]
}

export interface PlayThemes {
  script_id: string
  title?: string
  model?: {
    method?: string
    num_topics_global?: number
    trained_at?: string
  }
  topics: Array<{
    topic_id: number
    label: string
    weight: number
    keywords: string[]
    keyword_weights?: number[]
  }>
  topic_composition: number[]
  representative_blocks?: Array<{
    topic_id: number
    block_id: string
    block_index?: number
    text_snippet: string
    context_snippet?: string
    speaker_id?: string | null
    speaker_name?: string
    score?: number
  }>
  quality?: PlayThemeQuality
}

export interface PlayBlock {
  block_id: string
  block_index: number
  type: string
  speaker_id?: string | null
  speaker_name_raw?: string
  text: string
  performance_tags?: string[]
}

export interface PlayCleaned {
  script_id: string
  title?: string
  characters: Array<{ character_id: string; name: string }>
  blocks: PlayBlock[]
}

export interface PlayNarrative {
  script_id: string
  title?: string
  plot_stages: Array<{
    stage: string
    label?: string
    block_range: [number, number]
    summary?: string
  }>
  rhythm_series: Array<{
    block_index: number
    dialogue_density?: number
    aria_ratio?: number
    action_intensity?: number
    emotion_score?: number
    tension_score?: number
  }>
  performance_mark_distribution: Record<string, number>
  performance_by_stage?: Array<{ stage: string; distribution: Record<string, number> }>
  block_annotations?: Array<{
    block_index: number
    block_id?: string
    stage?: string
    dominant_topic_id?: number
    emotion_score?: number
  }>
}

export interface IntegratedCorrelation {
  type: 'character_theme' | 'network_stage' | 'hangdang_narrative' | 'theme_narrative' | 'character_network' | 'other'
  strength: number
  character_id?: string
  character_name?: string
  topic_id?: number
  topic_label?: string
  stage?: string
  hangdang?: string
  peak_block_index?: number
  edge_density_delta?: number
  evidence?: string
}

export interface PlayIntegrated {
  script_id: string
  title?: string
  summary_insights: string[]
  character_topic_matrix?: Array<{
    character_id: string
    character_name?: string
    topic_id: number
    topic_label?: string
    strength: number
  }>
  stage_network_snapshots?: Array<{
    stage: string
    block_range: [number, number]
    edge_density: number
    node_count: number
    edge_count?: number
  }>
  correlations?: IntegratedCorrelation[]
}

export interface RoleAnalysisGlobal {
  global_feature_hangdang_matrix: Array<{
    feature: string
    hangdang: string
    count: number
    ratio?: number
  }>
  by_collection?: Array<{
    collection_id: string
    collection_name: string
    hangdang_distribution: Record<string, number>
    play_count: number
  }>
  by_era_bucket?: Array<{
    era: string
    hangdang_distribution: Record<string, number>
    play_count: number
  }>
}

export interface ThemePatternsGlobal {
  topic_labels: Array<{ topic_id: number; label: string; keywords?: string[] }>
  play_topic_matrix: Array<{
    script_id: string
    title?: string
    weights: number[]
  }>
  topic_cooccurrence?: Array<{ topic_a: number; topic_b: number; count: number }>
  common_patterns?: Array<{
    labels: string[]
    support: number
    play_count: number
  }>
}

export interface ThemeQualityGlobal {
  summary: {
    play_count: number
    avg_score: number
    low_quality_count?: number
    low_quality_threshold?: number
    fallback_label_share?: number
    tier_totals?: Record<string, number>
  }
  label_distribution: Array<{ label: string; topic_count: number; weight_sum?: number }>
  fallback_keywords?: Array<{ keyword: string; count: number }>
  low_quality_plays?: Array<{
    script_id: string
    title?: string
    score: number
    fallback_weight?: number
    issues?: string[]
  }>
  plays?: Array<{
    script_id: string
    title?: string
    genre?: string
    score: number
    labeled_weight?: number
    fallback_weight?: number
    issues?: string[]
  }>
}

export interface NetworkCompareGlobal {
  by_genre: Array<{
    group_label: string
    play_count: number
    metrics: Record<string, { mean?: number; values?: number[] }>
  }>
  plays?: Array<{ script_id: string; title?: string; metrics: PlayNetwork['metrics'] }>
}

export interface NarrativeTemplatesGlobal {
  templates: Array<{
    template_id: string
    label: string
    play_count: number
    stage_proportions?: Record<string, number>
  }>
  by_genre?: Array<{
    genre: string
    play_count: number
    avg_rhythm_curve?: PlayNarrative['rhythm_series']
  }>
}
