<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  buildCharacterTopicHeatmap,
  buildMiniStageGraph,
  buildTensionDensityOverlay,
  CORRELATION_TYPE_LABELS,
  pivotCharacterTopicMatrix,
} from '@/utils/integratedCharts'
import { buildStageSubgraph } from '@/utils/stageNetwork'
import type { EChartsOption } from 'echarts'
import type { IntegratedCorrelation, PlayCleaned, PlayIntegrated, PlayNarrative, PlayNetwork } from '@/types'

const store = useFilterStore()
const router = useRouter()

const integrated = ref<PlayIntegrated | null>(null)
const narrative = ref<PlayNarrative | null>(null)
const network = ref<PlayNetwork | null>(null)
const playText = ref<PlayCleaned | null>(null)
const loading = ref(true)
const corrFilter = ref<string>('all')
const stageTab = ref(0)

const heatEl = ref<HTMLElement | null>(null)
const overlayEl = ref<HTMLElement | null>(null)
const miniNetEl = ref<HTMLElement | null>(null)

const snapshots = computed(() => integrated.value?.stage_network_snapshots ?? [])
const activeSnapshot = computed(() => snapshots.value[stageTab.value] ?? null)

const miniSubset = computed(() => {
  if (!network.value || !playText.value || !activeSnapshot.value) return null
  return buildStageSubgraph(playText.value, network.value, activeSnapshot.value.block_range)
})

const kpis = computed(() => {
  const m = network.value?.metrics
  const stages = snapshots.value.length
  return [
    { label: '主要人物', value: m?.node_count ?? '—' },
    { label: '关系边', value: m?.edge_count ?? '—' },
    { label: '网络密度', value: m ? m.density.toFixed(2) : '—' },
    { label: '叙事阶段', value: stages || '—' },
    { label: '关联规则', value: integrated.value?.correlations?.length ?? 0 },
  ]
})

const filteredCorrelations = computed(() => {
  const list = integrated.value?.correlations ?? []
  if (corrFilter.value === 'all') return list
  return list.filter((c) => c.type === corrFilter.value)
})

const selectedCharacterIds = computed(() => store.selectedCharacterIds)
const selectedTopicIds = computed(() => store.selectedTopicIds)

const heatOpt = computed(() =>
  buildCharacterTopicHeatmap(integrated.value?.character_topic_matrix ?? []),
)

const overlayOpt = computed(() =>
  narrative.value && snapshots.value.length
    ? buildTensionDensityOverlay(narrative.value, snapshots.value)
    : ({} as EChartsOption),
)

const miniNetOpt = computed(() =>
  network.value && miniSubset.value
    ? buildMiniStageGraph(network.value, miniSubset.value.nodes, miniSubset.value.links, selectedCharacterIds.value)
    : ({} as EChartsOption),
)

function onHeatClick(params: unknown) {
  const p = params as { data?: [number, number, number] }
  const matrix = integrated.value?.character_topic_matrix ?? []
  if (!p.data) return
  const { chars, topics } = pivotCharacterTopicMatrix(matrix)
  const cid = chars[p.data[1]]?.[0]
  const tid = topics[p.data[0]]?.[0]
  if (cid) store.selectedCharacterIds = [cid]
  if (tid != null) store.selectedTopicIds = [tid]
}

function onMiniGraphClick(params: unknown) {
  const p = params as { dataType?: string; data?: { id?: string } }
  if (p.dataType === 'node' && p.data?.id) store.toggleCharacter(p.data.id)
}

const heatChart = useChart(heatEl, () => heatOpt.value as EChartsOption, [heatOpt, selectedCharacterIds, selectedTopicIds], { click: onHeatClick })
const overlayChart = useChart(overlayEl, () => overlayOpt.value as EChartsOption, [overlayOpt])
const miniNetChart = useChart(miniNetEl, () => miniNetOpt.value as EChartsOption, [miniNetOpt, selectedCharacterIds], { click: onMiniGraphClick })

function refreshCharts() {
  heatChart.render()
  overlayChart.render()
  miniNetChart.render()
}

