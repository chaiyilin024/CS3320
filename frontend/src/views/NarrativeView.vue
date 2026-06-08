<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import SectionTabs from '@/components/SectionTabs.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import {
  buildEmotionTimeline,
  buildGenreRhythmOverlay,
  buildGlobalStageCompare,
  buildPerformancePie,
  buildPerformanceStacked,
  buildRhythmLine,
  buildStageProportionPie,
  buildStageRadar,
  buildTemplateStageCompare,
  rangesEqual,
  stageColor,
} from '@/utils/narrativeCharts'
import { buildStageExcerpts, type StageExcerpt } from '@/utils/narrativeExcerpts'
import type { EChartsOption } from 'echarts'
import type { NarrativeTemplatesGlobal, PlayCleaned, PlayNarrative } from '@/types'

const store = useFilterStore()
const narrative = ref<PlayNarrative | null>(null)
const globalNarr = ref<NarrativeTemplatesGlobal | null>(null)
const playText = ref<PlayCleaned | null>(null)
const loading = ref(true)
const excerptsLoading = ref(false)
const selectedStage = ref<string | null>(null)
const stageExcerpts = ref<StageExcerpt[]>([])
const excerptTotal = ref(0)

const rhythmEl = ref<HTMLElement | null>(null)
const stagePieEl = ref<HTMLElement | null>(null)
const perfStackEl = ref<HTMLElement | null>(null)
const perfPieEl = ref<HTMLElement | null>(null)
const radarEl = ref<HTMLElement | null>(null)
const emotionEl = ref<HTMLElement | null>(null)
const compareEl = ref<HTMLElement | null>(null)
const templateEl = ref<HTMLElement | null>(null)
const genreRhythmEl = ref<HTMLElement | null>(null)
const selectedTemplateId = ref('classic_five_act')
const playGenre = ref<string | null>(null)
const section = ref('rhythm')

const sectionTabs = [
  { id: 'rhythm', label: '节奏情感' },
  { id: 'stage', label: '阶段表演' },
]

function onSectionChange() {
  void nextTick(() => refreshCharts())
}

const selectedRange = computed(() => store.narrativeBlockRange)
const selectedTopicIds = computed(() => store.selectedTopicIds)

