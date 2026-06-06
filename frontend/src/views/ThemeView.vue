<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  assessmentForTopic,
  buildCooccurrenceHeatmap,
  buildCommonPatternsBar,
  buildFallbackKeywordBar,
  matchPlaysForPattern,
  buildGlobalLabelDist,
  buildGlobalPlayHeatmap,
  buildGlobalTierPie,
  resolveGlobalHeatmapRows,
  buildKeywordBar,
  buildKeywordHeatmap,
  buildPlayVsGlobalRadar,
  buildSnippetScoreBar,
  buildSpeakerTopicBar,
  buildTopicRose,
  buildTopicSankey,
  buildTopicTierBar,
  buildTopicTimeline,
  buildTopicWeightBar,
  topicColor,
  topicTierColor,
  topicTierLabel,
} from '@/utils/themeCharts'
import type { EChartsOption } from 'echarts'
import type { PlayThemes, ThemePatternsGlobal, ThemeQualityGlobal } from '@/types'

const store = useFilterStore()
const router = useRouter()
const themes = ref<PlayThemes | null>(null)
const selectedPattern = ref<string[] | null>(null)
const patterns = ref<ThemePatternsGlobal | null>(null)
const themeQuality = ref<ThemeQualityGlobal | null>(null)
const loading = ref(true)

const roseEl = ref<HTMLElement | null>(null)
const weightEl = ref<HTMLElement | null>(null)
const keywordEl = ref<HTMLElement | null>(null)
const kwHeatEl = ref<HTMLElement | null>(null)
const timelineEl = ref<HTMLElement | null>(null)
const speakerEl = ref<HTMLElement | null>(null)
const scoreEl = ref<HTMLElement | null>(null)
const sankeyEl = ref<HTMLElement | null>(null)
const globalHeatEl = ref<HTMLElement | null>(null)
const cooccurEl = ref<HTMLElement | null>(null)
const radarEl = ref<HTMLElement | null>(null)
const tierEl = ref<HTMLElement | null>(null)
const globalLabelEl = ref<HTMLElement | null>(null)
const globalTierEl = ref<HTMLElement | null>(null)
const fallbackKwEl = ref<HTMLElement | null>(null)
const patternEl = ref<HTMLElement | null>(null)

const selectedTopic = computed(() => {
  const id = store.selectedTopicIds[0]
  if (id == null || !themes.value) {
    return themes.value?.topics.slice().sort((a, b) => b.weight - a.weight)[0] ?? null
  }
  return themes.value.topics.find((t) => t.topic_id === id) ?? null
})

const roseOpt = computed(() => buildTopicRose(themes.value?.topics ?? []))
const weightOpt = computed(() => buildTopicWeightBar(themes.value?.topics ?? []))
const keywordOpt = computed(() => buildKeywordBar(selectedTopic.value))
const kwHeatOpt = computed(() => buildKeywordHeatmap(themes.value?.topics ?? []))
const timelineOpt = computed(() =>
  buildTopicTimeline(themes.value?.topics ?? [], themes.value?.representative_blocks),
)
const speakerOpt = computed(() =>
  buildSpeakerTopicBar(themes.value?.representative_blocks, themes.value?.topics ?? []),
)
const scoreOpt = computed(() =>
  buildSnippetScoreBar(themes.value?.representative_blocks, themes.value?.topics ?? []),
)
const sankeyOpt = computed(() => buildTopicSankey(themes.value?.topics ?? []))
const globalHeatOpt = computed(() =>
  buildGlobalPlayHeatmap(patterns.value, store.scriptId),
)
const cooccurOpt = computed(() => buildCooccurrenceHeatmap(patterns.value))
const radarOpt = computed(() =>
  themes.value ? buildPlayVsGlobalRadar(themes.value, patterns.value) : ({} as EChartsOption),
)
const tierOpt = computed(() => buildTopicTierBar(themes.value?.quality))
const globalLabelOpt = computed(() => buildGlobalLabelDist(themeQuality.value))
const globalTierOpt = computed(() => buildGlobalTierPie(themeQuality.value))
const fallbackKwOpt = computed(() => buildFallbackKeywordBar(themeQuality.value))
const patternOpt = computed(() => buildCommonPatternsBar(patterns.value))

const patternPlays = computed(() => {
  if (!selectedPattern.value) return []
  return matchPlaysForPattern(patterns.value, selectedPattern.value)
})

const qualityScore = computed(() => themes.value?.quality?.score)
const qualityIssues = computed(() => themes.value?.quality?.issues ?? [])

