<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  buildEmotionTimeline,
  buildGlobalStageCompare,
  buildPerformancePie,
  buildPerformanceStacked,
  buildRhythmLine,
  buildStageProportionPie,
  buildStageRadar,
  rangesEqual,
  stageColor,
} from '@/utils/narrativeCharts'
import type { EChartsOption } from 'echarts'
import type { NarrativeTemplatesGlobal, PlayNarrative } from '@/types'

const store = useFilterStore()
const narrative = ref<PlayNarrative | null>(null)
const globalNarr = ref<NarrativeTemplatesGlobal | null>(null)
const loading = ref(true)
const selectedStage = ref<string | null>(null)

const rhythmEl = ref<HTMLElement | null>(null)
const stagePieEl = ref<HTMLElement | null>(null)
const perfStackEl = ref<HTMLElement | null>(null)
const perfPieEl = ref<HTMLElement | null>(null)
const radarEl = ref<HTMLElement | null>(null)
const emotionEl = ref<HTMLElement | null>(null)
const compareEl = ref<HTMLElement | null>(null)

const selectedRange = computed(() => store.narrativeBlockRange)

const rhythmOpt = computed(() =>
  narrative.value
    ? buildRhythmLine(narrative.value, selectedRange.value, selectedStage.value)
    : ({} as EChartsOption),
)
const stagePieOpt = computed(() =>
  buildStageProportionPie(narrative.value?.plot_stages ?? []),
)
const perfStackOpt = computed(() =>
  buildPerformanceStacked(narrative.value?.performance_by_stage),
)
const perfPieOpt = computed(() =>
  buildPerformancePie(narrative.value?.performance_mark_distribution ?? {}),
)
const radarOpt = computed(() =>
  narrative.value
    ? buildStageRadar(narrative.value, selectedStage.value)
    : ({} as EChartsOption),
)
const emotionOpt = computed(() =>
  buildEmotionTimeline(narrative.value?.block_annotations, selectedRange.value),
)
const compareOpt = computed(() =>
  narrative.value
    ? buildGlobalStageCompare(narrative.value, globalNarr.value)
    : ({} as EChartsOption),
)

const rhythmChart = useChart(rhythmEl, () => rhythmOpt.value as EChartsOption, [rhythmOpt, selectedRange, selectedStage])
const stagePieChart = useChart(stagePieEl, () => stagePieOpt.value as EChartsOption, [stagePieOpt])
const perfStackChart = useChart(perfStackEl, () => perfStackOpt.value as EChartsOption, [perfStackOpt])
const perfPieChart = useChart(perfPieEl, () => perfPieOpt.value as EChartsOption, [perfPieOpt])
const radarChart = useChart(radarEl, () => radarOpt.value as EChartsOption, [radarOpt, selectedStage])
const emotionChart = useChart(emotionEl, () => emotionOpt.value as EChartsOption, [emotionOpt, selectedRange])
const compareChart = useChart(compareEl, () => compareOpt.value as EChartsOption, [compareOpt])

function refreshCharts() {
  rhythmChart.render()
  stagePieChart.render()
  perfStackChart.render()
  perfPieChart.render()
  radarChart.render()
  emotionChart.render()
  compareChart.render()
}

function isStageActive(st: PlayNarrative['plot_stages'][number]) {
  return selectedStage.value === st.stage && rangesEqual(selectedRange.value, st.block_range)
}

function pickStage(st: PlayNarrative['plot_stages'][number]) {
  if (isStageActive(st)) {
    selectedStage.value = null
    store.narrativeBlockRange = null
  } else {
    selectedStage.value = st.stage
    store.narrativeBlockRange = [st.block_range[0], st.block_range[1]]
  }
  refreshCharts()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  selectedStage.value = null
  store.narrativeBlockRange = null
  try {
    narrative.value = await api.playNarrative(store.scriptId)
    try {
      globalNarr.value = await api.globalNarrative()
    } catch {
      globalNarr.value = null
    }
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
      <h2 class="page-title">叙事结构</h2>
      <p class="page-desc">
        {{ narrative?.title ?? '' }} · 点击情节阶段按钮，节奏曲线与情感散点将高亮对应区间
      </p>
    </header>

    <div v-if="loading" class="loading">加载中…</div>
    <template v-else-if="narrative">
      <section class="stages-wrap">
        <h3 class="section-title">情节阶段</h3>
        <div class="stages">
          <button
            v-for="st in narrative.plot_stages"
            :key="`${st.stage}-${st.block_range[0]}`"
            type="button"
            class="stage-btn"
            :class="{ active: isStageActive(st) }"
            :style="{
              borderLeftColor: stageColor(st.stage),
              '--stage-color': stageColor(st.stage),
            }"
            @click="pickStage(st)"
          >
            <strong>{{ st.stage }}</strong>
            <span class="lbl">{{ st.label }}</span>
            <small>块 {{ st.block_range[0] }}–{{ st.block_range[1] }}</small>
            <p v-if="st.summary" class="summary">{{ st.summary }}</p>
          </button>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">节奏与情感</h3>
        <ChartCard
          title="叙事节奏曲线"
          :subtitle="selectedStage ? `已高亮：${selectedStage}（块 ${selectedRange?.[0]}–${selectedRange?.[1]}）` : '点击上方阶段按钮高亮区间'"
        >
          <div ref="rhythmEl" class="chart chart-tall" />
        </ChartCard>
        <div class="grid-2">
          <ChartCard title="块级情感散点" subtitle="颜色=情感强度 · 选中阶段区间高亮">
            <div ref="emotionEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="阶段节奏雷达" subtitle="五阶段对白/唱/动作/情感/张力均值">
            <div ref="radarEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">阶段与表演</h3>
        <div class="grid-3">
          <ChartCard title="阶段篇幅" subtitle="各情节阶段占全文块比例">
            <div ref="stagePieEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="分阶段唱念做打" subtitle="各阶段表演标记堆叠">
            <div ref="perfStackEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="全剧表演构成" subtitle="唱念做打总体分布">
            <div ref="perfPieEl" class="chart chart-md" />
          </ChartCard>
        </div>
        <ChartCard title="本剧 vs 全库阶段占比" subtitle="与「起承转合型」模板均值对比">
          <div ref="compareEl" class="chart chart-sm" />
        </ChartCard>
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

.stages {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.6rem;
}
.stage-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  font-size: 0.8rem;
  text-align: left;
  font-family: inherit;
  transition: background 0.15s, box-shadow 0.15s, border-color 0.15s;
}
.stage-btn:hover { background: #fffaf3; }
.stage-btn.active {
  border-color: var(--stage-color, var(--accent-red));
  background: color-mix(in srgb, var(--stage-color, #8b2500) 12%, #fff8ee);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--stage-color, #8b2500) 25%, transparent);
}
.stage-btn strong { font-size: 0.95rem; color: var(--text); }
.lbl { color: var(--text-muted); font-size: 0.78rem; }
.stage-btn small { color: var(--text-muted); font-size: 0.72rem; }
.summary {
  margin: 0.25rem 0 0;
  font-size: 0.72rem;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
  margin-top: 0.85rem;
}
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}
.chart { width: 100%; display: block; }
.chart-tall { height: 380px; }
.chart-md { height: 300px; }
.chart-sm { height: 260px; }

@media (max-width: 1100px) { .grid-3 { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