const rhythmOpt = computed(() =>
  narrative.value
    ? buildRhythmLine(
        narrative.value,
        selectedRange.value,
        selectedStage.value,
        selectedTopicIds.value,
        true,
      )
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
const templateOpt = computed(() =>
  narrative.value
    ? buildTemplateStageCompare(narrative.value, globalNarr.value, selectedTemplateId.value)
    : ({} as EChartsOption),
)
const genreRhythmOpt = computed(() =>
  narrative.value
    ? buildGenreRhythmOverlay(narrative.value, globalNarr.value, playGenre.value)
    : ({} as EChartsOption),
)

function onRhythmDataZoom(params: unknown) {
  const p = params as { batch?: Array<{ startValue?: number; endValue?: number }> }
  const batch = p.batch?.[0]
  if (batch?.startValue != null && batch?.endValue != null) {
    const lo = Math.floor(batch.startValue)
    const hi = Math.ceil(batch.endValue)
    store.setNarrativeBlockRange([lo, hi])
  }
}

const rhythmChart = useChart(
  rhythmEl,
  () => rhythmOpt.value as EChartsOption,
  [rhythmOpt, selectedRange, selectedStage, selectedTopicIds],
  { datazoom: onRhythmDataZoom },
)
const stagePieChart = useChart(stagePieEl, () => stagePieOpt.value as EChartsOption, [stagePieOpt])
const perfStackChart = useChart(perfStackEl, () => perfStackOpt.value as EChartsOption, [perfStackOpt])
const perfPieChart = useChart(perfPieEl, () => perfPieOpt.value as EChartsOption, [perfPieOpt])
const radarChart = useChart(radarEl, () => radarOpt.value as EChartsOption, [radarOpt, selectedStage])
const emotionChart = useChart(emotionEl, () => emotionOpt.value as EChartsOption, [emotionOpt, selectedRange])
const compareChart = useChart(compareEl, () => compareOpt.value as EChartsOption, [compareOpt])
const templateChart = useChart(templateEl, () => templateOpt.value as EChartsOption, [templateOpt, selectedTemplateId])
const genreRhythmChart = useChart(genreRhythmEl, () => genreRhythmOpt.value as EChartsOption, [genreRhythmOpt])

function refreshCharts() {
  rhythmChart.render()
  stagePieChart.render()
  perfStackChart.render()
  perfPieChart.render()
  radarChart.render()
  emotionChart.render()
  compareChart.render()
  templateChart.render()
  genreRhythmChart.render()
}

function isStageActive(st: PlayNarrative['plot_stages'][number]) {
  return selectedStage.value === st.stage && rangesEqual(selectedRange.value, st.block_range)
}

async function ensurePlayText(id: string) {
  if (playText.value?.script_id === id) return playText.value
  playText.value = await api.playCleaned(id)
  return playText.value
}

async function loadStageExcerpts(st: PlayNarrative['plot_stages'][number] | null) {
  if (!st || !store.scriptId) {
    stageExcerpts.value = []
    excerptTotal.value = 0
    return
  }
  excerptsLoading.value = true
  try {
    const play = await ensurePlayText(store.scriptId)
    const { items, total } = buildStageExcerpts(play, st.block_range)
    stageExcerpts.value = items
    excerptTotal.value = total
  } catch {
    stageExcerpts.value = []
    excerptTotal.value = 0
  } finally {
    excerptsLoading.value = false
  }
}

async function pickStage(st: PlayNarrative['plot_stages'][number]) {
  if (isStageActive(st)) {
    selectedStage.value = null
    store.narrativeBlockRange = null
    stageExcerpts.value = []
    excerptTotal.value = 0
  } else {
    selectedStage.value = st.stage
    store.narrativeBlockRange = [st.block_range[0], st.block_range[1]]
    await loadStageExcerpts(st)
  }
  refreshCharts()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  selectedStage.value = null
  store.narrativeBlockRange = null
  stageExcerpts.value = []
  excerptTotal.value = 0
  playText.value = null
  try {
    const id = store.scriptId
    narrative.value = await api.playNarrative(id)
    try {
      const cat = await api.catalog()
      playGenre.value = cat.plays.find((p) => p.script_id === id)?.tags?.genre_inferred ?? null
    } catch {
      playGenre.value = null
    }
    try {
      globalNarr.value = await api.globalNarrative()
      if (!globalNarr.value?.templates.some((t) => t.template_id === selectedTemplateId.value)) {
        selectedTemplateId.value = globalNarr.value?.templates[0]?.template_id ?? 'classic_five_act'
      }
    } catch {
      globalNarr.value = null
    }
  } finally {
    loading.value = false
    await nextTick()
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
        {{ narrative?.title ?? '' }} · 拖动节奏图滑块框选块区间 · 主题页选主题可在此标记
        <template v-if="store.selectedTopicIds.length"> · 已选主题 {{ store.selectedTopicIds.join(',') }}</template>
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

      <section v-if="selectedStage" class="excerpt-section">
        <h3 class="section-title">
          「{{ selectedStage }}」原文片段
          <span v-if="excerptTotal" class="excerpt-count">
            （块 {{ selectedRange?.[0] }}–{{ selectedRange?.[1] }}，共 {{ excerptTotal }} 段
            <template v-if="excerptTotal > stageExcerpts.length">，展示前 {{ stageExcerpts.length }} 段</template>）
          </span>
        </h3>
        <div v-if="excerptsLoading" class="excerpt-loading">加载正文中…</div>
        <div v-else-if="!stageExcerpts.length" class="excerpt-loading">
          暂无正文数据，请先运行 <code>python scripts/sync_frontend_data.py</code> 或 <code>npm run sync-data</code> 同步 play.json
        </div>
        <ul v-else class="snippets">
          <li
            v-for="ex in stageExcerpts"
            :key="ex.block_index"
            :style="{ borderLeftColor: stageColor(selectedStage) }"
          >
            <span class="meta">
              块 #{{ ex.block_index }} · {{ ex.typeLabel }}
              <template v-if="ex.speaker"> · {{ ex.speaker }}</template>
            </span>
            {{ ex.text }}
          </li>
        </ul>
      </section>

      <SectionTabs v-model="section" :tabs="sectionTabs" @change="onSectionChange" />

      <div v-show="section === 'rhythm'" class="tab-panel section">
        <ChartCard
          title="叙事节奏曲线"
          :subtitle="selectedRange ? `块 ${selectedRange[0]}–${selectedRange[1]}` : '拖动底部滑块或点击阶段按钮'"
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
      </div>

      <div v-show="section === 'stage'" class="tab-panel section">
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
        <div v-if="globalNarr?.templates.length" class="template-tabs">
          <button
            v-for="tpl in globalNarr.templates"
            :key="tpl.template_id"
            type="button"
            class="tab"
            :class="{ active: selectedTemplateId === tpl.template_id }"
            @click="selectedTemplateId = tpl.template_id"
          >
            {{ tpl.label }}（{{ tpl.play_count }}）
          </button>
        </div>
        <div class="grid-2 section-gap">
          <ChartCard title="叙事模板对比" subtitle="本剧 vs 所选模板阶段占比">
            <div ref="templateEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="体裁节奏对比" :subtitle="`${playGenre ?? '体裁'}平均张力曲线 vs 本剧`">
            <div ref="genreRhythmEl" class="chart chart-sm" />
          </ChartCard>
        </div>
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

.section-title {
  margin: 0 0 0.65rem;
  font-family: var(--font-serif);
  font-size: 1.05rem;
}
.section-hint {
  margin: -0.35rem 0 0.65rem;
  font-size: 0.8rem;
  color: var(--text-muted);
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

.excerpt-section {
  padding: 0.85rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
}
.excerpt-count {
  font-size: 0.78rem;
  font-weight: normal;
  color: var(--text-muted);
}
.excerpt-loading {
  color: var(--text-muted);
  font-size: 0.88rem;
  padding: 0.5rem 0;
}
.excerpt-loading code {
  font-size: 0.8rem;
  background: #f5f0e8;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
}
.snippets { margin: 0; padding: 0; list-style: none; font-size: 0.86rem; line-height: 1.55; max-height: 420px; overflow-y: auto; }
.snippets li {
  padding: 0.55rem 0.65rem 0.55rem 0.75rem;
  margin-bottom: 0.4rem;
  border-left: 3px solid #ccc;
  background: #fdfaf5;
  border-radius: 0 6px 6px 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.meta { display: block; font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem; }

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

.template-tabs { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.65rem 0; }
.tab {
  padding: 0.3rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  cursor: pointer;
  font-size: 0.78rem;
}
.tab.active { background: var(--accent-gold); font-weight: 600; }
.section-gap { margin-top: 0.85rem; }

@media (max-width: 1100px) { .grid-3 { grid-template-columns: 1fr; } }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