const roseChart = useChart(roseEl, () => roseOpt.value as EChartsOption, [roseOpt])
const weightChart = useChart(weightEl, () => weightOpt.value as EChartsOption, [weightOpt])
const keywordChart = useChart(keywordEl, () => keywordOpt.value as EChartsOption, [keywordOpt, selectedTopic])
const kwHeatChart = useChart(kwHeatEl, () => kwHeatOpt.value as EChartsOption, [kwHeatOpt])
const timelineChart = useChart(timelineEl, () => timelineOpt.value as EChartsOption, [timelineOpt])
const speakerChart = useChart(speakerEl, () => speakerOpt.value as EChartsOption, [speakerOpt])
const scoreChart = useChart(scoreEl, () => scoreOpt.value as EChartsOption, [scoreOpt])
const sankeyChart = useChart(sankeyEl, () => sankeyOpt.value as EChartsOption, [sankeyOpt])
function onHeatmapClick(params: unknown) {
  const p = params as { componentType?: string; data?: [number, number, number] }
  if (p.componentType !== 'series' || !p.data || !patterns.value) return
  const yi = p.data[1]
  const rows = resolveGlobalHeatmapRows(patterns.value, store.scriptId)
  const row = rows[yi]
  if (row?.script_id) store.setScriptId(row.script_id)
}

const globalHeatChart = useChart(
  globalHeatEl,
  () => globalHeatOpt.value as EChartsOption,
  [globalHeatOpt],
  { click: onHeatmapClick },
)
const cooccurChart = useChart(cooccurEl, () => cooccurOpt.value as EChartsOption, [cooccurOpt])
const radarChart = useChart(radarEl, () => radarOpt.value as EChartsOption, [radarOpt])
const tierChart = useChart(tierEl, () => tierOpt.value as EChartsOption, [tierOpt])
const globalLabelChart = useChart(globalLabelEl, () => globalLabelOpt.value as EChartsOption, [globalLabelOpt])
const globalTierChart = useChart(globalTierEl, () => globalTierOpt.value as EChartsOption, [globalTierOpt])
const fallbackKwChart = useChart(fallbackKwEl, () => fallbackKwOpt.value as EChartsOption, [fallbackKwOpt])
const patternChart = useChart(patternEl, () => patternOpt.value as EChartsOption, [patternOpt])

function refreshCharts() {
  roseChart.render()
  weightChart.render()
  keywordChart.render()
  kwHeatChart.render()
  timelineChart.render()
  speakerChart.render()
  scoreChart.render()
  sankeyChart.render()
  globalHeatChart.render()
  cooccurChart.render()
  radarChart.render()
  tierChart.render()
  globalLabelChart.render()
  globalTierChart.render()
  fallbackKwChart.render()
  patternChart.render()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    themes.value = await api.playThemes(store.scriptId)
    try {
      patterns.value = await api.globalThemes()
    } catch {
      patterns.value = null
    }
    try {
      themeQuality.value = await api.globalThemeQuality()
    } catch {
      themeQuality.value = null
    }
  } finally {
    loading.value = false
    refreshCharts()
  }
}

onMounted(load)
watch(() => store.scriptId, load)

function selectTopic(id: number) {
  store.toggleTopic(id)
  keywordChart.render()
}

function selectPattern(labels: string[]) {
  selectedPattern.value = selectedPattern.value?.join('|') === labels.join('|') ? null : labels
}

