<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import SectionTabs from '@/components/SectionTabs.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import { hangdangColor } from '@/utils/charts'
import {
  buildAdjacencyHeatmap,
  buildCentralityRadar,
  buildCentralityScatter,
  buildForceGraph,
  buildHangdangNodePie,
  buildMainVsSupportPie,
  buildMetricsBar,
  buildRelationTypePie,
  buildWeightHistogram,
  buildWeightedDegreeBar,
} from '@/utils/networkCharts'
import { buildStageSubgraph } from '@/utils/stageNetwork'
import type { EChartsOption } from 'echarts'
import type { PlayCleaned, PlayNetwork } from '@/types'

const store = useFilterStore()
const net = ref<PlayNetwork | null>(null)
const playText = ref<PlayCleaned | null>(null)
const loading = ref(true)
const section = ref('topology')

const sectionTabs = [
  { id: 'topology', label: '关系图' },
  { id: 'core', label: '核心人物' },
  { id: 'structure', label: '结构组成' },
  { id: 'interaction', label: '互动强度' },
  { id: 'detail', label: '节点明细' },
]

function onSectionChange() {
  void nextTick(() => refreshCharts())
}

const graphEl = ref<HTMLElement | null>(null)
const degreeEl = ref<HTMLElement | null>(null)
const radarEl = ref<HTMLElement | null>(null)
const metricsEl = ref<HTMLElement | null>(null)
const hangdangEl = ref<HTMLElement | null>(null)
const mainEl = ref<HTMLElement | null>(null)
const relationEl = ref<HTMLElement | null>(null)
const weightEl = ref<HTMLElement | null>(null)
const heatEl = ref<HTMLElement | null>(null)
const scatterEl = ref<HTMLElement | null>(null)

const selectedIds = computed(() => store.selectedCharacterIds)
const blockRange = computed(() => store.narrativeBlockRange)

const graphSubset = computed(() => {
  if (!net.value || !playText.value || !blockRange.value) return null
  return buildStageSubgraph(playText.value, net.value, blockRange.value)
})

const graphOpt = computed(() =>
  net.value
    ? buildForceGraph(net.value, selectedIds.value, graphSubset.value ?? undefined)
    : ({} as EChartsOption),
)
const degreeOpt = computed(() => buildWeightedDegreeBar(net.value?.nodes ?? []))
const radarOpt = computed(() => buildCentralityRadar(net.value?.nodes ?? []))
const metricsOpt = computed(() =>
  net.value ? buildMetricsBar(net.value.metrics) : ({} as EChartsOption),
)
const hangdangOpt = computed(() => buildHangdangNodePie(net.value?.nodes ?? []))
const mainOpt = computed(() => buildMainVsSupportPie(net.value?.nodes ?? []))
const relationOpt = computed(() => buildRelationTypePie(net.value?.links ?? []))
const weightOpt = computed(() => buildWeightHistogram(net.value?.links ?? []))
const heatOpt = computed(() =>
  net.value ? buildAdjacencyHeatmap(net.value) : ({} as EChartsOption),
)
const scatterOpt = computed(() => buildCentralityScatter(net.value?.nodes ?? []))

function onGraphClick(params: unknown) {
  const p = params as { dataType?: string; data?: { id?: string } }
  if (p.dataType === 'node' && p.data?.id) store.toggleCharacter(p.data.id)
}

const graphChart = useChart(
  graphEl,
  () => graphOpt.value as EChartsOption,
  [graphOpt, selectedIds],
  { click: onGraphClick },
)
const degreeChart = useChart(degreeEl, () => degreeOpt.value as EChartsOption, [degreeOpt])
const radarChart = useChart(radarEl, () => radarOpt.value as EChartsOption, [radarOpt])
const metricsChart = useChart(metricsEl, () => metricsOpt.value as EChartsOption, [metricsOpt])
const hangdangChart = useChart(hangdangEl, () => hangdangOpt.value as EChartsOption, [hangdangOpt])
const mainChart = useChart(mainEl, () => mainOpt.value as EChartsOption, [mainOpt])
const relationChart = useChart(relationEl, () => relationOpt.value as EChartsOption, [relationOpt])
const weightChart = useChart(weightEl, () => weightOpt.value as EChartsOption, [weightOpt])
const heatChart = useChart(heatEl, () => heatOpt.value as EChartsOption, [heatOpt])
const scatterChart = useChart(scatterEl, () => scatterOpt.value as EChartsOption, [scatterOpt])

function refreshCharts() {
  graphChart.render()
  degreeChart.render()
  radarChart.render()
  metricsChart.render()
  hangdangChart.render()
  mainChart.render()
  relationChart.render()
  weightChart.render()
  heatChart.render()
  scatterChart.render()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    const id = store.scriptId
    net.value = await api.playNetwork(id)
    try {
      playText.value = await api.playCleaned(id)
    } catch {
      playText.value = null
    }
  } finally {
    loading.value = false
    await nextTick()
    refreshCharts()
  }
}