function corrSummary(c: IntegratedCorrelation): string {
  const parts = [
    c.character_name,
    c.topic_label,
    c.stage,
    c.hangdang,
  ].filter(Boolean)
  return parts.join(' · ') || c.type
}

function jumpCorrelation(c: IntegratedCorrelation) {
  if (c.character_id) store.selectedCharacterIds = [c.character_id]
  if (c.topic_id != null) store.selectedTopicIds = [c.topic_id]

  if (c.type === 'network_stage' || c.type === 'theme_narrative') {
    const snap = snapshots.value.find((s) => s.stage === c.stage)
    if (snap) {
      store.setNarrativeBlockRange(snap.block_range)
      stageTab.value = snapshots.value.indexOf(snap)
    }
    router.push({ path: '/network', query: { script: store.scriptId ?? undefined } })
    return
  }
  if (c.type === 'character_theme' || c.type === 'character_network') {
    router.push({ path: '/role', query: { script: store.scriptId ?? undefined } })
    return
  }
  if (c.type === 'hangdang_narrative' && c.peak_block_index != null) {
    store.setNarrativeBlockRange([c.peak_block_index, c.peak_block_index + 20])
    router.push({ path: '/narrative', query: { script: store.scriptId ?? undefined } })
  }
}

function pickStage(idx: number) {
  stageTab.value = idx
  const snap = snapshots.value[idx]
  if (snap) store.setNarrativeBlockRange(snap.block_range)
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    const id = store.scriptId
    const [intg, narr, net] = await Promise.all([
      api.playIntegrated(id),
      api.playNarrative(id),
      api.playNetwork(id),
    ])
    integrated.value = intg
    narrative.value = narr
    network.value = net
    try {
      playText.value = await api.playCleaned(id)
    } catch {
      playText.value = null
    }
    stageTab.value = 0
    if (snapshots.value[0]) {
      store.setNarrativeBlockRange(snapshots.value[0].block_range)
    }
  } catch (e) {
    integrated.value = null
    narrative.value = null
    network.value = null
    console.error(e)
  } finally {
    loading.value = false
    await nextTick()
    refreshCharts()
  }
}

