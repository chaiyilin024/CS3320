<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import { filterCatalogPlays } from '@/utils/catalogFilter'
import { aggregateCatalog, filterPlays } from '@/utils/dashboardStats'
import { genreColor } from '@/utils/charts'
import { asChartOption } from '@/utils/chartOption'
import type { EChartsOption } from 'echarts'
import type { CatalogPlay } from '@/types'

const store = useFilterStore()
const plays = ref<CatalogPlay[]>([])
const loading = ref(true)
const search = ref('')

const genreEl = ref<HTMLElement | null>(null)
const collectionEl = ref<HTMLElement | null>(null)
const eraEl = ref<HTMLElement | null>(null)
const scatterEl = ref<HTMLElement | null>(null)
const blockEl = ref<HTMLElement | null>(null)
const qualityEl = ref<HTMLElement | null>(null)

const filteredCatalog = computed(() =>
  filterCatalogPlays(plays.value, {
    genre: store.genre,
    collectionId: store.collectionId,
  }),
)

const stats = computed(() => aggregateCatalog(filteredCatalog.value))

const currentPlay = computed(() =>
  plays.value.find((p) => p.script_id === store.scriptId) ?? null,
)

const searchResults = computed(() => filterPlays(plays.value, search.value))

const tasks = [
  { path: '/role', title: '人物与行当', desc: '特征推断、行当分布' },
  { path: '/network', title: '人物关系网络', desc: '力导向图、网络指标' },
  { path: '/theme', title: '主题分析', desc: '主题构成、关键词、热力图' },
  { path: '/narrative', title: '叙事结构', desc: '情节阶段、节奏曲线' },
  { path: '/integrated', title: '综合探索', desc: '跨维度关联与洞察' },
]

function selectPlay(id: string) {
  store.setScriptId(id)
}

function onScatterClick(params: unknown) {
  const data = (params as { data?: { script_id?: string } })?.data
  if (data?.script_id) selectPlay(data.script_id)
}

const genreOpt = computed(() => ({
  color: stats.value.genres.map((g) => genreColor(g.name)),
  tooltip: { trigger: 'item', formatter: '{b}<br/>{c} 部 ({d}%)' },
  legend: {
    type: 'scroll',
    orient: 'vertical',
    right: 0,
    top: 'middle',
    textStyle: { fontSize: 11 },
  },
  series: [{
    type: 'pie',
    radius: ['42%', '68%'],
    center: ['38%', '50%'],
    avoidLabelOverlap: true,
    itemStyle: { borderRadius: 6, borderColor: '#fffcf7', borderWidth: 2 },
    label: { show: false },
    emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
    data: stats.value.genres.map((g) => ({ name: g.name, value: g.value })),
  }],
}))

const collectionOpt = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} 部' },
  series: [{
    type: 'treemap',
    roam: false,
    nodeClick: false,
    breadcrumb: { show: false },
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    label: { show: true, formatter: '{b}', fontSize: 11 },
    upperLabel: { show: true, height: 24 },
    itemStyle: { borderColor: '#fffcf7', borderWidth: 2, gapWidth: 2 },
    levels: [
      {
        itemStyle: {
          borderColor: '#e8dfd3',
          borderWidth: 2,
          gapWidth: 2,
        },
      },
    ],
    data: stats.value.collections.map((c, i) => ({
      name: c.name,
      value: c.value,
      itemStyle: {
        color: `hsl(${(28 + i * 17) % 360} 45% ${48 + (i % 4) * 6}%)`,
      },
    })),
  }],
}))

const eraOpt = computed(() => {
  const rows = stats.value.eras
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 72, right: 16, top: 12, bottom: 24 },
    xAxis: { type: 'value', name: '剧本数' },
    yAxis: {
      type: 'category',
      data: rows.map((r) => r.name),
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: rows.map((r) => ({
        value: r.value,
        itemStyle: { color: '#8b2500', borderRadius: [0, 4, 4, 0] },
      })),
      barMaxWidth: 18,
    }],
  }
})

