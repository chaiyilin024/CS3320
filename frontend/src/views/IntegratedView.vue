<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  buildCharacterCentralityBar,
  buildCharacterTopicHeatmap,
  buildCharacterTopicSankey,
  buildCorrelationTypePie,
  buildHangdangPeakBar,
  buildKpis,
  buildNetworkStageDeltaBar,
  buildRhythmTensionOverlay,
  buildStageNetworkEvolution,
  buildThemeStageHeatmap,
  buildTopCorrelationsBar,
  buildTopicWeightMini,
} from '@/utils/integratedCharts'
import { buildForceGraph } from '@/utils/networkCharts'
import type { EChartsOption } from 'echarts'
import type { PlayIntegrated, PlayNarrative, PlayNetwork, PlayThemes } from '@/types'

const store = useFilterStore()
const integrated = ref<PlayIntegrated | null>(null)
const network = ref<PlayNetwork | null>(null)
const narrative = ref<PlayNarrative | null>(null)
const themes = ref<PlayThemes | null>(null)
const loading = ref(true)

const corrPieEl = ref<HTMLElement | null>(null)
const corrBarEl = ref<HTMLElement | null>(null)
const charTopicHeatEl = ref<HTMLElement | null>(null)
const charTopicSankeyEl = ref<HTMLElement | null>(null)
const stageNetEl = ref<HTMLElement | null>(null)
const stageDeltaEl = ref<HTMLElement | null>(null)
const themeStageEl = ref<HTMLElement | null>(null)
const hangdangPeakEl = ref<HTMLElement | null>(null)
const rhythmOverlayEl = ref<HTMLElement | null>(null)
const centralityEl = ref<HTMLElement | null>(null)
const graphEl = ref<HTMLElement | null>(null)
const topicBarEl = ref<HTMLElement | null>(null)

const selectedIds = computed(() => store.selectedCharacterIds)
const kpis = computed(() => buildKpis(integrated.value, network.value, narrative.value))

const corrPieOpt = computed(() => buildCorrelationTypePie(integrated.value))
const corrBarOpt = computed(() => buildTopCorrelationsBar(integrated.value))
const charTopicHeatOpt = computed(() =>
  buildCharacterTopicHeatmap(integrated.value?.character_topic_matrix),
)
const charTopicSankeyOpt = computed(() =>
  buildCharacterTopicSankey(integrated.value?.character_topic_matrix),
)
const stageNetOpt = computed(() =>
  buildStageNetworkEvolution(integrated.value?.stage_network_snapshots),
)
const stageDeltaOpt = computed(() => buildNetworkStageDeltaBar(integrated.value))
const themeStageOpt = computed(() => buildThemeStageHeatmap(integrated.value))
const hangdangPeakOpt = computed(() => buildHangdangPeakBar(integrated.value))
const rhythmOverlayOpt = computed(() =>
  buildRhythmTensionOverlay(narrative.value, integrated.value?.stage_network_snapshots),
)
const centralityOpt = computed(() =>
  buildCharacterCentralityBar(integrated.value, network.value),
)
const graphOpt = computed(() =>
  network.value ? buildForceGraph(network.value, selectedIds.value) : ({} as EChartsOption),
)
const topicBarOpt = computed(() => buildTopicWeightMini(themes.value?.topics ?? []))

function onGraphClick(params: unknown) {
  const p = params as { dataType?: string; data?: { id?: string } }
  if (p.dataType === 'node' && p.data?.id) store.toggleCharacter(p.data.id)
}

const corrPieChart = useChart(corrPieEl, () => corrPieOpt.value as EChartsOption, [corrPieOpt])
const corrBarChart = useChart(corrBarEl, () => corrBarOpt.value as EChartsOption, [corrBarOpt])
const charTopicHeatChart = useChart(charTopicHeatEl, () => charTopicHeatOpt.value as EChartsOption, [charTopicHeatOpt])
const charTopicSankeyChart = useChart(charTopicSankeyEl, () => charTopicSankeyOpt.value as EChartsOption, [charTopicSankeyOpt])
const stageNetChart = useChart(stageNetEl, () => stageNetOpt.value as EChartsOption, [stageNetOpt])
const stageDeltaChart = useChart(stageDeltaEl, () => stageDeltaOpt.value as EChartsOption, [stageDeltaOpt])
const themeStageChart = useChart(themeStageEl, () => themeStageOpt.value as EChartsOption, [themeStageOpt])
const hangdangPeakChart = useChart(hangdangPeakEl, () => hangdangPeakOpt.value as EChartsOption, [hangdangPeakOpt])
const rhythmOverlayChart = useChart(rhythmOverlayEl, () => rhythmOverlayOpt.value as EChartsOption, [rhythmOverlayOpt])
const centralityChart = useChart(centralityEl, () => centralityOpt.value as EChartsOption, [centralityOpt])
const graphChart = useChart(
  graphEl,
  () => graphOpt.value as EChartsOption,
  [graphOpt, selectedIds],
  { click: onGraphClick },
)
const topicBarChart = useChart(topicBarEl, () => topicBarOpt.value as EChartsOption, [topicBarOpt])