onMounted(load)
watch(() => store.scriptId, load)
watch(stageTab, () => {
  void nextTick(refreshCharts)
})
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h2 class="page-title">综合探索</h2>
      <p class="page-desc">
        {{ integrated?.title ?? '' }}
        · 人物、主题、叙事跨维关联 · 点击热力格或关联行可联动其他页面
      </p>
    </header>

    <div v-if="loading" class="loading">加载中…</div>
    <div v-else-if="!integrated" class="loading">暂无综合关联数据，请先运行 analytics integrated</div>
    <template v-else>
      <section class="kpi-row">
        <div v-for="k in kpis" :key="k.label" class="kpi">
          <span class="num">{{ k.value }}</span>
          <span class="lbl">{{ k.label }}</span>
        </div>
      </section>

      <section class="insights">
        <h3 class="section-title">自动洞察</h3>
        <ul class="insight-list">
          <li v-for="(line, i) in integrated.summary_insights" :key="i">{{ line }}</li>
        </ul>
      </section>

      <div class="grid-2">
        <ChartCard title="人物 × 主题关联" subtitle="点击单元格选中人物与主题，可跳转行当页">
          <div ref="heatEl" class="chart chart-md" />
        </ChartCard>

        <ChartCard title="张力 × 网络密度" subtitle="各叙事阶段：节奏张力（线）与同场网络密度（柱）是否同步">
          <div ref="overlayEl" class="chart chart-md" />
        </ChartCard>
      </div>

      <div class="grid-2">
        <ChartCard title="阶段子网络" subtitle="切换阶段查看该块区间内出场人物的迷你关系图">
          <div class="stage-tabs">
            <button
              v-for="(snap, i) in snapshots"
              :key="snap.stage"
              type="button"
              class="stage-tab"
              :class="{ active: stageTab === i }"
              @click="pickStage(i)"
            >
              {{ snap.stage }}
              <span class="meta">密度 {{ snap.edge_density.toFixed(2) }}</span>
            </button>
          </div>
          <p v-if="activeSnapshot" class="stage-hint">
            块 {{ activeSnapshot.block_range[0] }}–{{ activeSnapshot.block_range[1] }}
            · {{ activeSnapshot.node_count }} 人 · {{ activeSnapshot.edge_count ?? 0 }} 边
          </p>
          <div ref="miniNetEl" class="chart chart-sm" />
        </ChartCard>

        <ChartCard title="关联规则明细" subtitle="筛选类型 · 点击「跳转」联动叙事/网络/行当页">
          <div class="corr-filter">
            <button
              type="button"
              class="filter-btn"
              :class="{ active: corrFilter === 'all' }"
              @click="corrFilter = 'all'"
            >
              全部
            </button>
            <button
              v-for="(label, key) in CORRELATION_TYPE_LABELS"
              :key="key"
              type="button"
              class="filter-btn"
              :class="{ active: corrFilter === key }"
              @click="corrFilter = key"
            >
              {{ label }}
            </button>
          </div>
          <div class="corr-table-wrap">
            <table class="corr-table">
              <thead>
                <tr>
                  <th>类型</th>
                  <th>对象</th>
                  <th>强度</th>
                  <th>依据</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                <tr v-for="(c, i) in filteredCorrelations" :key="i">
                  <td>{{ CORRELATION_TYPE_LABELS[c.type] ?? c.type }}</td>
                  <td>{{ corrSummary(c) }}</td>
                  <td>{{ c.strength.toFixed(2) }}</td>
                  <td class="evidence">{{ c.evidence }}</td>
                  <td>
                    <button type="button" class="link-btn" @click="jumpCorrelation(c)">跳转</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </ChartCard>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 1rem;
}
.page-title {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 1.35rem;
}
.page-desc {
  margin: 0.35rem 0 0;
  font-size: 0.88rem;
  color: var(--text-muted);
}
.loading {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
.kpi-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.kpi {
  flex: 1;
  min-width: 88px;
  padding: 0.65rem 0.85rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  text-align: center;
}
.kpi .num {
  display: block;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--accent-red);
}
.kpi .lbl {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.insights {
  margin-bottom: 1rem;
  padding: 0.85rem 1rem;
  background: #fff8e8;
  border: 1px solid var(--accent-gold);
  border-radius: 8px;
}
.section-title {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
  font-family: var(--font-serif);
}
.insight-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.88rem;
  line-height: 1.55;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
.chart {
  width: 100%;
}
.chart-md {
  height: 320px;
}
.chart-sm {
  height: 260px;
}
.stage-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  padding: 0 0.25rem 0.5rem;
}
.stage-tab {
  padding: 0.35rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  font-size: 0.78rem;
  cursor: pointer;
}
.stage-tab.active {
  border-color: var(--accent-gold);
  background: #fff8e8;
  font-weight: 600;
}
.stage-tab .meta {
  display: block;
  font-size: 0.68rem;
  color: var(--text-muted);
  font-weight: 400;
}
.stage-hint {
  margin: 0 0 0.25rem;
  padding: 0 0.25rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}
.corr-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-bottom: 0.5rem;
}
.filter-btn {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface);
  font-size: 0.72rem;
  cursor: pointer;
}
.filter-btn.active {
  background: var(--accent-gold);
  border-color: var(--accent-gold);
  color: #1a0f0a;
}
.corr-table-wrap {
  max-height: 280px;
  overflow: auto;
}
.corr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
}
.corr-table th,
.corr-table td {
  padding: 0.35rem 0.4rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
.corr-table th {
  position: sticky;
  top: 0;
  background: var(--surface);
  font-weight: 600;
}
.evidence {
  max-width: 180px;
  color: var(--text-muted);
  line-height: 1.35;
}
.link-btn {
  padding: 0.15rem 0.45rem;
  border: none;
  border-radius: 4px;
  background: var(--accent-red);
  color: #fff;
  font-size: 0.72rem;
  cursor: pointer;
}
</style>