const scatterOpt = computed(() => {
  const selected = store.scriptId
  const byGenre = new Map<string, typeof stats.value.scatter>()
  for (const p of stats.value.scatter) {
    const list = byGenre.get(p.genre) ?? []
    list.push(p)
    byGenre.set(p.genre, list)
  }

  return asChartOption({
    tooltip: {
      trigger: 'item',
      formatter: (p: unknown) => {
        const d = (p as { data?: (typeof stats.value.scatter)[0] }).data
        if (!d) return ''
        return [
          `<b>${d.title}</b>（${d.script_id}）`,
          `体裁：${d.genre}`,
          `馆藏：${d.collection_name}`,
          `人物 ${d.character_count} · 正文块 ${d.block_count} · 场次 ${d.scene_count}`,
          d.parse_quality ? `解析质量 ${(d.parse_quality * 100).toFixed(1)}%` : '',
        ].filter(Boolean).join('<br/>')
      },
    },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: { fontSize: 10 },
      data: [...byGenre.keys()],
    },
    grid: { left: 48, right: 20, top: 36, bottom: 52 },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'inside', yAxisIndex: 0 },
    ],
    xAxis: {
      name: '正文块数',
      nameLocation: 'middle',
      nameGap: 28,
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.35 } },
    },
    yAxis: {
      name: '人物数',
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.35 } },
    },
    series: [...byGenre.entries()].map(([genre, points]) => ({
      name: genre,
      type: 'scatter',
      large: true,
      symbolSize: (val: number[]) => Math.max(6, Math.min(22, 4 + (val[2] ?? 0) * 0.8)),
      itemStyle: { color: genreColor(genre), opacity: 0.72 },
      emphasis: { focus: 'series', itemStyle: { opacity: 1 } },
      data: points.map((p) => ({
        value: [p.block_count, p.character_count, p.scene_count],
        script_id: p.script_id,
        title: p.title,
        genre: p.genre,
        collection_name: p.collection_name,
        character_count: p.character_count,
        block_count: p.block_count,
        scene_count: p.scene_count,
        parse_quality: p.parse_quality,
        itemStyle: p.script_id === selected
          ? { borderColor: '#c9a227', borderWidth: 3, opacity: 1 }
          : undefined,
      })),
    })),
  });
})

const blockOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 44, right: 16, top: 20, bottom: 40 },
  xAxis: {
    type: 'category',
    data: stats.value.blockBins.map((b) => b.label),
    axisLabel: { rotate: 20, fontSize: 10 },
  },
  yAxis: { type: 'value', name: '剧本数' },
  series: [{
    type: 'bar',
    data: stats.value.blockBins.map((b) => b.value),
    itemStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: '#c9a227' },
          { offset: 1, color: '#8b2500' },
        ],
      },
      borderRadius: [6, 6, 0, 0],
    },
  }],
}))

const qualityOpt = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 44, right: 16, top: 20, bottom: 40 },
  xAxis: {
    type: 'category',
    data: stats.value.qualityBins.map((b) => b.label),
    axisLabel: { rotate: 24, fontSize: 10 },
  },
  yAxis: { type: 'value', name: '剧本数' },
  series: [{
    type: 'line',
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    lineStyle: { width: 3, color: '#1565c0' },
    areaStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: 'rgba(21, 101, 192, 0.35)' },
          { offset: 1, color: 'rgba(21, 101, 192, 0.02)' },
        ],
      },
    },
    data: stats.value.qualityBins.map((b) => b.value),
  }],
}))

const genreChart = useChart(genreEl, () => genreOpt.value as EChartsOption, [genreOpt])
const collectionChart = useChart(collectionEl, () => collectionOpt.value as EChartsOption, [collectionOpt])
const eraChart = useChart(eraEl, () => eraOpt.value as EChartsOption, [eraOpt])
const scatterChart = useChart(
  scatterEl,
  () => scatterOpt.value as EChartsOption,
  [scatterOpt],
  { click: onScatterClick },
)
const blockChart = useChart(blockEl, () => blockOpt.value as EChartsOption, [blockOpt])
const qualityChart = useChart(qualityEl, () => qualityOpt.value as EChartsOption, [qualityOpt])

