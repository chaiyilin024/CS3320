<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  buildCharacterCentralityBar,
  buildCharacterTopicHeatmap,
  buildCharacterTopicSankey,
  buildCorrelationTypePie,
  CORRELATION_TYPE_LABELS,
  buildHangdangPeakBar,
  buildKpis,
  buildNetworkStageDeltaBar,
  buildRhythmTensionOverlay,
  buildStageMiniNetwork,
  buildStageNetworkEvolution,
  buildThemeStageHeatmap,
  buildTopCorrelationsBar,
  buildTopicWeightMini,
  correlationLabel,
  sortedCorrelations,
} from '@/utils/integratedCharts'
import { buildForceGraph } from '@/utils/networkCharts'
import type { EChartsOption } from 'echarts'
import type { IntegratedCorrelation, PlayCleaned, PlayIntegrated, PlayNarrative, PlayNetwork, PlayThemes } from '@/types'

const store = useFilterStore()
const router = useRouter()
const integrated = ref<PlayIntegrated | null>(null)
const network = ref<PlayNetwork | null>(null)
const narrative = ref<PlayNarrative | null>(null)
const themes = ref<PlayThemes | null>(null)
const playText = ref<PlayCleaned | null>(null)
const loading = ref(true)
const corrTypeFilter = ref<IntegratedCorrelation['type'] | 'all'>('all')
const selectedStageIdx = ref(0)

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
const miniNetEl = ref<HTMLElement | null>(null)

const selectedIds = computed(() => store.selectedCharacterIds)
const corrRows = computed(() => {
  const rows = sortedCorrelations(integrated.value)
  if (corrTypeFilter.value === 'all') return rows
  return rows.filter((c) => c.type === corrTypeFilter.value)
})
const stageSnapshots = computed(() => integrated.value?.stage_network_snapshots ?? [])
const activeSnapshot = computed(() => stageSnapshots.value[selectedStageIdx.value] ?? null)
const miniNetOpt = computed(() =>
  buildStageMiniNetwork(
    playText.value,
    network.value,
    activeSnapshot.value?.block_range ?? null,
    activeSnapshot.value?.stage,
  ),
)
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

function onCharTopicClick(params: unknown) {
  const p = params as { data?: [number, number, number] }
  if (!p.data || !integrated.value?.character_topic_matrix) return
  const [topicXi, charYi] = p.data
  const cells = integrated.value.character_topic_matrix
  const charOrder = [...new Set(cells.map((c) => c.character_name ?? c.character_id))]
  const topicOrder = [...new Set(cells.map((c) => c.topic_label ?? `T${c.topic_id}`))]
  const charName = charOrder[charYi]
  const topicName = topicOrder[topicXi]
  const cell = cells.find(
    (c) => (c.character_name ?? c.character_id) === charName
      && (c.topic_label ?? `T${c.topic_id}`) === topicName,
  )
  if (cell?.character_id) store.toggleCharacter(cell.character_id)
  if (cell?.topic_id != null) store.toggleTopic(cell.topic_id)
}

function goToTask(path: string) {
  router.push({ path, query: { script: store.scriptId ?? undefined } })
}

