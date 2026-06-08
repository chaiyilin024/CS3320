<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import SectionTabs from '@/components/SectionTabs.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  buildCorpusStageBar,
  buildGenreStageStacked,
  buildGlobalPerformancePie,
  buildTemplateDistribution,
} from '@/utils/narrativeCharts'
import {
  buildGenreCompareBar,
  buildMetricBoxplot,
  buildPlaysMetricScatter,
} from '@/utils/networkCharts'
import {
  buildEvolutionStacked,
  buildGlobalHeatmap,
} from '@/utils/roleCharts'
import {
  buildCooccurrenceHeatmap,
  buildCommonPatternsBar,
  buildGlobalPlayHeatmap,
  buildPlayVsGlobalRadar,
  matchPlaysForPattern,
  resolveGlobalHeatmapRows,
} from '@/utils/themeCharts'
import type { EChartsOption } from 'echarts'
import type {
  NarrativeTemplatesGlobal,
  NetworkCompareGlobal,
  PlayNetwork,
  PlayThemes,
  RoleAnalysisGlobal,
  ThemePatternsGlobal,
} from '@/types'

const props = defineProps<{ visible?: boolean }>()

const store = useFilterStore()
const loading = ref(true)
const sub = ref('role')

const subTabs = [
  { id: 'role', label: '人物行当' },
  { id: 'network', label: '关系网络' },
  { id: 'theme', label: '主题模式' },
  { id: 'narrative', label: '叙事结构' },
]

const globalRole = ref<RoleAnalysisGlobal | null>(null)
const globalNet = ref<NetworkCompareGlobal | null>(null)
const globalThemes = ref<ThemePatternsGlobal | null>(null)
const globalNarr = ref<NarrativeTemplatesGlobal | null>(null)
const playNet = ref<PlayNetwork | null>(null)
const playThemes = ref<PlayThemes | null>(null)

const evolutionMode = ref<'era' | 'collection'>('era')
const compareGroup = ref<'by_genre' | 'by_collection'>('by_genre')
const boxMetric = ref<'density' | 'avg_clustering' | 'avg_degree'>('density')
const selectedPattern = ref<string[] | null>(null)

const roleHeatEl = ref<HTMLElement | null>(null)
const roleEraEl = ref<HTMLElement | null>(null)
const netBoxEl = ref<HTMLElement | null>(null)
const netScatterEl = ref<HTMLElement | null>(null)
const netCompareEl = ref<HTMLElement | null>(null)
const themeHeatEl = ref<HTMLElement | null>(null)
const themeCooccurEl = ref<HTMLElement | null>(null)
const themeRadarEl = ref<HTMLElement | null>(null)
const themePatternEl = ref<HTMLElement | null>(null)
const narrTemplateEl = ref<HTMLElement | null>(null)
const narrStageEl = ref<HTMLElement | null>(null)
const narrGenreStageEl = ref<HTMLElement | null>(null)
const narrPerfEl = ref<HTMLElement | null>(null)

const roleHeatOpt = computed(() =>
  buildGlobalHeatmap(globalRole.value?.global_feature_hangdang_matrix ?? []),
)
const roleEraOpt = computed(() => {
  const g = globalRole.value
  if (!g) return buildEvolutionStacked([])
  if (evolutionMode.value === 'collection') {
    return buildEvolutionStacked(
      (g.by_collection ?? []).map((b) => ({
        label: b.collection_name,
        hangdang_distribution: b.hangdang_distribution,
        play_count: b.play_count,
      })),
    )
  }
  return buildEvolutionStacked(
    (g.by_era_bucket ?? []).map((b) => ({
      label: b.era,
      hangdang_distribution: b.hangdang_distribution,
      play_count: b.play_count,
    })),
  )
})

