<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import { hangdangColor } from '@/utils/charts'
import {
  buildCharacterRadar,
  buildCoarseRose,
  buildConfidenceBar,
  buildCueStacked,
  buildGlobalHeatmap,
  buildHangdangPie,
  buildIdentityBar,
  buildPersonalityBar,
  buildSourcePie,
  buildTraitSankey,
} from '@/utils/roleCharts'
import type { EChartsOption } from 'echarts'
import type { PlayRole, RoleAnalysisGlobal } from '@/types'

const store = useFilterStore()
const role = ref<PlayRole | null>(null)
const globalRole = ref<RoleAnalysisGlobal | null>(null)
const loading = ref(true)

const pieEl = ref<HTMLElement | null>(null)
const coarseEl = ref<HTMLElement | null>(null)
const sourceEl = ref<HTMLElement | null>(null)
const confEl = ref<HTMLElement | null>(null)
const cueEl = ref<HTMLElement | null>(null)
const identityEl = ref<HTMLElement | null>(null)
const personalityEl = ref<HTMLElement | null>(null)
const sankeyEl = ref<HTMLElement | null>(null)
const radarEl = ref<HTMLElement | null>(null)
const heatEl = ref<HTMLElement | null>(null)

const selectedChar = computed(() => {
  const id = store.selectedCharacterIds[0]
  if (!id || !role.value) return null
  return role.value.characters.find((c) => c.character_id === id) ?? null
})

const pieOpt = computed(() => buildHangdangPie(role.value?.hangdang_distribution ?? {}))
const coarseOpt = computed(() =>
  buildCoarseRose(role.value?.hangdang_coarse_distribution ?? role.value?.hangdang_distribution ?? {}),
)
const sourceOpt = computed(() => {
  const total = role.value?.characters.length ?? 0
  return buildSourcePie(
    role.value?.labeled_count ?? 0,
    role.value?.inferred_count ?? 0,
    total,
  )
})
const confOpt = computed(() => buildConfidenceBar(role.value?.characters ?? []))
const cueOpt = computed(() => buildCueStacked(role.value?.characters ?? []))
const identityOpt = computed(() => buildIdentityBar(role.value?.characters ?? []))
const personalityOpt = computed(() => buildPersonalityBar(role.value?.characters ?? []))
const sankeyOpt = computed(() => buildTraitSankey(role.value?.trait_summary ?? []))
const radarOpt = computed(() => buildCharacterRadar(selectedChar.value))
const heatOpt = computed(() =>
  buildGlobalHeatmap(globalRole.value?.global_feature_hangdang_matrix ?? []),
)

const pieChart = useChart(pieEl, () => pieOpt.value as EChartsOption, [pieOpt])
const coarseChart = useChart(coarseEl, () => coarseOpt.value as EChartsOption, [coarseOpt])
const sourceChart = useChart(sourceEl, () => sourceOpt.value as EChartsOption, [sourceOpt])
const confChart = useChart(confEl, () => confOpt.value as EChartsOption, [confOpt])
const cueChart = useChart(cueEl, () => cueOpt.value as EChartsOption, [cueOpt])
const identityChart = useChart(identityEl, () => identityOpt.value as EChartsOption, [identityOpt])
const personalityChart = useChart(personalityEl, () => personalityOpt.value as EChartsOption, [personalityOpt])
const sankeyChart = useChart(sankeyEl, () => sankeyOpt.value as EChartsOption, [sankeyOpt])
const radarChart = useChart(radarEl, () => radarOpt.value as EChartsOption, [radarOpt])
const heatChart = useChart(heatEl, () => heatOpt.value as EChartsOption, [heatOpt])

function refreshCharts() {
  pieChart.render()
  coarseChart.render()
  sourceChart.render()
  confChart.render()
  cueChart.render()
  identityChart.render()
  personalityChart.render()
  sankeyChart.render()
  radarChart.render()
  heatChart.render()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    role.value = await api.playRole(store.scriptId)
    try {
      globalRole.value = await api.globalRole()
    } catch {
      globalRole.value = null
    }
  } finally {
    loading.value = false
    refreshCharts()
  }
}

