<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import { hangdangColor } from '@/utils/charts'
import {
  buildCharacterRadar,
  buildConfidenceBar,
  buildHangdangPie,
} from '@/utils/roleCharts'
import type { EChartsOption } from 'echarts'
import type { PlayRole } from '@/types'

const store = useFilterStore()
const role = ref<PlayRole | null>(null)
const loading = ref(true)

const pieEl = ref<HTMLElement | null>(null)
const confEl = ref<HTMLElement | null>(null)
const radarEl = ref<HTMLElement | null>(null)

const selectedChar = computed(() => {
  const id = store.selectedCharacterIds[0]
  if (!id || !role.value) return null
  return role.value.characters.find((c) => c.character_id === id) ?? null
})

const filteredChars = computed(() => {
  const chars = role.value?.characters ?? []
  const hd = store.filterHangdang
  if (!hd) return chars
  return chars.filter((c) => c.hangdang_final === hd)
})

const pieOpt = computed(() => buildHangdangPie(role.value?.hangdang_distribution ?? {}))
const confOpt = computed(() => buildConfidenceBar(filteredChars.value))
const radarOpt = computed(() => buildCharacterRadar(selectedChar.value))

function onPieClick(params: unknown) {
  const p = params as { name?: string }
  if (p.name) {
    store.setFilterHangdang(store.filterHangdang === p.name ? null : p.name)
  }
}

function onConfClick(params: unknown) {
  const p = params as { componentType?: string; data?: { character_id?: string } }
  if (p.componentType !== 'series' || !p.data?.character_id) return
  store.toggleCharacter(p.data.character_id)
}

const pieChart = useChart(pieEl, () => pieOpt.value as EChartsOption, [pieOpt], { click: onPieClick })
const confChart = useChart(
  confEl,
  () => confOpt.value as EChartsOption,
  [confOpt],
  { click: onConfClick },
)
const radarChart = useChart(radarEl, () => radarOpt.value as EChartsOption, [radarOpt])

function refreshCharts() {
  pieChart.render()
  confChart.render()
  radarChart.render()
}

async function load() {
  if (!store.scriptId) return
  loading.value = true
  try {
    role.value = await api.playRole(store.scriptId)
  } finally {
    loading.value = false
    await nextTick()
    refreshCharts()
  }
}

onMounted(load)
watch(() => store.scriptId, load)
watch(selectedChar, () => radarChart.render())
watch(filteredChars, () => confChart.render())
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h2 class="page-title">人物与行当</h2>
      <p class="page-desc">
        点击饼图按行当筛选 · 点击置信度条选中人物 · 下方查看详情与雷达画像
        <span v-if="store.filterHangdang" class="filter-tag">
          行当：{{ store.filterHangdang }}
          <button type="button" @click="store.setFilterHangdang(null)">×</button>
        </span>
      </p>
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

      <div class="grid-top">
        <ChartCard title="行当分布" subtitle="点击扇区筛选右侧人物列表">
          <div ref="pieEl" class="chart chart-md" />
        </ChartCard>
        <ChartCard title="人物置信度" subtitle="点击条形选中 · 查看下方详情">
          <div ref="confEl" class="chart chart-tall" />
        </ChartCard>
      </div>

      <div class="grid-bottom">
        <section class="char-panel">
          <template v-if="selectedChar">
            <header class="char-head">
              <h3>{{ selectedChar.name }}</h3>
              <span class="tag" :style="{ background: hangdangColor(selectedChar.hangdang_final) }">
                {{ selectedChar.hangdang_final }}
              </span>
            </header>
            <dl class="char-meta">
              <div><dt>戏考标注</dt><dd>{{ selectedChar.hangdang_labeled ?? '—' }}</dd></div>
              <div><dt>规则推断</dt><dd>{{ selectedChar.hangdang_inferred ?? '—' }}</dd></div>
              <div><dt>置信度</dt><dd>{{ (selectedChar.confidence * 100).toFixed(0) }}%</dd></div>
            </dl>
            <p v-if="selectedChar.top_features?.length" class="char-feat">
              {{ selectedChar.top_features.join(' · ') }}
            </p>
          </template>
          <p v-else class="char-empty">在上方置信度条中点击人物</p>
        </section>
        <ChartCard
          :title="selectedChar ? `${selectedChar.name} · 多维画像` : '多维画像'"
          subtitle="唱念做打 · 台词量 · 置信度"
        >
          <div ref="radarEl" class="chart chart-md" />
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

.grid-top {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 0.85rem;
}
.grid-bottom {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 1.4fr;
  gap: 0.85rem;
  align-items: stretch;
}

.chart { width: 100%; display: block; }
.chart-md { height: 300px; }
.chart-tall { height: 380px; }

.char-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.15rem;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 300px;
}
.char-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.char-head h3 { margin: 0; font-family: var(--font-serif); font-size: 1.25rem; }
.char-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin: 0 0 0.75rem;
}
.char-meta div { display: flex; flex-direction: column; gap: 0.15rem; }
.char-meta dt { font-size: 0.72rem; color: var(--text-muted); }
.char-meta dd { margin: 0; font-size: 0.9rem; font-weight: 600; }
.char-feat {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.5;
}
.char-empty {
  margin: 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.88rem;
}
.tag { color: #fff; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }

.filter-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: 0.5rem;
  padding: 0.15rem 0.45rem;
  background: #fff8e8;
  border: 1px solid var(--accent-gold);
  border-radius: 4px;
  font-size: 0.8rem;
}
.filter-tag button {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  color: var(--text-muted);
}

@media (max-width: 900px) {
  .grid-top,
  .grid-bottom { grid-template-columns: 1fr; }
  .char-meta { grid-template-columns: 1fr; }
}
</style>