const corrPieChart = useChart(corrPieEl, () => corrPieOpt.value as EChartsOption, [corrPieOpt])
const corrBarChart = useChart(corrBarEl, () => corrBarOpt.value as EChartsOption, [corrBarOpt])
const charTopicHeatChart = useChart(
  charTopicHeatEl,
  () => charTopicHeatOpt.value as EChartsOption,
  [charTopicHeatOpt],
  { click: onCharTopicClick },
)
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
const miniNetChart = useChart(miniNetEl, () => miniNetOpt.value as EChartsOption, [miniNetOpt, selectedStageIdx])

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
  miniNetChart.render()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    const id = store.scriptId
    const [resIntegrated, resNetwork, resNarrative, resThemes, resPlay] = await Promise.all([
      api.playIntegrated(id).catch(() => null),
      api.playNetwork(id),
      api.playNarrative(id),
      api.playThemes(id),
      api.playCleaned(id).catch(() => null),
    ])
    integrated.value = resIntegrated
    network.value = resNetwork
    narrative.value = resNarrative
    themes.value = resThemes
    playText.value = resPlay
    selectedStageIdx.value = 0
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
        <ChartCard title="关联明细表" subtitle="可按类型筛选 · 点击跳转对应任务页">
          <div class="corr-filters">
            <button
              type="button"
              class="tab"
              :class="{ active: corrTypeFilter === 'all' }"
              @click="corrTypeFilter = 'all'"
            >全部</button>
            <button
              v-for="(label, type) in CORRELATION_TYPE_LABELS"
              :key="type"
              type="button"
              class="tab"
              :class="{ active: corrTypeFilter === type }"
              @click="corrTypeFilter = type as IntegratedCorrelation['type']"
            >{{ label }}</button>
          </div>
          <table class="corr-table">
            <thead>
              <tr><th>类型</th><th>描述</th><th>强度</th><th>依据</th><th>跳转</th></tr>
            </thead>
            <tbody>
              <tr v-for="(c, i) in corrRows.slice(0, 20)" :key="i">
                <td>{{ CORRELATION_TYPE_LABELS[c.type] }}</td>
                <td>{{ correlationLabel(c) }}</td>
                <td>{{ c.strength.toFixed(3) }}</td>
                <td class="evidence">{{ c.evidence ?? '—' }}</td>
                <td>
                  <button
                    v-if="c.type === 'character_theme' || c.type === 'character_network'"
                    type="button"
                    class="link-btn"
                    @click="goToTask('/role')"
                  >行当</button>
                  <button
                    v-if="c.type === 'network_stage' || c.type === 'character_network'"
                    type="button"
                    class="link-btn"
                    @click="goToTask('/network')"
                  >网络</button>
                  <button
                    v-if="c.type === 'character_theme' || c.type === 'theme_narrative'"
                    type="button"
                    class="link-btn"
                    @click="goToTask('/theme')"
                  >主题</button>
                  <button
                    v-if="c.type === 'hangdang_narrative' || c.type === 'theme_narrative' || c.type === 'network_stage'"
                    type="button"
                    class="link-btn"
                    @click="goToTask('/narrative')"
                  >叙事</button>
                </td>
              </tr>
            </tbody>
          </table>
        </ChartCard>
      </section>

      <section class="section">
        <h3 class="section-title">人物 ↔ 主题</h3>
        <div class="grid-2">
          <ChartCard title="人物×主题热力图" subtitle="点击单元格同时高亮人物与主题">
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
        <div v-if="stageSnapshots.length" class="stage-tabs">
          <button
            v-for="(snap, i) in stageSnapshots"
            :key="snap.stage"
            type="button"
            class="tab"
            :class="{ active: selectedStageIdx === i }"
            @click="selectedStageIdx = i"
          >
            {{ snap.stage }}（{{ snap.node_count }}人）
          </button>
        </div>
        <ChartCard title="阶段迷你子网络" subtitle="该阶段出场人物的同场关系（环形布局）">
          <div ref="miniNetEl" class="chart chart-md" />
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
.corr-filters, .stage-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.65rem;
}
.tab {
  padding: 0.28rem 0.55rem;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface);
  cursor: pointer;
  font-size: 0.75rem;
}
.tab.active { background: var(--accent-gold); font-weight: 600; }
.corr-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.corr-table th, .corr-table td { padding: 0.45rem; border-bottom: 1px solid var(--border); text-align: left; }
.evidence { font-size: 0.75rem; color: var(--text-muted); max-width: 220px; }
.link-btn {
  margin-right: 0.25rem;
  padding: 0.1rem 0.35rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: #fff8ee;
  font-size: 0.7rem;
  cursor: pointer;
}

@media (max-width: 900px) {
  .grid-2 { grid-template-columns: 1fr; }
  .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