function refreshCharts() {
  genreChart.render()
  collectionChart.render()
  eraChart.render()
  scatterChart.render()
  blockChart.render()
  qualityChart.render()
}

onMounted(async () => {
  try {
    const cat = await api.catalog()
    plays.value = cat.plays
  } finally {
    loading.value = false
    refreshCharts()
  }
})
</script>

<template>
  <div class="dashboard">
    <section class="hero">
      <h2>ChinaVis · 戏韵万象</h2>
      <p>京剧剧本语料库纵览 · 点击散点或搜索可切换当前分析剧本</p>
    </section>

    <div v-if="loading" class="loading">加载目录中…</div>
    <template v-else>
      <div class="kpis">
        <div class="kpi">
          <span class="num">{{ stats.kpis.plays.toLocaleString() }}</span>
          <span class="lbl">剧本</span>
        </div>
        <div class="kpi">
          <span class="num">{{ stats.kpis.characters.toLocaleString() }}</span>
          <span class="lbl">人物</span>
        </div>
        <div class="kpi">
          <span class="num">{{ stats.kpis.blocks.toLocaleString() }}</span>
          <span class="lbl">正文块</span>
        </div>
        <div class="kpi">
          <span class="num">{{ stats.kpis.scenes.toLocaleString() }}</span>
          <span class="lbl">场次</span>
        </div>
        <div class="kpi">
          <span class="num">{{ stats.kpis.collections }}</span>
          <span class="lbl">丛书/馆藏</span>
        </div>
        <div class="kpi">
          <span class="num">{{ (stats.kpis.avgParseQuality * 100).toFixed(1) }}%</span>
          <span class="lbl">平均解析质量</span>
        </div>
      </div>

      <section v-if="currentPlay" class="spotlight">
        <div class="spotlight-main">
          <span class="badge">当前剧本</span>
          <h3>{{ currentPlay.title }}</h3>
          <p class="meta">
            {{ currentPlay.script_id }} · {{ currentPlay.collection_name }} ·
            {{ currentPlay.tags?.genre_inferred ?? '未知体裁' }} ·
            {{ currentPlay.tags?.era_inferred ?? '未知时代' }}
          </p>
          <p class="meta">
            {{ currentPlay.character_count }} 人物 ·
            {{ currentPlay.block_count }} 正文块 ·
            {{ currentPlay.scene_count ?? '—' }} 场次
          </p>
        </div>
        <div class="spotlight-actions">
          <RouterLink
            v-for="t in tasks"
            :key="t.path"
            :to="{ path: t.path, query: { script: currentPlay.script_id } }"
            class="mini-link"
          >
            {{ t.title }}
          </RouterLink>
        </div>
      </section>

      <section class="viz-section">
        <h3 class="section-title">语料库可视化纵览</h3>
        <div class="viz-grid">
          <ChartCard title="体裁分布" subtitle="按推断体裁统计剧本数量">
            <div ref="genreEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="丛书馆藏" subtitle="矩形面积 ∝ 剧本数量（前 12 + 其他）">
            <div ref="collectionEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="时代背景" subtitle="戏考/标签推断的历史时代">
            <div ref="eraEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="剧本规模全景" subtitle="点击散点选中剧本 · 气泡大小=场次数 · 颜色=体裁">
            <div ref="scatterEl" class="chart chart-lg" />
          </ChartCard>
          <ChartCard title="正文块数分布" subtitle="全库剧本篇幅直方图">
            <div ref="blockEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="解析质量分布" subtitle="预处理 PDF 解析置信度">
            <div ref="qualityEl" class="chart chart-sm" />
          </ChartCard>
        </div>
      </section>

      <section class="search-section">
        <label class="search-label" for="play-search">快速定位剧本</label>
        <input
          id="play-search"
          v-model="search"
          type="search"
          class="search-input"
          placeholder="输入剧名、ID 或丛书名…"
        />
        <div v-if="searchResults.length" class="search-results">
          <button
            v-for="p in searchResults"
            :key="p.script_id"
            type="button"
            class="search-item"
            :class="{ active: p.script_id === store.scriptId }"
            @click="selectPlay(p.script_id)"
          >
            <strong>{{ p.title }}</strong>
            <span>{{ p.script_id }} · {{ p.collection_name }} · {{ p.tags?.genre_inferred ?? '—' }}</span>
          </button>
        </div>
      </section>

      <section class="tasks">
        <h3>分析任务入口</h3>
        <div class="grid">
          <RouterLink
            v-for="t in tasks"
            :key="t.path"
            :to="{ path: t.path, query: store.scriptId ? { script: store.scriptId } : {} }"
            class="task-card"
          >
            <h4>{{ t.title }}</h4>
            <p>{{ t.desc }}</p>
          </RouterLink>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 1.5rem; }