function refreshCharts() {
  corrPieChart.render()
  corrBarChart.render()
  charTopicHeatChart.render()
  charTopicSankeyChart.render()
  stageNetChart.render()
  stageDeltaChart.render()
  themeStageChart.render()
  hangdangPeakChart.render()
  rhythmOverlayChart.render()
  centralityChart.render()
  graphChart.render()
  topicBarChart.render()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    const id = store.scriptId
    const [resIntegrated, resNetwork, resNarrative, resThemes] = await Promise.all([
      api.playIntegrated(id).catch(() => null),
      api.playNetwork(id),
      api.playNarrative(id),
      api.playThemes(id),
    ])
    integrated.value = resIntegrated
    network.value = resNetwork
    narrative.value = resNarrative
    themes.value = resThemes
  } finally {
    loading.value = false
    refreshCharts()
  }
}

onMounted(load)
watch(() => store.scriptId, load)
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h2 class="page-title">综合探索</h2>
      <p class="page-desc">
        {{ integrated?.title ?? '' }} · 跨行当、关系网、主题与叙事的关联洞察
      </p>
    </header>

    <div v-if="loading" class="loading">加载中…</div>

    <div v-else-if="!integrated && !network" class="loading">
      暂无综合数据，请先运行分析生成 integrated.json
    </div>

    <template v-else>
      <section class="kpi-row">
        <div v-for="k in kpis" :key="k.label" class="kpi-card">
          <span class="kpi-value">{{ k.value }}</span>
          <span class="kpi-label">{{ k.label }}</span>
          <span v-if="k.hint" class="kpi-hint">{{ k.hint }}</span>
        </div>
      </section>

      <section v-if="integrated?.summary_insights?.length" class="insights">
        <h3 class="section-title">自动洞察摘要</h3>
        <ul>
          <li v-for="(line, i) in integrated!.summary_insights" :key="i">{{ line }}</li>
        </ul>
      </section>

      <section class="section">
        <h3 class="section-title">关联规则总览</h3>
        <div class="grid-2">
          <ChartCard title="关联类型构成" subtitle="人物-主题 / 网络-阶段 / 行当-叙事等">
            <div ref="corrPieEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="Top 关联强度" subtitle="按 strength 排序，悬停查看依据">
            <div ref="corrBarEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">人物 ↔ 主题</h3>
        <div class="grid-2">
          <ChartCard title="人物×主题热力图" subtitle="台词与 LDA 主题的关联强度">
            <div ref="charTopicHeatEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="人物→主题桑基图" subtitle="主要人物与主导主题的流向">
            <div ref="charTopicSankeyEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <div class="grid-2 section-gap">
          <ChartCard title="主题权重" subtitle="本剧各主题占比">
            <div ref="topicBarEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="主题×叙事阶段" subtitle="哪段情节对应哪类主题">
            <div ref="themeStageEl" class="chart chart-sm" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">网络 ↔ 叙事阶段</h3>
        <ChartCard title="阶段网络演化" subtitle="各情节阶段的同场密度、人物数与边数">
          <div ref="stageNetEl" class="chart chart-tall" />
        </ChartCard>
        <div class="grid-2 section-gap">
          <ChartCard title="阶段密度变化" subtitle="相对前一阶段的网络密度增减">
            <div ref="stageDeltaEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="张力 × 网络密度叠图" subtitle="叙事张力曲线 + 阶段网络密度（虚线）">
            <div ref="rhythmOverlayEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">人物网络与行当</h3>
        <div class="grid-2">
          <ChartCard
            title="人物关系网络"
            :subtitle="selectedIds.length ? `已选：${selectedIds.join('、')}（点击节点切换）` : '点击节点可联动其他页面'"
          >
            <div ref="graphEl" class="chart chart-tall" />
          </ChartCard>
          <div class="side-col">
            <ChartCard title="核心人物中心性" subtitle="加权度 Top 人物">
              <div ref="centralityEl" class="chart chart-md" />
            </ChartCard>
            <ChartCard title="行当情感峰值" subtitle="各行当在叙事中的情感高峰块位置">
              <div ref="hangdangPeakEl" class="chart chart-sm" />
            </ChartCard>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; gap: 1.25rem; }
.page-head { margin-bottom: 0.25rem; }
.page-title { margin: 0; font-family: var(--font-serif); font-size: 1.5rem; }
.page-desc { margin: 0.35rem 0 0; font-size: 0.88rem; color: var(--text-muted); }
.loading { color: var(--text-muted); padding: 2rem; text-align: center; }

.section-title {
  margin: 0 0 0.65rem;
  font-family: var(--font-serif);
  font-size: 1.05rem;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.65rem;
}
.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: 0.75rem 0.85rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  border-left: 3px solid var(--accent-red, #8b2500);
}
.kpi-value { font-size: 1.35rem; font-weight: 700; font-family: var(--font-serif); }
.kpi-label { font-size: 0.82rem; font-weight: 600; }
.kpi-hint { font-size: 0.72rem; color: var(--text-muted); }

.insights {
  padding: 0.85rem 1rem;
  background: #fff8ee;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.insights ul { margin: 0; padding-left: 1.2rem; }
.insights li { font-size: 0.88rem; line-height: 1.55; color: var(--text); margin-bottom: 0.25rem; }

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.side-col { display: flex; flex-direction: column; gap: 0.85rem; }
.section-gap { margin-top: 0.85rem; }

.chart { width: 100%; display: block; }
.chart-tall { height: 360px; }
.chart-md { height: 300px; }
.chart-sm { height: 240px; }

@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 900px) {
  .grid-2 { grid-template-columns: 1fr; }
  .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