const netBoxOpt = computed(() => {
  if (!playNet.value) return {} as EChartsOption
  const highlight = compareGroup.value === 'by_genre' ? playNet.value.genre : undefined
  const cur = boxMetric.value === 'density'
    ? playNet.value.metrics.density
    : boxMetric.value === 'avg_clustering'
      ? playNet.value.metrics.avg_clustering
      : playNet.value.metrics.avg_degree
  return buildMetricBoxplot(globalNet.value, compareGroup.value, boxMetric.value, highlight ?? null, cur ?? null)
})
const netScatterOpt = computed(() =>
  buildPlaysMetricScatter(globalNet.value, 'density', 'avg_clustering', store.scriptId),
)
const netCompareOpt = computed(() =>
  playNet.value ? buildGenreCompareBar(playNet.value, globalNet.value) : ({} as EChartsOption),
)

const themeHeatOpt = computed(() => buildGlobalPlayHeatmap(globalThemes.value, store.scriptId))
const themeCooccurOpt = computed(() => buildCooccurrenceHeatmap(globalThemes.value))
const themeRadarOpt = computed(() =>
  playThemes.value ? buildPlayVsGlobalRadar(playThemes.value, globalThemes.value) : ({} as EChartsOption),
)
const themePatternOpt = computed(() => buildCommonPatternsBar(globalThemes.value))

const narrTemplateOpt = computed(() => buildTemplateDistribution(globalNarr.value))
const narrStageOpt = computed(() => buildCorpusStageBar(globalNarr.value))
const narrGenreStageOpt = computed(() => buildGenreStageStacked(globalNarr.value))
const narrPerfOpt = computed(() => buildGlobalPerformancePie(globalNarr.value))

const patternPlays = computed(() => {
  if (!selectedPattern.value) return []
  return matchPlaysForPattern(globalThemes.value, selectedPattern.value)
})

function onThemeHeatClick(params: unknown) {
  const p = params as { componentType?: string; data?: [number, number, number] }
  if (p.componentType !== 'series' || !p.data || !globalThemes.value) return
  const row = resolveGlobalHeatmapRows(globalThemes.value, store.scriptId)[p.data[1]]
  if (row?.script_id) store.setScriptId(row.script_id)
}

function selectPattern(labels: string[]) {
  selectedPattern.value = selectedPattern.value?.join('|') === labels.join('|') ? null : labels
}

const roleHeatChart = useChart(roleHeatEl, () => roleHeatOpt.value as EChartsOption, [roleHeatOpt])
const roleEraChart = useChart(roleEraEl, () => roleEraOpt.value as EChartsOption, [roleEraOpt, evolutionMode])
const netBoxChart = useChart(netBoxEl, () => netBoxOpt.value as EChartsOption, [netBoxOpt, compareGroup, boxMetric])
const netScatterChart = useChart(netScatterEl, () => netScatterOpt.value as EChartsOption, [netScatterOpt])
const netCompareChart = useChart(netCompareEl, () => netCompareOpt.value as EChartsOption, [netCompareOpt])
const themeHeatChart = useChart(
  themeHeatEl,
  () => themeHeatOpt.value as EChartsOption,
  [themeHeatOpt],
  { click: onThemeHeatClick },
)
const themeCooccurChart = useChart(themeCooccurEl, () => themeCooccurOpt.value as EChartsOption, [themeCooccurOpt])
const themeRadarChart = useChart(themeRadarEl, () => themeRadarOpt.value as EChartsOption, [themeRadarOpt])
const themePatternChart = useChart(themePatternEl, () => themePatternOpt.value as EChartsOption, [themePatternOpt])
const narrTemplateChart = useChart(narrTemplateEl, () => narrTemplateOpt.value as EChartsOption, [narrTemplateOpt])
const narrStageChart = useChart(narrStageEl, () => narrStageOpt.value as EChartsOption, [narrStageOpt])
const narrGenreStageChart = useChart(narrGenreStageEl, () => narrGenreStageOpt.value as EChartsOption, [narrGenreStageOpt])
const narrPerfChart = useChart(narrPerfEl, () => narrPerfOpt.value as EChartsOption, [narrPerfOpt])