function goToNarrativeBlock(blockIndex: number) {
  store.setNarrativeBlockRange([blockIndex, blockIndex + 20])
  router.push({ path: '/narrative', query: { script: store.scriptId ?? undefined } })
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h2 class="page-title">主题分析</h2>
      <p class="page-desc">
        {{ themes?.title ?? '' }}
        <template v-if="themes?.model?.method"> · 模型 {{ themes.model.method.toUpperCase() }}</template>
        · 点击主题卡片切换关键词详情
      </p>
    </header>

    <div v-if="loading" class="loading">加载中…</div>
    <template v-else-if="themes">
      <section class="kpi-row">
        <div class="kpi">
          <span class="num">{{ themes.topics.length }}</span>
          <span class="lbl">本剧主题数</span>
        </div>
        <div class="kpi">
          <span class="num">{{ themes.model?.num_topics_global ?? '—' }}</span>
          <span class="lbl">全局 K 值</span>
        </div>
        <div class="kpi">
          <span class="num">{{ (themes.topics.reduce((m, t) => Math.max(m, t.weight), 0) * 100).toFixed(0) }}%</span>
          <span class="lbl">主导主题占比</span>
        </div>
        <div class="kpi">
          <span class="num">{{ themes.representative_blocks?.length ?? 0 }}</span>
          <span class="lbl">代表片段</span>
        </div>
        <div class="kpi" :class="{ warn: qualityScore != null && qualityScore < 0.55 }">
          <span class="num">{{ qualityScore != null ? (qualityScore * 100).toFixed(0) : '—' }}</span>
          <span class="lbl">主题质量分</span>
        </div>
        <div class="kpi">
          <span class="num">{{ themes.quality ? `${(themes.quality.labeled_weight * 100).toFixed(0)}%` : '—' }}</span>
          <span class="lbl">已识别占比</span>
        </div>
      </section>

      <section v-if="qualityIssues.length" class="quality-alert">
        <strong>质量提示：</strong>{{ qualityIssues.join('；') }}
      </section>

      <section class="section">
        <h3 class="section-title">主题质量检查</h3>
        <p class="section-hint">
          「未识别」对应标签为「其他情节」等未能匹配 theme.json 规则的主题；可据此判断是否需要扩展主题词典或改进分词。
        </p>
        <div class="grid-2">
          <ChartCard title="本剧主题分层" subtitle="强识别 / 弱识别 / 未识别 · 按权重">
            <div ref="tierEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard
            title="全库识别分层"
            :subtitle="`共 ${themeQuality?.summary.play_count ?? 0} 部 · 均分 ${themeQuality ? (themeQuality.summary.avg_score * 100).toFixed(0) : '—'}`"
          >
            <div ref="globalTierEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="全库标签分布" subtitle="「其他情节」为未能自动命名的主题">
            <div ref="globalLabelEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="未识别主题高频词" subtitle="出现在 fallback 主题 Top 关键词中的词">
            <div ref="fallbackKwEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">本剧主题构成</h3>
        <div class="grid-3">
          <ChartCard title="主题玫瑰图" subtitle="面积 ∝ 主题权重">
            <div ref="roseEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="主题权重" subtitle="横向对比各主题占比">
            <div ref="weightEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard
            :title="selectedTopic ? `关键词 · ${selectedTopic.label}` : '关键词详情'"
            subtitle="选中主题的核心词汇权重"
          >
            <div ref="keywordEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <div class="topics">
          <div
            v-for="t in themes.topics"
            :key="t.topic_id"
            class="topic-card"
            :class="{ active: store.selectedTopicIds.includes(t.topic_id) || selectedTopic?.topic_id === t.topic_id }"
            :style="{ borderLeftColor: topicColor(t.topic_id) }"
            @click="selectTopic(t.topic_id)"
          >
            <span class="tid">T{{ t.topic_id }}</span>
            <span
              v-if="assessmentForTopic(themes.quality, t.topic_id)"
              class="tier-badge"
              :style="{ color: topicTierColor(assessmentForTopic(themes.quality, t.topic_id)!.tier), borderColor: topicTierColor(assessmentForTopic(themes.quality, t.topic_id)!.tier) }"
            >
              {{ topicTierLabel(assessmentForTopic(themes.quality, t.topic_id)!.tier) }}
            </span>
            <h4>{{ t.label }}</h4>
            <p class="w">{{ (t.weight * 100).toFixed(1) }}%</p>
            <p class="kw">{{ t.keywords.slice(0, 6).join(' · ') }}</p>
          </div>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">关键词与语义结构</h3>
        <div class="grid-2">
          <ChartCard title="关键词矩阵" subtitle="各主题 Top8 关键词与权重">
            <div ref="kwHeatEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="关键词 → 主题" subtitle="桑基流：词汇如何汇聚到主题">
            <div ref="sankeyEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">剧情中的主题分布</h3>
        <div class="grid-2">
          <ChartCard title="主题时间线" subtitle="代表片段在正文块中的位置 · 气泡=得分">
            <div ref="timelineEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="代表片段得分" subtitle="各片段对主题的归属强度">
            <div ref="scoreEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="说话人 × 主题" subtitle="谁在说哪些主题的代表台词">
            <div ref="speakerEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">跨剧与全局</h3>
        <div class="grid-2">
          <ChartCard
            title="跨剧主题热力"
            :subtitle="`点击行切换剧本（全库 ${patterns?.play_topic_matrix.length ?? 0} 部，Top48）`"
          >
            <div ref="globalHeatEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="主题共现" subtitle="全局模型中主题同时出现的频率">
            <div ref="cooccurEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <ChartCard title="本剧 vs 全库" subtitle="主题向量雷达对比">
          <div ref="radarEl" class="chart chart-sm" />
        </ChartCard>
        <ChartCard title="主题组合模式" subtitle="频繁主题套餐 · 点击卡片筛选范例剧本">
          <div ref="patternEl" class="chart chart-sm" />
        </ChartCard>
        <div v-if="patterns?.common_patterns?.length" class="pattern-cards">
          <button
            v-for="(pat, i) in patterns.common_patterns.slice(0, 8)"
            :key="i"
            type="button"
            class="pattern-card"
            :class="{ active: selectedPattern?.join('|') === pat.labels.join('|') }"
            @click="selectPattern(pat.labels)"
          >
            <span class="labels">{{ pat.labels.join(' + ') }}</span>
            <span class="meta">支持度 {{ (pat.support * 100).toFixed(0) }}% · {{ pat.play_count }} 部</span>
          </button>
        </div>
        <div v-if="patternPlays.length" class="pattern-plays">
          <span class="plays-label">匹配剧本：</span>
          <button
            v-for="p in patternPlays"
            :key="p.script_id"
            type="button"
            class="play-chip"
            @click="store.setScriptId(p.script_id)"
          >
            {{ p.title ?? p.script_id }}
          </button>
        </div>
      </section>

      <ChartCard v-if="themes.representative_blocks?.length" title="代表片段原文" subtitle="各主题最具代表性的台词">
        <ul class="snippets">
          <li
            v-for="(r, i) in themes.representative_blocks.slice(0, 10)"
            :key="i"
            :style="{ borderLeftColor: topicColor(r.topic_id) }"
            class="snippet-click"
            @click="r.block_index != null && goToNarrativeBlock(r.block_index)"
          >
            <span class="meta">
              T{{ r.topic_id }}
              <template v-if="r.speaker_name"> · {{ r.speaker_name }}</template>
              <template v-if="r.block_index != null"> · 块 #{{ r.block_index }}</template>
              <template v-if="r.score != null"> · {{ (r.score * 100).toFixed(0) }}%</template>
            </span>
            {{ r.text_snippet }}
          </li>
        </ul>
      </ChartCard>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-head { margin-bottom: 0.25rem; }
.page-title { margin: 0; font-family: var(--font-serif); font-size: 1.5rem; }
.page-desc { margin: 0.35rem 0 0; font-size: 0.88rem; color: var(--text-muted); }
.loading { color: var(--text-muted); padding: 2rem; text-align: center; }

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 0.65rem;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  text-align: center;
}
.kpi .num { display: block; font-size: 1.35rem; font-weight: 700; color: var(--accent-red); }
.kpi.warn .num { color: #bf360c; }
.kpi .lbl { font-size: 0.75rem; color: var(--text-muted); }

.quality-alert {
  padding: 0.65rem 0.85rem;
  background: #fff8e8;
  border: 1px solid #e8d4a8;
  border-radius: 8px;
  font-size: 0.86rem;
  color: #6d4c00;
}
.section-hint {
  margin: -0.35rem 0 0.65rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}
.tier-badge {
  float: right;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.1rem 0.35rem;
  border: 1px solid;
  border-radius: 4px;
}

.section-title {
  margin: 0 0 0.65rem;
  font-family: var(--font-serif);
  font-size: 1.05rem;
}
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.chart { width: 100%; display: block; }
.chart-md { height: 300px; }
.chart-sm { height: 280px; }

.topics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 0.6rem;
}
.topic-card {
  padding: 0.7rem 0.75rem 0.7rem 0.85rem;
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 8px;
  cursor: pointer;
  background: var(--surface);
  transition: background 0.12s, border-color 0.12s;
}
.topic-card:hover { background: #fffaf3; }
.topic-card.active { border-color: var(--accent-gold); background: #fff8e8; }
.tid { font-size: 0.7rem; color: var(--text-muted); font-weight: 600; }
.topic-card h4 { margin: 0.15rem 0; font-size: 0.92rem; }
.w { margin: 0; font-weight: 600; color: var(--accent-red); font-size: 0.9rem; }
.kw { margin: 0.3rem 0 0; font-size: 0.72rem; color: var(--text-muted); line-height: 1.4; }

.snippets { margin: 0; padding: 0; list-style: none; font-size: 0.86rem; line-height: 1.55; }
.snippets li {
  padding: 0.55rem 0.65rem 0.55rem 0.75rem;
  margin-bottom: 0.4rem;
  border-left: 3px solid #ccc;
  background: #fdfaf5;
  border-radius: 0 6px 6px 0;
}
.meta { display: block; font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem; }
.snippet-click { cursor: pointer; }
.snippet-click:hover { background: #fff8e8; }
.pattern-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.5rem;
  margin-top: 0.65rem;
}
.pattern-card {
  text-align: left;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  font-family: inherit;
}
.pattern-card.active { border-color: #6a1b9a; background: #f3e5f5; }
.pattern-card .labels { display: block; font-size: 0.82rem; font-weight: 600; }
.pattern-card .meta { font-size: 0.72rem; color: var(--text-muted); }
.pattern-plays { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; margin-top: 0.5rem; }
.plays-label { font-size: 0.8rem; color: var(--text-muted); }
.play-chip {
  padding: 0.2rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: #fff8ee;
  font-size: 0.75rem;
  cursor: pointer;
}
.play-chip:hover { border-color: var(--accent-gold); }

@media (max-width: 1100px) { .grid-3 { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