onMounted(load)
watch(() => store.scriptId, load)
watch(blockRange, () => graphChart.render())
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h2 class="page-title">人物关系网络</h2>
      <p class="page-desc">
        {{ net?.title ?? '' }}
        <template v-if="net?.genre"> · {{ net.genre }}</template>
        · 点击节点高亮人物
        <template v-if="blockRange"> · 叙事块 {{ blockRange[0] }}–{{ blockRange[1] }} 子网络</template>
      </p>
    </header>

    <div v-if="loading" class="loading">加载中…</div>
    <template v-else-if="net">
      <section class="kpi-row">
        <div class="kpi"><span class="num">{{ net.metrics.node_count }}</span><span class="lbl">节点</span></div>
        <div class="kpi"><span class="num">{{ net.metrics.edge_count }}</span><span class="lbl">边</span></div>
        <div class="kpi"><span class="num">{{ net.metrics.density.toFixed(3) }}</span><span class="lbl">密度</span></div>
        <div class="kpi"><span class="num">{{ (net.metrics.avg_clustering ?? 0).toFixed(3) }}</span><span class="lbl">聚类系数</span></div>
        <div class="kpi"><span class="num">{{ (net.metrics.modularity ?? 0).toFixed(3) }}</span><span class="lbl">模块度</span></div>
        <div class="kpi"><span class="num">{{ net.metrics.component_count ?? 1 }}</span><span class="lbl">连通分量</span></div>
      </section>

      <SectionTabs v-model="section" :tabs="sectionTabs" @change="onSectionChange" />

      <div v-show="section === 'topology'" class="tab-panel section">
        <ChartCard title="力导向关系图" subtitle="红=对话+同场 · 金=对话 · 蓝虚线=同场 · 叙事页选阶段可滤子网">
          <div ref="graphEl" class="chart chart-tall" />
        </ChartCard>
      </div>

      <div v-show="section === 'core'" class="tab-panel section">
        <div class="grid-3">
          <ChartCard title="加权度排名" subtitle="互动最频繁的人物">
            <div ref="degreeEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="中心性雷达" subtitle="Top5 人物：度/介数/接近/特征向量">
            <div ref="radarEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="度 × 介数散点" subtitle="气泡大小=加权度 · 识别桥接角色">
            <div ref="scatterEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </div>

      <div v-show="section === 'structure'" class="tab-panel section">
        <div class="grid-4">
          <ChartCard title="网络指标" subtitle="密度、聚类、模块度等">
            <div ref="metricsEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="节点行当" subtitle="网络中各行当人数">
            <div ref="hangdangEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="主配角" subtitle="is_main 标记">
            <div ref="mainEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="关系类型" subtitle="对话 / 同场 / 兼有">
            <div ref="relationEl" class="chart chart-sm" />
          </ChartCard>
        </div>
      </div>

      <div v-show="section === 'interaction'" class="tab-panel section">
        <div class="grid-wide">
          <ChartCard title="边权分布" subtitle="关系强度直方图">
            <div ref="weightEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="人物互动矩阵" subtitle="Top10 人物两两关系热力图">
            <div ref="heatEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </div>

      <div v-show="section === 'detail'" class="tab-panel">
        <ChartCard title="节点明细" subtitle="点击行与力导向图联动高亮">
          <table class="table">
            <thead>
              <tr>
                <th>姓名</th><th>行当</th><th>度</th><th>加权度</th>
                <th>介数</th><th>接近</th><th>社区</th><th>主要</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="n in [...net.nodes].sort((a, b) => (b.weighted_degree ?? 0) - (a.weighted_degree ?? 0))"
                :key="n.id"
                :class="{ hl: selectedIds.includes(n.id) }"
                @click="store.toggleCharacter(n.id)"
              >
                <td>{{ n.name }}</td>
                <td>
                  <span class="tag" :style="{ background: hangdangColor(n.hangdang) }">{{ n.hangdang }}</span>
                </td>
                <td>{{ n.degree }}</td>
                <td>{{ (n.weighted_degree ?? 0).toFixed(1) }}</td>
                <td>{{ (n.betweenness ?? 0).toFixed(3) }}</td>
                <td>{{ (n.closeness ?? 0).toFixed(3) }}</td>
                <td>{{ n.community_id ?? '—' }}</td>
                <td>{{ n.is_main ? '是' : '—' }}</td>
              </tr>
            </tbody>
          </table>
        </ChartCard>
      </div>
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
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 0.65rem;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
  text-align: center;
}
.kpi .num { display: block; font-size: 1.25rem; font-weight: 700; color: var(--accent-red); }
.kpi .lbl { font-size: 0.72rem; color: var(--text-muted); }

.section-title {
  margin: 0 0 0.65rem;
  font-family: var(--font-serif);
  font-size: 1.05rem;
}
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}
.grid-4 {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}
.grid-wide {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}
.chart { width: 100%; display: block; }
.chart-tall { height: 400px; }
.chart-md { height: 300px; }
.chart-sm { height: 260px; }

.table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
th, td { padding: 0.5rem; border-bottom: 1px solid var(--border); text-align: left; }
tr { cursor: pointer; transition: background 0.12s; }
tr.hl, tr:hover { background: #fff8e8; }
.tag { color: #fff; padding: 0.12rem 0.45rem; border-radius: 4px; font-size: 0.78rem; }
.tab-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.65rem; }
.tab {
  padding: 0.3rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  cursor: pointer;
  font-size: 0.78rem;
}
.tab.active { background: var(--accent-gold); border-color: var(--accent-gold); font-weight: 600; }

@media (max-width: 1100px) {
  .grid-4 { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .grid-3, .grid-wide { grid-template-columns: 1fr; }
}
</style>