onMounted(load)
watch(() => store.scriptId, load)
watch(selectedChar, () => radarChart.render())
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h2 class="page-title">人物与行当</h2>
      <p class="page-desc">本剧行当构成、表演线索与特征推断 · 点击人物表可查看雷达画像</p>
    </header>

    <div v-if="loading" class="loading">加载中…</div>
    <template v-else-if="role">
      <section class="kpi-row">
        <div class="kpi">
          <span class="num">{{ role.characters.length }}</span>
          <span class="lbl">人物</span>
        </div>
        <div class="kpi">
          <span class="num">{{ Object.keys(role.hangdang_distribution).length }}</span>
          <span class="lbl">行当类型</span>
        </div>
        <div class="kpi">
          <span class="num">{{ role.labeled_count ?? 0 }}</span>
          <span class="lbl">戏考标注</span>
        </div>
        <div class="kpi">
          <span class="num">{{ role.inferred_count ?? 0 }}</span>
          <span class="lbl">规则推断</span>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">本剧行当概览</h3>
        <div class="grid-3">
          <ChartCard title="细分行当分布" subtitle="各行当人物占比">
            <div ref="pieEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="生旦净丑" subtitle="粗行当极坐标柱图">
            <div ref="coarseEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="行当来源" subtitle="标注 / 推断 / 未确定">
            <div ref="sourceEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">人物与表演线索</h3>
        <div class="grid-2">
          <ChartCard title="推断置信度" subtitle="按人物排序 · 颜色=最终行当">
            <div ref="confEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="唱念做打 × 行当" subtitle="各行当人物表演类型堆叠">
            <div ref="cueEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard title="戏剧身份" subtitle="君主、将领、谋士等">
            <div ref="identityEl" class="chart chart-md" />
          </ChartCard>
          <ChartCard
            :title="selectedChar ? `${selectedChar.name} · 多维画像` : '人物多维画像'"
            subtitle="唱念做打 · 台词量 · 置信度（点击下表选择）"
          >
            <div ref="radarEl" class="chart chart-md" />
          </ChartCard>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">特征与关联</h3>
        <div class="grid-wide">
          <ChartCard title="性格标签" subtitle="全剧人物性格词频">
            <div ref="personalityEl" class="chart chart-sm" />
          </ChartCard>
          <ChartCard title="特征 → 行当" subtitle="本剧特征与行当桑基流">
            <div ref="sankeyEl" class="chart chart-sankey" />
          </ChartCard>
        </div>
        <ChartCard title="全局特征 × 行当" subtitle="跨剧本共现热力图（颜色越深共现越多）">
          <div ref="heatEl" class="chart chart-heat" />
        </ChartCard>
      </section>

      <ChartCard title="人物明细" subtitle="点击行高亮并在雷达图中查看">
        <table class="table">
          <thead>
            <tr>
              <th>姓名</th><th>标注</th><th>推断</th><th>最终</th><th>置信度</th><th>特征</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in role.characters"
              :key="c.character_id"
              :class="{ hl: store.selectedCharacterIds.includes(c.character_id) }"
              @click="store.toggleCharacter(c.character_id)"
            >
              <td>{{ c.name }}</td>
              <td>{{ c.hangdang_labeled ?? '—' }}</td>
              <td>{{ c.hangdang_inferred ?? '—' }}</td>
              <td>
                <span class="tag" :style="{ background: hangdangColor(c.hangdang_final) }">
                  {{ c.hangdang_final }}
                </span>
              </td>
              <td>
                <span class="conf-bar">
                  <span class="conf-fill" :style="{ width: `${c.confidence * 100}%`, background: hangdangColor(c.hangdang_final) }" />
                  <span class="conf-txt">{{ (c.confidence * 100).toFixed(0) }}%</span>
                </span>
              </td>
              <td class="feat">{{ (c.top_features ?? []).join(' · ') }}</td>
            </tr>
          </tbody>
        </table>
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
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 0.65rem;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
  text-align: center;
}
.kpi .num { display: block; font-size: 1.4rem; font-weight: 700; color: var(--accent-red); }
.kpi .lbl { font-size: 0.75rem; color: var(--text-muted); }

.section-title {
  margin: 0 0 0.65rem;
  font-family: var(--font-serif);
  font-size: 1.05rem;
  color: var(--text);
}
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}
.grid-wide {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 0.85rem;
  margin-bottom: 0.85rem;
}
.chart { width: 100%; display: block; }
.chart-md { height: 300px; }
.chart-sm { height: 260px; }
.chart-sankey { height: 320px; }
.chart-heat { height: 360px; }

.table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { padding: 0.5rem; border-bottom: 1px solid var(--border); text-align: left; }
tr { cursor: pointer; transition: background 0.12s; }
tr.hl, tr:hover { background: #fff8e8; }
.tag { color: #fff; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }
.feat { font-size: 0.75rem; color: var(--text-muted); max-width: 320px; }

.conf-bar {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 88px;
  height: 1.25rem;
  background: #f0ebe3;
  border-radius: 4px;
  overflow: hidden;
}
.conf-fill { position: absolute; left: 0; top: 0; bottom: 0; opacity: 0.55; }
.conf-txt { position: relative; z-index: 1; padding: 0 0.35rem; font-size: 0.75rem; font-weight: 600; }

@media (max-width: 1100px) {
  .grid-3 { grid-template-columns: 1fr; }
  .grid-wide { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