function refreshCharts() {
  roleHeatChart.render()
  roleEraChart.render()
  netBoxChart.render()
  netScatterChart.render()
  netCompareChart.render()
  themeHeatChart.render()
  themeCooccurChart.render()
  themeRadarChart.render()
  themePatternChart.render()
  narrTemplateChart.render()
  narrStageChart.render()
  narrGenreStageChart.render()
  narrPerfChart.render()
}

function onSubChange() {
  void nextTick(() => refreshCharts())
}

async function loadGlobals() {
  loading.value = true
  try {
    const [role, net, themes, narr] = await Promise.allSettled([
      api.globalRole(),
      api.globalNetwork(),
      api.globalThemes(),
      api.globalNarrative(),
    ])
    globalRole.value = role.status === 'fulfilled' ? role.value : null
    globalNet.value = net.status === 'fulfilled' ? net.value : null
    globalThemes.value = themes.status === 'fulfilled' ? themes.value : null
    globalNarr.value = narr.status === 'fulfilled' ? narr.value : null
  } finally {
    loading.value = false
    refreshCharts()
  }
}

async function loadPlayContext() {
  if (!store.scriptId) {
    playNet.value = null
    playThemes.value = null
    netCompareChart.render()
    themeRadarChart.render()
    return
  }
  const id = store.scriptId
  const [net, themes] = await Promise.allSettled([
    api.playNetwork(id),
    api.playThemes(id),
  ])
  playNet.value = net.status === 'fulfilled' ? net.value : null
  playThemes.value = themes.status === 'fulfilled' ? themes.value : null
  netBoxChart.render()
  netCompareChart.render()
  themeRadarChart.render()
}

onMounted(async () => {
  await loadGlobals()
  await loadPlayContext()
})

watch(() => store.scriptId, loadPlayContext)
watch(() => props.visible, (v) => {
  if (v) void nextTick(() => refreshCharts())
})

defineExpose({ refreshCharts })
</script>