.hero h2 { margin: 0; font-family: var(--font-serif); font-size: 1.75rem; }
.hero p { color: var(--text-muted); margin: 0.35rem 0 0; }
.loading { color: var(--text-muted); padding: 2rem; text-align: center; }

.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.75rem;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.85rem 1rem;
  text-align: center;
}
.kpi .num {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent-red);
  line-height: 1.2;
}
.kpi .lbl { font-size: 0.78rem; color: var(--text-muted); }

.spotlight {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 1.25rem;
  background: linear-gradient(135deg, #fff8ee 0%, #fffcf7 60%);
  border: 1px solid var(--border);
  border-left: 4px solid var(--accent-gold);
  border-radius: 10px;
}
.spotlight-main h3 { margin: 0.35rem 0; font-family: var(--font-serif); font-size: 1.35rem; }
.badge {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--accent-gold);
  font-weight: 600;
}
.meta { margin: 0.2rem 0 0; font-size: 0.85rem; color: var(--text-muted); }
.spotlight-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-content: flex-start;
}
.mini-link {
  padding: 0.35rem 0.65rem;
  font-size: 0.78rem;
  border: 1px solid var(--border);
  border-radius: 999px;
  text-decoration: none;
  color: var(--text);
  background: var(--surface);
  transition: border-color 0.15s, color 0.15s;
}
.mini-link:hover { border-color: var(--accent-red); color: var(--accent-red); }

.section-title {
  margin: 0 0 0.75rem;
  font-family: var(--font-serif);
  font-size: 1.1rem;
}
.viz-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}
.chart {
  width: 100%;
  display: block;
}
.chart-sm { height: 220px; }
.chart-md { height: 300px; }
.chart-lg { height: 360px; }

.search-section { display: flex; flex-direction: column; gap: 0.5rem; }
.search-label { font-size: 0.85rem; color: var(--text-muted); }
.search-input {
  max-width: 420px;
  padding: 0.55rem 0.85rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  font-family: inherit;
  font-size: 0.95rem;
}
.search-results {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-width: 560px;
}
.search-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: border-color 0.15s, background 0.15s;
}
.search-item:hover { border-color: var(--accent-gold); background: #fffaf3; }
.search-item.active { border-color: var(--accent-gold); background: #fff3e0; }
.search-item strong { font-size: 0.92rem; }
.search-item span { font-size: 0.78rem; color: var(--text-muted); }

.tasks h3 { margin: 0 0 0.75rem; font-family: var(--font-serif); }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}
.task-card {
  padding: 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, transform 0.15s;
}
.task-card:hover {
  border-color: var(--accent-gold);
  transform: translateY(-2px);
}
.task-card h4 { margin: 0 0 0.35rem; font-size: 1rem; }
.task-card p { margin: 0; font-size: 0.8rem; color: var(--text-muted); }

@media (max-width: 900px) {
  .viz-grid { grid-template-columns: 1fr; }
}
</style>