<template>
  <div class="corpus">
    <div v-if="loading" class="loading">加载全库分析…</div>
    <template v-else>
      <SectionTabs v-model="sub" :tabs="subTabs" @change="onSubChange" />

      <div v-show="sub === 'role'" class="panel">
        <ChartCard title="全局特征 × 行当" subtitle="跨剧本共现热力图（颜色越深共现越多）">
          <div ref="roleHeatEl" class="chart chart-heat" />
        </ChartCard>
        <template v-if="globalRole?.by_era_bucket?.length || globalRole?.by_collection?.length">
          <div class="tab-row">
            <button type="button" class="tab" :class="{ active: evolutionMode === 'era' }" @click="evolutionMode = 'era'">按时代</button>
            <button type="button" class="tab" :class="{ active: evolutionMode === 'collection' }" @click="evolutionMode = 'collection'">按集合</button>
          </div>
          <ChartCard
            :title="evolutionMode === 'era' ? '时代 × 行当占比' : '集合 × 行当占比'"
            subtitle="生旦净丑堆叠 · 纵轴为各行当占该组人物比例"
          >
            <div ref="roleEraEl" class="chart chart-md" />
          </ChartCard>
        </template>
      </div>

      <div v-show="sub === 'network'" class="panel">
        <div class="tab-row">
          <button type="button" class="tab" :class="{ active: compareGroup === 'by_genre' }" @click="compareGroup = 'by_genre'">按体裁</button>
          <button type="button" class="tab" :class="{ active: compareGroup === 'by_collection' }" @click="compareGroup = 'by_collection'">按集合</button>
          <button type="button" class="tab" :class="{ active: boxMetric === 'density' }" @click="boxMetric = 'density'">密度</button>
          <button type="button" class="tab" :class="{ active: boxMetric === 'avg_clustering' }" @click="boxMetric = 'avg_clustering'">聚类</button>
          <button type="button" class="tab" :class="{ active: boxMetric === 'avg_degree' }" @click="boxMetric = 'avg_degree'">平均度</button>
        </div>
        <div class="grid-2">
          <ChartCard title="网络指标箱线图" subtitle="各分组全库分布 · 红点=当前剧本（需已选剧本）">
            <div ref="netBoxEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="全库散点" subtitle="密度 × 聚类 · 高亮当前剧本">
            <div ref="netScatterEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <ChartCard
          v-if="playNet?.genre"
          title="同体裁对比"
          :subtitle="`当前剧本 vs ${playNet.genre} 全库均值`"
        >
          <div ref="netCompareEl" class="chart chart-sm" />
        </ChartCard>
      </div>

      <div v-show="sub === 'theme'" class="panel">
        <div class="grid-2">
          <ChartCard
            title="跨剧主题热力"
            :subtitle="`点击行切换剧本（全库 ${globalThemes?.play_topic_matrix.length ?? 0} 部，Top48）`"
          >
            <div ref="themeHeatEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="主题共现" subtitle="全局模型中主题同时出现的频率">
            <div ref="themeCooccurEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <ChartCard
          v-if="playThemes"
          title="当前剧本 vs 全库"
          subtitle="主题向量雷达对比（需已选剧本）"
        >
          <div ref="themeRadarEl" class="chart chart-sm" />
        </ChartCard>
        <ChartCard title="主题组合模式" subtitle="频繁主题套餐 · 点击卡片筛选范例剧本">
          <div ref="themePatternEl" class="chart chart-sm" />
        </ChartCard>
        <div v-if="globalThemes?.common_patterns?.length" class="pattern-cards">
          <button
            v-for="(pat, i) in globalThemes.common_patterns.slice(0, 8)"
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
      </div>

      <div v-show="sub === 'narrative'" class="panel">
        <p v-if="globalNarr" class="hint">
          基于 {{ globalNarr.total_play_count ?? '—' }} 部剧本的叙事聚合
        </p>
        <div class="grid-2">
          <ChartCard title="叙事模板分布" subtitle="四类模板在全库中的占比">
            <div ref="narrTemplateEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="全库五阶段均值" subtitle="全部剧本阶段占比的算术平均">
            <div ref="narrStageEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <div class="grid-2">
          <ChartCard title="体裁 × 阶段构成" subtitle="各体裁五阶段堆叠占比">
            <div ref="narrGenreStageEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="全库表演构成" subtitle="唱念做打标记累计（全库）">
            <div ref="narrPerfEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.corpus { display: flex; flex-direction: column; gap: 1rem; }
.loading { color: var(--text-muted); padding: 1.5rem; text-align: center; }
.panel { display: flex; flex-direction: column; gap: 0.85rem; }
.hint { margin: 0; font-size: 0.8rem; color: var(--text-muted); }
.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.tab-row { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.tab {
  padding: 0.3rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  font-size: 0.78rem;
  cursor: pointer;
  font-family: inherit;
}
.tab.active { border-color: var(--accent-red); color: var(--accent-red); background: #fff5f2; }
.chart { width: 100%; display: block; }
.chart-sm { height: 260px; }
.chart-md { height: 300px; }
.chart-heat { height: 360px; }
.pattern-cards { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.pattern-card {
  display: flex; flex-direction: column; align-items: flex-start; gap: 0.2rem;
  padding: 0.55rem 0.75rem; border: 1px solid var(--border); border-radius: 8px;
  background: var(--surface); cursor: pointer; font-family: inherit; text-align: left;
}
.pattern-card.active { border-color: var(--accent-gold); background: #fff8ee; }
.pattern-card .labels { font-size: 0.85rem; font-weight: 600; }
.pattern-card .meta { font-size: 0.72rem; color: var(--text-muted); }
.pattern-plays { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: center; }
.plays-label { font-size: 0.78rem; color: var(--text-muted); }
.play-chip {
  padding: 0.25rem 0.55rem; border: 1px solid var(--border); border-radius: 999px;
  background: var(--surface); font-size: 0.75rem; cursor: pointer; font-family: inherit;
}
.play-chip:hover { border-color: var(--accent-gold); }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
